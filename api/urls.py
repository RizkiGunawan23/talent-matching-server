from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views.SkillView import SkillView
from api.views.MaintenanceView import MaintenanceView 
from api.views.ReportView import ReportView
from api.views.admin.AdminJobView import AdminJobView
from api.views.admin.AdminMatchingView import AdminMatchingView
from api.views.admin.AdminReportView import AdminReportView
from api.views.admin.AdminScrapingView import AdminScrapingView
from api.views.AuthenticationView import AuthenticationView
from api.views.job_seeker.JobSeekerBookmarkView import JobSeekerBookmarkView
from api.views.job_seeker.JobSeekerJobView import JobSeekerJobView
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
router.register(
    r"job-seeker/job", JobSeekerJobView, basename="job-seeker-job"
)
router.register(r"job-seeker/bookmark", JobSeekerBookmarkView, basename="job-seeker-bookmark")
router.register(r"report", ReportView, basename="report")
router.register(r"skill", SkillView, basename="skill")
router.register(r"maintenance", MaintenanceView, basename="maintenance")

urlpatterns = [
    path("", include(router.urls)),
]
