import requests
from bs4 import BeautifulSoup
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from ..tasks import scrape_jobstreet_data
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
            task = scrape_jobstreet_data.delay()
            return Response({"task_id": task.id, "message": "Scraping job is running in the background"}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class JobScrapingTaskStatusView(APIView):
    def get(self, request, task_id):
        result = AsyncResult(task_id)
        progress = cache.get(f'scraping_progress_{task_id}', 0)

        if result.state == "PROGRESS" and result.info and isinstance(result.info, dict):
            progress = result.info.get('progress', progress)

        if result.state == "SUCCESS":
            progress = 100

        return Response({
            "task_id": task_id,
            "status": result.status,
            "progress": f"{progress}%",
            "result": result.result if result.status == "SUCCESS" else None,
        })
