from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views.admin.AdminJobView import AdminJobView
from api.views.admin.AdminMatchingView import AdminMatchingView
from api.views.admin.AdminReportView import AdminReportView
from api.views.admin.AdminScrapingView import AdminScrapingView
from api.views.AuthenticationView import AuthenticationView
from api.views.job_seeker.JobSeekerProfileView import JobSeekerProfileView

router = DefaultRouter()
router.register(r"auth", AuthenticationView, basename="auth")
router.register(r"admin/jobs", AdminJobView, basename="admin-jobs")
router.register(r"admin/scraping", AdminScrapingView, basename="admin-scraping")
router.register(
    r"admin/scraping/matching", AdminMatchingView, basename="admin-scraping-matching"
)
router.register(r"admin/reports", AdminReportView, basename="admin-reports")
router.register(
    r"job-seeker/profile", JobSeekerProfileView, basename="job-seeker-profile"
)

urlpatterns = [
    path("", include(router.urls)),
]
