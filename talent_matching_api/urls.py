from django.urls import path, include
from .views.authentication import (
    SignUpView,
    SignInView,
    ForgetPasswordView,
)
from .views.job import JobRecommendationView
from .views.profile import ProfileView

urlpatterns = [
    path('auth/sign-up/', SignUpView.as_view(), name='sign-up'),
    path('auth/sign-in/', SignInView.as_view(), name='sign-in'),
    path('auth/forgot-password/', ForgetPasswordView.as_view(), name='forgot-password'),

    path('jobs/recommendation/', JobRecommendationView.as_view(), name='job-recommendation'),

    path('profile/update/', ProfileView.as_view(), name='profile-update'),
]