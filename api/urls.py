from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views.admin.AdminJobView import AdminJobView
from api.views.admin.AdminScrapingView import AdminScrapingView
from api.views.AuthenticationView import AuthenticationView

router = DefaultRouter()
router.register(r"auth", AuthenticationView, basename="auth")
router.register(r"admin/jobs", AdminJobView, basename="admin-jobs")
router.register(r"admin/scraping", AdminScrapingView, basename="admin-scraping")

urlpatterns = [
    path("", include(router.urls)),
]
