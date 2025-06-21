from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.models import Maintenance


class MaintenanceView(ViewSet):
    """
    ViewSet for checking and managing system maintenance status.
    """
    permission_classes = [AllowAny]
    
    @action(
        methods=["get"],
        detail=False,
        url_path="status",
        url_name="maintenance-status",
    )
    def get_status(self, request):
        """Get the current maintenance status of the system"""
        try:
            maintenance = Maintenance.get_current_maintenance()
            
            # If no maintenance record exists yet
            if not maintenance:
                return Response({
                    "message": "Maintenance status retrieved successfully",
                    "data": {
                        "isMaintenance": False
                    }
                }, status=status.HTTP_200_OK)
            
            return Response({
                "message": "Maintenance status retrieved successfully",
                "data": {
                    "isMaintenance": maintenance.isMaintenance
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                "message": f"Error retrieving maintenance status: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)