from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class AdminScrapingView(ViewSet):
    @action(methods=["get"], detail=False, url_path="status")
    def status(self, request):
        return Response({"message": "Scraping status retrieved successfully."})

    @action(methods=["post"], detail=False, url_path="start")
    def start_scraping(self, request):
        return Response({"message": "Scraping started successfully."})

    @action(methods=["post"], detail=False, url_path="cancel")
    def stop_scraping(self, request):
        return Response({"message": "Scraping stopped successfully."})
