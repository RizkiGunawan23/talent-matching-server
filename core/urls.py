from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from core.views.admin.file import FileDetailView, FileUploadView
from core.views.admin.job import AdminJobDetailView, AdminJobView
from core.views.admin.scraping import (
    ImportOntologyToNeosemanticsView,
    JobDumpView,
    JobExportAsJSONView,
    JobScrapingCancelView,
    JobScrapingTaskStatusView,
    JobScrapingView,
    OntologyFileUploadView,
)
from core.views.authentication import (
    ForgetPasswordView,
    SignInView,
    SignOutView,
    SignUpView,
)
from core.views.job_seeker.job import (
    JobRecommendationView,
    JobSeekerJobDetailView,
    JobSeekerJobView,
)
from core.views.job_seeker.profile import ProfileView
from core.views.seeder import SeederView

urlpatterns = [
    path("seeder/users/", SeederView.as_view(), name="seeder-users"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/sign-up/", SignUpView.as_view(), name="sign-up"),
    path("auth/sign-in/", SignInView.as_view(), name="sign-in"),
    path("auth/sign-out/", SignOutView.as_view(), name="sign-out"),
    path("auth/forgot-password/", ForgetPasswordView.as_view(), name="forgot-password"),
    path(
        "jobs/recommendation/",
        JobRecommendationView.as_view(),
        name="job-recommendation",
    ),
    path("jobs/scraping/start", JobScrapingView.as_view(), name="job-scraping-start"),
    path(
        "jobs/scraping/cancel",
        JobScrapingCancelView.as_view(),
        name="job-scraping-cancel",
    ),
    path(
        "jobs/scraping/status/",
        JobScrapingTaskStatusView.as_view(),
        name="job-scraping-status",
    ),
    path(
        "jobs/scraping/save",
        ImportOntologyToNeosemanticsView.as_view(),
        name="create-scraped-jobs",
    ),
    path(
        "jobs/scraping/upload-ontology/",
        OntologyFileUploadView.as_view(),
        name="upload-ontology",
    ),
    path("profile/update/", ProfileView.as_view(), name="profile-update"),
    path("files/", FileUploadView.as_view(), name="file-upload"),
    path("files/<str:file_id>/", FileDetailView.as_view(), name="file-detail"),
]
