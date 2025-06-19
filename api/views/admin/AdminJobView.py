from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.services.admin.admin_job_services import (
    delete_multiple_jobs,
    get_job_detail_with_skills,
    get_job_list_with_skills,
)


class AdminJobView(ViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def list(self, request):
        result = get_job_list_with_skills()
        return Response(
            {
                "message": "Berhasil mendapatkan daftar pekerjaan",
                "data": result,
            },
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, pk=None):
        result = get_job_detail_with_skills(job_url=pk)
        return Response(
            {
                "message": "Berhasil mendapatkan detail pekerjaan",
                "data": result,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["delete"])
    def bulk_delete(self, request):
        """Delete multiple jobs at once"""
        job_urls = request.data.get("job_urls", [])

        if not job_urls:
            return Response(
                {"error": "job_urls list is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(job_urls, list):
            return Response(
                {"error": "job_urls must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = delete_multiple_jobs(job_urls)
            return Response(
                {
                    "message": "Bulk delete completed",
                    "data": result,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
