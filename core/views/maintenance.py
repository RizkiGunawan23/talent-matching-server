from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.services.maintenance_service import maintenance_service

class MaintenanceStatusView(APIView):
    permission_classes = []

    def get(self, request):
        status_data = maintenance_service.get_maintenance_status()
        return Response(status_data, status=status.HTTP_200_OK)