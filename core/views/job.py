from celery.result import AsyncResult
from core.models import Job, ScrapingTask, Skill, User
from core.tasks import scrape_glints_data_detail
from django.core.cache import cache
from neomodel import db
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import status
from typing import Dict, List, Union
from utils.job_data_parser import normalize_glints_job_data
import json


class JobRecommendationView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        return Response({"message": "get JobRecommendationListViewsssss"}, status=status.HTTP_200_OK)


class JobDetailView(APIView):
    pass


class JobScrapingView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request: Request) -> Response:
        try:
            scraping_task: ScrapingTask | None = ScrapingTask.nodes.filter(
                status__in=["RUNNING", "FINISHED"]
            ).order_by('-started_at').first_or_none()

            if scraping_task:
                return Response({"message": f"Scraping sedang dalam status {scraping_task.status}, silakan tunggu hingga selesai atau cancel dahulu."}, status=status.HTTP_403_FORBIDDEN)

            task = scrape_glints_data_detail.delay()

            user: User = request.user

            scraping_task = ScrapingTask(uid=task.id, status="RUNNING",
                                         message='Scraping sedang berjalan').save()

            scraping_task.triggered_by.connect(user)

            return Response({"message": "Scraping job sedang berjalan di background"}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class JobScrapingCancelView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request: Request) -> Response:
        scraping_task = ScrapingTask.nodes.filter(
            status__in=["RUNNING", "FINISHED"]
        ).order_by('-started_at').first_or_none()

        if not scraping_task:
            return Response({"message": "Tidak ada task yang bisa dibatalkan"}, status=status.HTTP_404_NOT_FOUND)

        cache.set(f"scraping_cancel_{scraping_task.uid}", True, timeout=600)

        scraping_task.status = 'DUMPED'
        scraping_task.message = 'Task dibatalkan oleh admin'
        scraping_task.save()

        cache.delete(f'scraping_progress_{scraping_task.uid}')
        result = AsyncResult(scraping_task.uid)
        result.forget()

        return Response({"message": "Task berhasil dibatalkan"}, status=status.HTTP_200_OK)


class JobScrapingTaskStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request: Request) -> Response:
        scraping_task: ScrapingTask | None = ScrapingTask.nodes.filter(
            status__in=["RUNNING", "FINISHED"]).order_by('-started_at').first_or_none()
        if not scraping_task:
            return Response({"message": "Belum ada task scraping terbaru yang sedang berjalan"},
                            status=status.HTTP_404_NOT_FOUND)

        task_id: str = scraping_task.uid
        result: AsyncResult = AsyncResult(task_id)
        task_status: str = result.status

        progress_data: Dict[str, int | None] = cache.get(
            f'scraping_progress_{task_id}', {})

        max_page: int | None = progress_data.get("max_page", 0)
        scraped_jobs: int | None = progress_data.get("scraped_jobs", 0)
        total_jobs: int | None = progress_data.get("total_jobs", 0)

        normalized_result: List[Dict[str, str |
                                     int | List[str] | None]] | None = None

        if task_status == "SUCCESS":
            scraping_task.status = "FINISHED"
            scraping_task.save()

            data: str | List[Dict[str, str |
                                  int | List[str] | None]] = result.result
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    data = []

            normalized_result = normalize_glints_job_data(data)

        return Response({
            "task_id": task_id,
            "status": task_status,
            "max_page": max_page if task_status != "PENDING" and task_status != "GETTING_AUTH_DATA" else None,
            "scraped_jobs": scraped_jobs if task_status == "SCRAPING_JOB_DETAIL" or task_status == "SUCCESS" else None,
            "total_jobs": total_jobs if task_status == "COLLECTING_JOB_URLS" or task_status == "SCRAPING_JOB_DETAIL" or task_status == "SUCCESS" else None,
            "result": normalized_result
        })


class JobView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request: Request) -> Response:
        scraping_task: ScrapingTask | None = ScrapingTask.nodes.filter(
            status='FINISHED').order_by('-started_at').first_or_none()

        if not scraping_task:
            return Response({"message": "Belum ada task scraping terbaru yang selesai"},
                            status=status.HTTP_404_NOT_FOUND)

        task_id: str = scraping_task.uid
        result: AsyncResult = AsyncResult(task_id)

        normalized_result: List[Dict[str, str |
                                     int | List[str] | None]] | None = None

        data: str | List[Dict[str, str |
                              int | List[str] | None]] = result.result
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = []

        normalized_result = normalize_glints_job_data(data)

        if not normalized_result:
            return Response({"message": "Terjadi kesalahan saat normalisasi data scraping"}, status=status.HTTP_400_BAD_REQUEST)

        saved_jobs = 0
        skipped_jobs = 0

        for job in normalized_result:
            skills: List[str] | None = job.pop("required_skills")
            saved_skills: List[Skill] = []

            job_url = job.get("job_url")
            existing_job = Job.nodes.filter(job_url=job_url).first_or_none()

            if existing_job:
                skipped_jobs += 1
                continue

            if skills:
                for skill in skills:
                    existing_skill = Skill.nodes.filter(
                        name=skill).first_or_none()
                    if existing_skill:
                        saved_skills.append(existing_skill)
                    else:
                        saved_skills.append(Skill(name=skill).save())

            db.begin()
            try:
                new_job = Job(**job).save()
                saved_jobs += 1

                for skill in saved_skills:
                    new_job.skills.connect(skill)

                db.commit()
            except Exception as e:
                db.rollback()

        cache.delete(
            f'scraping_progress_{task_id}')
        result.forget()
        scraping_task.status = 'IMPORTED'
        scraping_task.message = 'Data scraping sudah disimpan'
        scraping_task.save()

        return Response({
            "message": f"Job berhasil disimpan: {saved_jobs} job baru, {skipped_jobs} duplikat di-skip.",
        }, status=status.HTTP_201_CREATED)
