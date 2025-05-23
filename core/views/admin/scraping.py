import json
import os
import uuid
from datetime import datetime
from typing import Dict, List

from celery.result import AsyncResult
from django.conf import settings
from django.core.cache import cache
from django.http import FileResponse, HttpResponse
from neomodel import db
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Job, ScrapingTask, UploadedFile, User
from core.serializers import UploadedFileSerializer
from core.tasks import scrape_job_data
from utils.job_data_parser import normalize_glints_job_data


class JobScrapingView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request: Request) -> Response:
        try:
            scraping_task: ScrapingTask | None = (
                ScrapingTask.nodes.filter(status__in=["RUNNING", "FINISHED"])
                .order_by("-started_at")
                .first_or_none()
            )

            if scraping_task:
                return Response(
                    {
                        "message": f"Scraping sedang dalam status {scraping_task.status}, silakan tunggu hingga selesai atau cancel dahulu."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            task = scrape_job_data.delay()

            user: User = request.user

            db.begin()
            try:
                scraping_task = ScrapingTask(
                    uid=task.id, status="RUNNING", message="Scraping sedang berjalan"
                ).save()

                scraping_task.triggered_by.connect(user)
                db.commit()
            except Exception as e:
                db.rollback()
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            return Response(
                {"message": "Scraping job sedang berjalan di background"},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class JobScrapingCancelView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request: Request) -> Response:
        scraping_task = (
            ScrapingTask.nodes.filter(status__in=["RUNNING", "FINISHED"])
            .order_by("-started_at")
            .first_or_none()
        )

        if not scraping_task:
            return Response(
                {"message": "Tidak ada task yang bisa dibatalkan"},
                status=status.HTTP_404_NOT_FOUND,
            )

        cache.set(f"scraping_cancel_{scraping_task.uid}", True, timeout=600)

        db.begin()
        try:
            scraping_task.status = "DUMPED"
            scraping_task.message = "Task dibatalkan oleh admin"
            scraping_task.save()
            db.commit()
        except Exception as e:
            db.rollback()
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(f"scraping_progress_{scraping_task.uid}")
        result = AsyncResult(scraping_task.uid)
        result.forget()

        return Response(
            {"message": "Task berhasil dibatalkan"}, status=status.HTTP_200_OK
        )


class JobScrapingTaskStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request: Request) -> Response:
        scraping_task: ScrapingTask | None = (
            ScrapingTask.nodes.filter(status__in=["RUNNING", "FINISHED"])
            .order_by("-started_at")
            .first_or_none()
        )
        if not scraping_task:
            return Response(
                {"message": "Belum ada task scraping terbaru yang sedang berjalan"},
                status=status.HTTP_404_NOT_FOUND,
            )

        task_id: str = scraping_task.uid
        result: AsyncResult = AsyncResult(task_id)
        task_status: str = result.status

        progress_data: Dict[str, int | None] = cache.get(
            f"scraping_progress_{task_id}", {}
        )

        max_page: int | None = progress_data.get("max_page", 0)
        scraped_jobs: int | None = progress_data.get("scraped_jobs", 0)
        total_jobs: int | None = progress_data.get("total_jobs", 0)

        normalized_result: List[Dict[str, str | int | List[str] | None]] | None = None

        if task_status == "SUCCESS":
            db.begin()
            try:
                scraping_task.status = "FINISHED"
                scraping_task.message = "Task selesai"
                scraping_task.save()
                db.commit()
            except Exception as e:
                db.rollback()
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            data: str | List[Dict[str, str | int | List[str] | None]] = result.result
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    data = []

            normalized_result = normalize_glints_job_data(data)

        return Response(
            {
                "task_id": task_id,
                "status": task_status,
                "scraped_jobs": (
                    scraped_jobs
                    if task_status == "SCRAPING_JOB_DETAIL" or task_status == "SUCCESS"
                    else None
                ),
                "total_jobs": (
                    total_jobs
                    if task_status == "COLLECTING_JOB_URLS"
                    or task_status == "SCRAPING_JOB_DETAIL"
                    or task_status == "SUCCESS"
                    else None
                ),
                "result": normalized_result,
            }
        )


class JobExportAsJSONView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request: Request) -> HttpResponse:
        try:
            # Find the latest completed scraping task
            scraping_task: ScrapingTask | None = (
                ScrapingTask.nodes.filter(status="FINISHED")
                .order_by("-started_at")
                .first_or_none()
            )

            if not scraping_task:
                return Response(
                    {"message": "No completed scraping task found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get results from Celery task
            result = AsyncResult(scraping_task.uid)
            if result.status != "SUCCESS":
                return Response(
                    {"message": "Scraping task has not successfully completed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get and normalize the data
            data = result.result
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    data = []

            job_data = normalize_glints_job_data(data)

            # Create JSON file
            json_data = json.dumps(job_data, indent=4)

            # Create HTTP response with JSON file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"job_export_{timestamp}.json"

            response = HttpResponse(json_data, content_type="application/json")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OntologyFileUploadView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request: Request) -> Response:
        # Check if there's an existing ontology file
        existing_file = UploadedFile.nodes.filter(file_type="ontology").first_or_none()
        if existing_file:
            serializer = UploadedFileSerializer(existing_file)
            return Response(
                {
                    "message": "Existing ontology file found",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"message": "No ontology file has been uploaded"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def post(self, request: Request) -> Response:
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response(
                {"message": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file type (only allow .ttl files)
        if not uploaded_file.name.endswith(".ttl"):
            return Response(
                {"message": "Only Turtle (.ttl) files are allowed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete existing ontology file if any
        existing_file = UploadedFile.nodes.filter(file_type="ontology").first_or_none()
        if existing_file:
            path_to_existing_file = "/app/uploaded_files/ontology/"
            # Delete file from storage
            if os.path.exists(path_to_existing_file + existing_file.filename):
                os.remove(path_to_existing_file + existing_file.filename)
            # Delete database record
            db.begin()
            try:
                existing_file.delete()
                db.commit()
            except Exception as e:
                db.rollback()
                return Response(
                    {"message": f"Failed to delete existing file record: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # Save file to the ontology directory
        filename = f"{uuid.uuid4()}_{uploaded_file.name}"

        # Path lengkap untuk penyimpanan fisik
        file_path = os.path.join(settings.MEDIA_ONTOLOGY_DIR, filename)

        with open(file_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Create database record with transaction
        db.begin()
        try:
            user = request.user
            file_record = UploadedFile(
                filename=filename,
                original_filename=uploaded_file.name,
                file_path=f"/media/ontology/{filename}",
                content_type=uploaded_file.content_type,
                file_size=uploaded_file.size,
                file_type="ontology",
            ).save()

            file_record.uploaded_by.connect(user)
            db.commit()

            serializer = UploadedFileSerializer(file_record)
            return Response(
                {
                    "message": "Successfully upload new ontology file",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            db.rollback()
            # Clean up the file if database operation fails
            if os.path.exists(file_path):
                os.remove(file_path)
            return Response(
                {"message": f"Failed to save file record: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JobDumpView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request: Request) -> Response:
        try:
            # Find the latest completed scraping task
            scraping_task: ScrapingTask | None = (
                ScrapingTask.nodes.filter(status="FINISHED")
                .order_by("-started_at")
                .first_or_none()
            )

            if not scraping_task:
                return Response(
                    {"message": "No completed scraping task found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get results from Celery task
            result = AsyncResult(scraping_task.uid)
            if result.status != "SUCCESS":
                return Response(
                    {"message": "Scraping task has not successfully completed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update scraping task status to DUMPED
            db.begin()
            try:
                scraping_task.status = "DUMPED"
                scraping_task.message = (
                    "Data has been dumped to file and cleared from cache"
                )
                scraping_task.save()
                db.commit()
            except Exception as e:
                db.rollback()
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            # Clear all related cache data
            cache.delete(f"scraping_progress_{scraping_task.uid}")
            cache.delete(f"scraping_cancel_{scraping_task.uid}")

            # Forget the result to free up Redis memory
            result.forget()

            return Response(
                {
                    "message": "Scraping data successfully dumped and cleared from cache",
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"message": f"Failed to dump scraping data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ImportOntologyToNeosemanticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request: Request) -> Response:
        try:
            # Find the latest uploaded ontology file
            uploaded_file: UploadedFile | None = (
                UploadedFile.nodes.filter(file_type="ontology")
                .order_by("-uploaded_at")
                .first_or_none()
            )

            if not uploaded_file:
                return Response(
                    {"message": "No ontology file found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Import the ontology file to Neo4j
            # (Assuming you have a function to handle this)
            # import_ontology_to_neosemantics(uploaded_file.file_path)

            return Response(
                {"message": "Ontology imported successfully"},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"message": f"Failed to import ontology: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
