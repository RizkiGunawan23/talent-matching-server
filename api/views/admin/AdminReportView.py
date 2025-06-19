from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.services.admin.admin_report_services import (
    approve_report,
    get_report_detail_with_job_and_skills,
    get_report_list_with_job,
    reject_report,
)


class AdminReportView(ViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def list(self, request):
        """Get list of all reports with job information"""
        result = get_report_list_with_job()
        return Response(
            {
                "message": "Berhasil mendapatkan daftar laporan",
                "data": result,
            },
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, pk=None):
        """Get detailed report information
        pk format should be: {user_uid}_{job_url_encoded}
        """
        # Parse pk to extract user_uid and job_url
        if "_" not in pk:
            return Response(
                {"error": "Invalid report ID format. Use {user_uid}_{job_url_encoded}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Split only on first underscore to handle URLs with underscores
        user_uid, job_url_encoded = pk.split("_", 1)

        # URL decode if needed (depends on how frontend encodes it)
        import urllib.parse

        job_url = urllib.parse.unquote(job_url_encoded)

        result = get_report_detail_with_job_and_skills(user_uid, job_url)
        return Response(
            {
                "message": "Berhasil mendapatkan detail laporan",
                "data": result,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a report and delete the reported job
        pk format should be: {user_uid}_{job_url_encoded}
        """
        # Parse pk to extract user_uid and job_url
        if "_" not in pk:
            return Response(
                {"error": "Invalid report ID format. Use {user_uid}_{job_url_encoded}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_uid, job_url_encoded = pk.split("_", 1)

        import urllib.parse

        job_url = urllib.parse.unquote(job_url_encoded)

        result = approve_report(user_uid, job_url)
        return Response(
            {
                "message": "Laporan disetujui dan pekerjaan telah dihapus",
                "data": result,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a report
        pk format should be: {user_uid}_{job_url_encoded}
        """
        # Parse pk to extract user_uid and job_url
        if "_" not in pk:
            return Response(
                {"error": "Invalid report ID format. Use {user_uid}_{job_url_encoded}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_uid, job_url_encoded = pk.split("_", 1)

        import urllib.parse

        job_url = urllib.parse.unquote(job_url_encoded)

        rejection_reason = request.data.get("rejection_reason", "")

        result = reject_report(user_uid, job_url, rejection_reason)
        return Response(
            {
                "message": "Laporan ditolak",
                "data": result,
            },
            status=status.HTTP_200_OK,
        )
