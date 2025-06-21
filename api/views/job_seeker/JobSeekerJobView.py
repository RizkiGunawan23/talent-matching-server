from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.services.job_seeker.job_seeker_job_services import (
    get_filter_options,
    get_job_by_url,
    get_job_provinces,
    get_job_recommendations,
    search_jobs
)


class JobSeekerJobView(ViewSet):
    
    @action(
        methods=["get"],
        detail=False, 
        url_path="filter-options",
        url_name="filter-options",
        permission_classes=[AllowAny]
    )
    def get_filter_option(self, request):
        """Get all available filter options from database"""
        try:
            filter_options = get_filter_options()
            
            return Response(
                {
                    "message": "Filter options retrieved successfully",
                    "data": filter_options
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Error fetching filter options: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(
        methods=["get"],
        detail=False, 
        url_path="provinces",
        url_name="provinces",
        permission_classes=[AllowAny]
    )
    def get_job_provinces(self, request):
        """Get all unique provinces from database"""
        try:
            provinces = get_job_provinces()
            
            return Response(
                {
                    "message": "Provinces retrieved successfully",
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
            
    @action(
        methods=["get"],
        detail=False, 
        url_path="search",
        url_name="search",
        permission_classes=[AllowAny]
    )
    def search_job(self, request):
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
            
            # Get filtered jobs from database
            jobs = search_jobs(filters)
            
            return Response(
                {
                    "message": "Jobs retrieved successfully",
                    "data": {
                        "jobs": jobs,
                        "total": len(jobs),
                        "filters_applied": filters
                    }
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error searching jobs: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        methods=["get"],
        detail=False, 
        url_path="detail",
        url_name="detail",
        permission_classes=[AllowAny]
    )
    def get_job_by_url(self, request):
        """Get job detail by URL"""
        try:
            # Get the URL from query parameters
            job_url = request.query_params.get('url')
            
            if not job_url:
                return Response(
                    {
                        "error": "Job URL is required"
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get job from database
            job_data = get_job_by_url(job_url)
            
            if job_data:
                return Response(
                    {
                        "message": "Job details retrieved successfully",
                        "data": {
                            "job": job_data
                        }
                    }, 
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        "error": f"Job not found with URL: {job_url}"
                    }, 
                    status=status.HTTP_404_NOT_FOUND
                )
                    
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {
                    "error": f"Error getting job detail: {str(e)}"
                }, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        methods=["get"],  # Changed from POST to GET to use query parameters
        detail=False, 
        url_path="recommendations",
        url_name="recommendations",
        permission_classes=[IsAuthenticated]
    )
    def get_recommendations(self, request):
        """Get job recommendations for the authenticated user with filters"""
        try:
            # Get user email from the authenticated user
            user_email = request.user.email
            
            # Parse query parameters
            filters = {}
            
            # Salary filters
            if request.query_params.get('salaryMin'):
                filters['salaryMin'] = request.query_params.get('salaryMin')
                
            if request.query_params.get('salaryMax'):
                filters['salaryMax'] = request.query_params.get('salaryMax')
            
            # Sort order - limit to similarity-desc and similarity-asc only
            if request.query_params.get('sortOrder') and request.query_params.get('sortOrder') in ['similarity-desc', 'similarity-asc']:
                filters['sortOrder'] = request.query_params.get('sortOrder')
            else:
                filters['sortOrder'] = 'similarity-desc'  # default
            
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
        
            # Get job recommendations with filters
            recommendations = get_job_recommendations(user_email, filters)
            
            return Response(
                {
                    "message": "Job recommendations retrieved successfully",
                    "data": {
                        "jobs": recommendations,
                        "total": len(recommendations),
                        "filters_applied": filters
                    }
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error fetching job recommendations: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )