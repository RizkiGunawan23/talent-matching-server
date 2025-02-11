from django.urls import path, include
from .views.authentication import (
    SignUpView,
    SignInView,
    SignOutView,
    ForgetPasswordView,
)
from .views.job import JobRecommendationView, JobScrapingView, JobScrapingTaskStatusView
from .views.profile import ProfileView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/sign-up/', SignUpView.as_view(), name='sign-up'),
    path('auth/sign-in/', SignInView.as_view(), name='sign-in'),
    path('auth/sign-out/', SignOutView.as_view(), name='sign-out'),
    path('auth/forgot-password/',
         ForgetPasswordView.as_view(), name='forgot-password'),

    path('jobs/recommendation/', JobRecommendationView.as_view(),
         name='job-recommendation'),
    path('jobs/scraping/', JobScrapingView.as_view(), name='job-scraping'),
    path('jobs/scraping/status/<str:task_id>/',
         JobScrapingTaskStatusView.as_view(), name='job-scraping-status'),

    path('profile/update/', ProfileView.as_view(), name='profile-update'),
]
