from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from core.views.admin.file import FileDetailView, FileUploadView
from core.views.admin.job import AdminJobDetailView, AdminJobView
from core.views.admin.matching import (
    JobMatchingAfterScrapingView,
    JobMatchingTaskStatusView,
)
from core.views.admin.scraping import (
    JobDumpView,
    JobScrapingCancelView,
    JobScrapingTaskStatusView,
    JobScrapingView,
)
from core.views.authentication import (
    CheckEmailView,
    ForgetPasswordView,
    SignInView,
    SignOutView,
    SignUpView,
)
from core.views.bookmark import BookmarkStatusView, BookmarkView
from core.views.job_seeker.job import (
    JobRecommendationView,
    JobSeekerJobDetailView,
    JobSeekerJobView,
)
from core.views.job_seeker.profile import ProfileView
from core.views.jobs import (
    DeleteJobView,
    JobDetailByIdView,
    JobFilterOptionsView,
    JobReportAssessment,
    JobReportedUsersView,
    JobSearchView,
    ProvincesView,
    ReportJobView,
)
from core.views.maintenance import MaintenanceStatusView
from core.views.media import ProfileImageView
from core.views.password import ChangePasswordView
from core.views.profile import EditProfileView, UserProfileView
from core.views.seeder import SeederView
from core.views.media import ProfileImageView
from core.views.skills import SkillsListView
from core.views.jobs import JobFilterOptionsView, JobSearchView, ProvincesView, JobRecommendationView, JobDetailByIdView, ReportJobView, DeleteJobView
from core.views.bookmark import BookmarkView, BookmarkStatusView
from core.views.password import ChangePasswordView
from core.views.profile import EditProfileView, UserProfileView
from core.views.maintenance import MaintenanceStatusView
from core.views.skills import SkillsListView

urlpatterns = [
    path("seeder/users/", SeederView.as_view(), name="seeder-users"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/sign-up/", SignUpView.as_view(), name="sign-up"),
    path("auth/sign-in/", SignInView.as_view(), name="sign-in"),
    path("auth/sign-out/", SignOutView.as_view(), name="sign-out"),
    path('auth/check-email/', CheckEmailView.as_view(), name='check-email'),
    path("auth/forgot-password/", ForgetPasswordView.as_view(), name="forgot-password"),
    path(
        "jobs/recommendation/",
        JobRecommendationView.as_view(),
        name="job-recommendation",
    ),
    path("jobs/scraping/start/", JobScrapingView.as_view(), name="job-scraping-start"),
    path(
        "jobs/scraping/cancel/",
        JobScrapingCancelView.as_view(),
        name="job-scraping-cancel",
    ),
    path(
        "jobs/scraping/status/",
        JobScrapingTaskStatusView.as_view(),
        name="job-scraping-status",
    ),
    path(
        "jobs/scraping/matching/start/",
        JobMatchingAfterScrapingView.as_view(),
        name="job-matching-after-scraping",
    ),
    path(
        "jobs/scraping/matching/status/",
        JobMatchingTaskStatusView.as_view(),
        name="job-matching-task-status",
    ),
    path(
        "jobs/admin/",
        AdminJobView.as_view(),
        name="admin-job-list",
    ),
    path(
        "jobs/admin/detail/",
        AdminJobDetailView.as_view(),
        name="admin-job-list",
    ),
    path(
        "report/admin/",
        JobReportedUsersView.as_view(),
        name="report-admin-job-list",
    ),
    path(
        "report/admin/assessment/",
        JobReportAssessment.as_view(),
        name="report-admin-job-list",
    ),
    path("profile/update/", ProfileView.as_view(), name="profile-update"),
    path("files/", FileUploadView.as_view(), name="file-upload"),
    path("files/<str:file_id>/", FileDetailView.as_view(), name="file-detail"),
    path(
        "profile/image/<str:email>/", ProfileImageView.as_view(), name="profile-image"
    ),
    path("skills/", SkillsListView.as_view(), name="skills-list"),
    path(
        "jobs/filter-options/",
        JobFilterOptionsView.as_view(),
        name="job-filter-options",
    ),
    path("jobs/search/", JobSearchView.as_view(), name="job-search"),
    path("jobs/provinces/", ProvincesView.as_view(), name="job-provinces"),
    path(
        "jobs/recommendations/",
        JobRecommendationView.as_view(),
        name="job-recommendations",
    ),
    path("jobs/detail/", JobDetailByIdView.as_view(), name="job-detail-by-id"),
    path("bookmark/", BookmarkView.as_view(), name="bookmark"),
    path("bookmark/status/", BookmarkStatusView.as_view(), name="bookmark-status"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("profile/edit/", EditProfileView.as_view(), name="edit-profile"),
    path("profile/default/", UserProfileView.as_view(), name="user-profile-default"),
    path(
        "maintenance/status/",
        MaintenanceStatusView.as_view(),
        name="maintenance-status",
    ),
    path("jobs/report/", ReportJobView.as_view(), name="report-job"),
    path("jobs/delete/", DeleteJobView.as_view(), name="delete-job"),
]
