from core.views.admin.file import FileDetailView, FileUploadView
from core.views.admin.job import AdminJobDetailView, AdminJobView
from core.views.admin.scraping import (
    JobDumpView,
    JobScrapingCancelView,
    JobScrapingTaskStatusView,
    JobScrapingView,
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
