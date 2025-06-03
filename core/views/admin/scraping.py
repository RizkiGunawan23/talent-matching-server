import json
import uuid

from celery.result import AsyncResult
from django.core.cache import cache
from django.utils import timezone
from django.utils.timezone import is_aware, make_aware
from neomodel import db
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import ScrapingTask, User
from core.tasks import scrape_job_data


class JobScrapingView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request: Request) -> Response:
        try:
            scraping_task: ScrapingTask | None = (
                ScrapingTask.nodes.filter(status__in=["RUNNING", "FINISHED"])
                .order_by("-startedAt")
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
                    uid=task.id,
                    status="RUNNING",
                    message="Scraping sedang berjalan",
                    startedAt=timezone.now(),
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
            .order_by("-startedAt")
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
            .order_by("-startedAt")
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

        progress_data: dict[str, int | None] = cache.get(
            f"scraping_progress_{task_id}", {}
        )

        scraped_jobs: int = progress_data.get("scraped_jobs", 0)

        data = None

        if task_status == "SUCCESS":
            db.begin()
            try:
                scraping_task.status = "FINISHED"
                scraping_task.message = "Task selesai"
                if not scraping_task.finishedAt:
                    scraping_task.finishedAt = timezone.now()
                scraping_task.save()
                db.commit()
            except Exception as e:
                db.rollback()
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            data = result.result
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    data = []

            # Handle Celery task failure
        elif task_status == "FAILURE":
            db.begin()
            try:
                scraping_task.status = "ERROR"
                error_message = (
                    str(result.info) if result.info else "Unknown error occurred"
                )
                scraping_task.message = f"Task failed: {error_message}"
                if not scraping_task.finishedAt:
                    scraping_task.finishedAt = timezone.now()
                scraping_task.save()
                db.commit()
            except Exception as e:
                db.rollback()
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        current_time = timezone.now()
        started_at = scraping_task.startedAt
        finished_at = scraping_task.finishedAt

        # Make sure both datetimes have the same timezone awareness
        if not is_aware(started_at):
            started_at = make_aware(started_at)

        if finished_at:
            if not is_aware(finished_at):
                finished_at = make_aware(finished_at)
            time_spent_seconds = (finished_at - started_at).total_seconds()
            print(f"masuk ke finished_at: {time_spent_seconds}")
        else:
            time_spent_seconds = (current_time - started_at).total_seconds()
            print(f"masuk ke not finished_at: {time_spent_seconds}")

        return Response(
            {
                "task_id": task_id,
                "status": task_status,
                "scraped_jobs": scraped_jobs or None,
                "started_at": scraping_task.startedAt.isoformat(),
                "time_spent": time_spent_seconds,
                "result": data or None,
            }
        )


class JobDumpView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request: Request) -> Response:
        try:
            # Find the latest completed scraping task
            scraping_task: ScrapingTask | None = (
                ScrapingTask.nodes.filter(status="FINISHED")
                .order_by("-startedAt")
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
