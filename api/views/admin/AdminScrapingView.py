from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.services.admin.admin_scraping_services import (
    cancel_scraping_task,
    scraping_task_status,
    start_scraping_task,
)


class AdminScrapingView(ViewSet):
    @action(
        methods=["get"],
        detail=False,
        url_path="status",
        url_name="scraping-status",
        permission_classes=[IsAuthenticated, IsAdminUser],
    )
    def status(self, request):
        responseData = scraping_task_status(request.user)
        return Response(
            {
                "message": "Scraping status retrieved successfully",
                "data": responseData,
            }
        )

    @action(
        methods=["post"],
        detail=False,
        url_path="start",
        url_name="scraping-start",
        permission_classes=[IsAuthenticated, IsAdminUser],
    )
    def start_scraping(self, request):
        start_scraping_task(request.user)
        return Response(
            {"message": "Scraping job sedang berjalan di background"},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(
        methods=["post"],
        detail=False,
        url_path="cancel",
        url_name="scraping-cancel",
        permission_classes=[IsAuthenticated, IsAdminUser],
    )
    def stop_scraping(self, request):
        cancel_scraping_task()
        return Response(
            {"message": "Scraping job telah dibatalkan"},
            status=status.HTTP_200_OK,
        )
