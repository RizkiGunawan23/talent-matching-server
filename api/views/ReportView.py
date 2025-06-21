from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.services.report_services import report_job


class ReportView(ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(
        methods=["post"],
        detail=False,
        url_path="create-report",
        url_name="create-report",
    )
    def create_report(self, request):
        """Report a job that seems fraudulent or inappropriate"""
        try:
            # Get user UID from authenticated user
            user_uid = request.user.uid
            
            # Get request data
            job_url = request.data.get("job_url")
            report_type = request.data.get("reportType")
            report_descriptions = request.data.get("reportDescriptions", "")
            
            # Validate required fields
            if not all([job_url, report_type]):
                return Response(
                    {"success": False, "message": "Semua field harus diisi"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create report
            success = report_job(
                user_uid, 
                job_url, 
                report_type, 
                report_descriptions
            )
            
            if success:
                return Response(
                    {"success": True, "message": "Report berhasil dikirim"},
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {"success": False, "message": "Gagal mengirim report"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"success": False, "message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )