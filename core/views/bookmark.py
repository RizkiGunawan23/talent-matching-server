from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import JsonResponse
from core.services.user_service import user_service
from core.services.job_service import job_service


class BookmarkView(APIView):
    """API for bookmark operations"""
    permission_classes = [AllowAny]

    def post(self, request):
        """Toggle bookmark status"""
        try:
            user_uid = request.data.get('user_uid')
            job_url = request.data.get('job_url')
            
            if not user_uid or not job_url:
                return Response({
                    'success': False,
                    'message': 'user_uid and job_url are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = user_service.toggle_bookmark(user_uid, job_url)
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """Get bookmarked jobs for user"""
        try:
            user_uid = request.query_params.get('user_uid')
            
            if not user_uid:
                return Response({
                    'success': False,
                    'message': 'user_uid is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            bookmarked_jobs = user_service.get_bookmarked_jobs(user_uid)
            
            return Response({
                'success': True,
                'data': {
                    'jobs': bookmarked_jobs,
                    'total': len(bookmarked_jobs)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BookmarkStatusView(APIView):
    """API to check bookmark status for multiple jobs"""
    permission_classes = [AllowAny]

    def post(self, request):
        """Check bookmark status for multiple job URLs"""
        try:
            user_uid = request.data.get('user_uid')
            job_urls = request.data.get('job_urls', [])
            
            if not user_uid:
                return Response({
                    'success': False,
                    'message': 'user_uid is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            bookmark_status = user_service.check_bookmark_status(user_uid, job_urls)
            
            return Response({
                'success': True,
                'data': bookmark_status
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)