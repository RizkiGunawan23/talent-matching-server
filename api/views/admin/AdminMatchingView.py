from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.services.admin.admin_matching_services import (
    scraping_task_status,
    start_matching_scraped_job_data,
)
from api.services.matchers.matchers_services import matching_after_scraping


class AdminMatchingView(ViewSet):
    @action(
        methods=["get"],
        detail=False,
        url_path="status",
        url_name="matching-status",
        permission_classes=[IsAuthenticated, IsAdminUser],
    )
    def status(self, request):
        responseData = scraping_task_status()
        return Response(
            {
                "message": "Matching status retrieved successfully",
                "data": responseData,
            }
        )

    @action(
        methods=["post"],
        detail=False,
        url_path="start",
        url_name="matching-start",
        permission_classes=[IsAuthenticated, IsAdminUser],
    )
    def start_matching(self, request):
        start_matching_scraped_job_data()
        return Response(
            {"message": "Matching job sedang berjalan di background"},
            status=status.HTTP_202_ACCEPTED,
        )
