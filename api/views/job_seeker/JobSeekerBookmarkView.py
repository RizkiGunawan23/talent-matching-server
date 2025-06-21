from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.services.job_seeker.job_seeker_bookmark_services import (
    toggle_bookmark,
    get_bookmarked_jobs,
    check_bookmark_status
)


class JobSeekerBookmarkView(ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(
        methods=["post"],
        detail=False,
        url_path="change-status",
        url_name="change-status",
    )
    def change_status(self, request):
        """Toggle bookmark status for a job"""
        try:
            # Get user_uid from authenticated user
            user_uid = request.user.uid
            job_url = request.data.get('job_url')
            
            if not job_url:
                return Response({
                    'message': 'job_url is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = toggle_bookmark(user_uid, job_url)
            
            if result['success']:
                return Response({
                    'message': result['message'],
                    'data': {
                        'action': result['action'],
                        'is_bookmarked': result['is_bookmarked']
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': result['message']
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(
        methods=["get"],
        detail=False,
        url_path="list",
        url_name="list",
    )
    def get_bookmarked_jobs(self, request):
        """Get all bookmarked jobs for the authenticated user"""
        try:
            # Get user_uid from authenticated user
            user_uid = request.user.uid
            
            # Get bookmarked jobs
            bookmarked_jobs = get_bookmarked_jobs(user_uid)
            
            return Response({
                'message': 'Bookmarked jobs retrieved successfully',
                'data': {
                    'jobs': bookmarked_jobs,
                    'total': len(bookmarked_jobs)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'message': f'Error retrieving bookmarked jobs: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(
        methods=["post"],
        detail=False,
        url_path="check",
        url_name="check",
    )
    def check_bookmark_status(self, request):
        """Check bookmark status for multiple job URLs"""
        try:
            # Get user_uid from authenticated user
            user_uid = request.user.uid
            job_urls = request.data.get('job_urls', [])
            
            if not job_urls:
                return Response({
                    'message': 'job_urls list is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            bookmark_status = check_bookmark_status(user_uid, job_urls)
            
            return Response({
                'message': 'Bookmark status retrieved successfully',
                'data': bookmark_status
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'message': f'Error checking bookmark status: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)