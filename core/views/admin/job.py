import os

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

from core.models import Job, UploadedFile
from core.serializers import UploadedFileSerializer

# Base directory for file storage
FILE_STORAGE_DIR = os.path.join(settings.BASE_DIR, "uploaded_files/ontology")
os.makedirs(FILE_STORAGE_DIR, exist_ok=True)


class AdminJobView(APIView):
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

    def delete(self, request: Request) -> Response:
        try:
            job_id = request.query_params.get("id")
            if not job_id:
                return Response(
                    {"message": "Job ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            job = Job.nodes.get_or_none(uid=job_id)
            if not job:
                return Response(
                    {"message": "Job not found"}, status=status.HTTP_404_NOT_FOUND
                )

            db.begin()
            try:
                job.delete()
                db.commit()
                return Response(
                    {"message": "Job deleted successfully"}, status=status.HTTP_200_OK
                )
            except Exception as e:
                db.rollback()
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminJobDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request: Request) -> Response:
        try:
            job_id = request.query_params.get("id")
            if not job_id:
                return Response(
                    {"message": "Job ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            job = Job.nodes.get_or_none(uid=job_id)
            if not job:
                return Response(
                    {"message": "Job not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # Get related skills
            skills = [skill.to_dict() for skill in job.skills.all()]

            # Create response data with job details and skills
            job_data = job.to_dict()
            job_data["skills"] = skills

            return Response(
                {"message": "Success", "data": job_data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
