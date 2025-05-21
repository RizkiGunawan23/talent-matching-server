# Import admin job views
from core.views.admin.job import AdminJobDetailView, AdminJobView

# Import scraping views (including JobScrapingCancelView)
from core.views.admin.scraping import (
    JobScrapingCancelView,  # This is defined in scraping.py, not job.py
)
from core.views.admin.scraping import (
    ImportOntologyToNeosemanticsView,
    JobDumpView,
    JobExportAsJSONView,
    JobScrapingTaskStatusView,
    JobScrapingView,
    OntologyFileUploadView,
)

# Import authentication views
from core.views.authentication import (
    ForgetPasswordView,
    SignInView,
    SignOutView,
    SignUpView,
)

# Import job seeker views
from core.views.job_seeker.job import (
    JobRecommendationView,
    JobSeekerJobDetailView,
    JobSeekerJobView,
)
from core.views.job_seeker.profile import ProfileView
from core.views.seeder import SeederView
