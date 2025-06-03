import json
from typing import Dict, List

from celery.result import AsyncResult
from django.core.cache import cache
from neomodel import db
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Job, ScrapingTask, Skill
from core.scrapers.normalize_glints_data import normalize_glints_job_data


class JobRecommendationView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        return Response(
            {"message": "get JobRecommendationListViewsssss"}, status=status.HTTP_200_OK
        )


class JobSeekerJobView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request: Request) -> Response:
        try:
            jobs = Job.nodes.all()
            return Response(
                {"message": "Success", "data": [job.to_dict() for job in jobs]},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class JobSeekerJobDetailView(APIView):
    pass
