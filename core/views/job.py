from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from ..tasks import scrape_glints_data_detail
from django.core.cache import cache
from celery.result import AsyncResult


class JobRecommendationView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        return Response({"message": "get JobRecommendationListViewsssss"}, status=status.HTTP_200_OK)


class JobDetailView(APIView):
    pass


class JobScrapingView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        try:
            task = scrape_glints_data_detail.delay()
            return Response({"task_id": task.id, "message": "Scraping job is running in the background"}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class JobScrapingDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        try:
            task = scrape_glints_data_detail.delay()
            return Response({"task_id": task.id, "message": "Scraping job is running in the background"}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class JobScrapingTaskStatusView(APIView):
    def get(self, request, task_id):
        result = AsyncResult(task_id)
        progress_data = cache.get(f'scraping_progress_{task_id}', {})

        # Ambil nilai dari progress_data dengan default 0 jika tidak ditemukan
        status = result.status
        max_page = progress_data.get("max_page", 0)
        scraped_jobs = progress_data.get("scraped_jobs", 0)
        total_jobs = progress_data.get("total_jobs", 0)

        return Response({
            "task_id": task_id,
            "status": status,
            "max_page": max_page if status == "GETTING_MAX_PAGE_NUMBER" or status == "SUCCESS" else None,
            "scraped_jobs": scraped_jobs if status == "SCRAPING_JOB_DETAIL" or status == "SUCCESS" else None,
            "total_jobs": total_jobs if status != "GETTING_AUTH_DATA" or status != "GETTING_MAX_PAGE_NUMBER" else None,
            "result": result.result if result.status == "SUCCESS" else None,
        })
