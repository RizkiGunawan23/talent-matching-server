from core.views.authentication import (
    SignUpView,
    SignInView,
    SignOutView,
    ForgetPasswordView,
)
from core.views.job import JobRecommendationView, JobScrapingView, JobScrapingCancelView, JobScrapingTaskStatusView, JobView
from core.views.profile import ProfileView
from django.urls import path, include
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
    path('jobs/scraping/', JobScrapingView.as_view(),
         name='job-scraping'),
    path('jobs/scraping/cancel', JobScrapingCancelView.as_view(),
         name='job-scraping-cancel'),
    path('jobs/scraping/status/',
         JobScrapingTaskStatusView.as_view(), name='job-scraping-status'),
    path('jobs/', JobView.as_view(),
         name='create-scraped-jobs'),

    path('profile/update/', ProfileView.as_view(), name='profile-update'),
]
