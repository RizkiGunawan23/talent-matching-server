from django.http import JsonResponse
from rest_framework import status
from django.views import View
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.services import job_service
from core.services.matching_service import MatchingService
import json

class JobFilterOptionsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request: Request) -> Response:
        """Get all available filter options from database"""
        try:
            filter_options = job_service.get_filter_options()
            
            return Response(
                {
                    "success": True,
                    "data": filter_options
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Error fetching filter options: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TAMBAH: Endpoint khusus untuk provinces
class ProvincesView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request: Request) -> Response:
        """Get all unique provinces from database"""
        try:
            provinces = job_service.get_provinces()
            
            return Response(
                {
                    "success": True,
                    "data": {
                        "provinces": provinces
                    }
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Error fetching provinces: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class JobSearchView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request: Request) -> Response:
        """Search jobs with filters"""
        try:
            # Parse query parameters
            filters = {}
            
            # Search terms
            if request.query_params.get('job'):
                filters['job'] = request.query_params.get('job')
            
            if request.query_params.get('location'):
                filters['location'] = request.query_params.get('location')
            
            # Salary filters
            if request.query_params.get('salaryMin'):
                filters['salaryMin'] = request.query_params.get('salaryMin')
                
            if request.query_params.get('salaryMax'):
                filters['salaryMax'] = request.query_params.get('salaryMax')
            
            # Sort order
            if request.query_params.get('sortOrder'):
                filters['sortOrder'] = request.query_params.get('sortOrder')
            
            # Array-based filters - CONVERT TO DATABASE VALUES
            if request.query_params.get('jobTypes'):
                job_types_raw = request.query_params.get('jobTypes').split(',')
                # Convert frontend values to database values
                job_types_mapping = {
                    'penuh-waktu': 'Penuh Waktu',
                    'paruh-waktu': 'Paruh Waktu', 
                    'kontrak': 'Kontrak',
                    'magang': 'Magang',
                    'freelance': 'Freelance'
                }
                job_types = []
                for jt in job_types_raw:
                    jt = jt.strip()
                    if jt in job_types_mapping:
                        job_types.append(job_types_mapping[jt])
                    else:
                        job_types.append(jt)  # fallback to original value
                filters['jobTypes'] = job_types
                
            if request.query_params.get('workArrangements'):
                work_arrangements_raw = request.query_params.get('workArrangements').split(',')
                # Convert frontend values to database values  
                work_arrangements_mapping = {
                    'kerja-di-kantor': 'Kerja di kantor',
                    'remote-dari-rumah': 'Remote',
                    'hybrid': 'Hybrid'
                }
                work_arrangements = []
                for wa in work_arrangements_raw:
                    wa = wa.strip()
                    if wa in work_arrangements_mapping:
                        work_arrangements.append(work_arrangements_mapping[wa])
                    else:
                        work_arrangements.append(wa)  # fallback
                filters['workArrangements'] = work_arrangements
                
            if request.query_params.get('experiences'):
                experiences = request.query_params.get('experiences').split(',')
                filters['experiences'] = [exp.strip() for exp in experiences if exp.strip()]
                
            if request.query_params.get('educationLevels'):
                education_levels_raw = request.query_params.get('educationLevels').split(',')
                # Convert frontend values to database values
                education_levels_mapping = {
                    'sma-smk': 'SMA/SMK',
                    'diploma-d1---d4': 'Diploma (D1 - D4)',
                    'sarjana-s1': 'Sarjana (S1)',
                    'magister-s2': 'Magister (S2)',
                    'doktor-s3': 'Doktor (S3)',
                    'sd': 'SD',
                    'smp': 'SMP'
                }
                education_levels = []
                for ed in education_levels_raw:
                    ed = ed.strip()
                    if ed in education_levels_mapping:
                        education_levels.append(education_levels_mapping[ed])
                    else:
                        education_levels.append(ed)  # fallback
                filters['educationLevels'] = education_levels
            
            print(f"Original query params: {dict(request.query_params)}")
            print(f"Processed filters: {filters}")
            
            # Get filtered jobs from database
            jobs = job_service.get_jobs_by_filters(filters)
            
            return Response(
                {
                    "success": True,
                    "data": {
                        "jobs": jobs,
                        "total": len(jobs),
                        "filters_applied": filters
                    }
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            print(f"Error in job search: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error searching jobs: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class JobRecommendationView(APIView):
    """Get job recommendations for the current user with filters"""
    permission_classes = [AllowAny]  # Ubah dari IsAuthenticated ke AllowAny

    def post(self, request):
        """Handle POST request to get job recommendations with filters"""
        try:
            # Get user email from request body (frontend sudah mengirim ini)
            user_email = request.data.get('user_email')
            
            if not user_email:
                return JsonResponse({
                    'success': False,
                    'error': 'User email is required in request body'
                }, status=400)
            
            # Get filters from request body (exclude user_email from filters)
            filters = {k: v for k, v in request.data.items() if k != 'user_email'}
            
            # Get job recommendations with filters
            matching_service = MatchingService()
            recommendations = matching_service.get_user_job_matches_with_filters(user_email, filters)
            
            return JsonResponse({
                'success': True,
                'data': {
                    'jobs': recommendations,
                    'total_count': len(recommendations)
                }
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

class JobDetailByIdView(APIView):
    """Get job detail by 36 character suffix from job_url"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Handle GET request to get job detail by ID suffix"""
        try:
            # Get the 36 character ID from query parameters
            job_id_suffix = request.query_params.get('id')
            
            if not job_id_suffix:
                return JsonResponse({
                    'success': False,
                    'error': 'Job ID suffix is required'
                }, status=400)
            
            print(f"🔍 Looking for job with ID suffix: {job_id_suffix}")
            
            # Use job service to get job from Neo4j database
            job_data = job_service.get_job_by_url_suffix(job_id_suffix)
            
            if job_data:
                print(f"✅ Found matching job: {job_data.get('job_title', 'Unknown')}")
                return JsonResponse({
                    'success': True,
                    'data': {
                        'job': job_data
                    }
                })
            else:
                print(f"❌ No job found with ID suffix: {job_id_suffix}")
                return JsonResponse({
                    'success': False,
                    'error': f'Job not found with ID suffix: {job_id_suffix}'
                }, status=404)
                
        except Exception as e:
            print(f"❌ Error getting job detail: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)