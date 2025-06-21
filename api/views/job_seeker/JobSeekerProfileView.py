from rest_framework.request import Request 
from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.services.job_seeker.job_seeker_profile_services import change_password
from api.services.job_seeker.job_seeker_profile_services import (
    change_profile_and_match,
    get_profile_info,
    get_profile_picture,
)


class JobSeekerProfileView(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user_uid = request.user.uid

        response_data = get_profile_info(user_uid=user_uid)

        return Response(
            {
                "message": "Berhasil mengambil profil",
                "data": response_data,
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, pk=None):
        if not pk:
            return Response(
                {"error": "ID user tidak boleh kosong"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request_data = request.data

        # Update profile with intelligent matching
        result = change_profile_and_match(pk, request_data)

        if not result:
            return Response(
                {"error": "Failed to update profile or user not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"message": "Profil berhasil di-update", "data": result},
            status=status.HTTP_200_OK,
        )

    @action(
    methods=["post"],
    detail=False,
    url_path="change-password",
    url_name="profile-change-password",
    permission_classes=[IsAuthenticated],
    parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def change_password(self, request: Request) -> Response:
        """
        Endpoint for changing user password.
        """
        user_email = request.user.email
        response_data = change_password(request.data, user_email=user_email)
        return Response(
            {
                "message": response_data.get("message")
            },
            status=status.HTTP_200_OK,
        )

    @action(
    methods=["get"],
    detail=False,
    url_path="image/(?P<email>.+)",  # This will match the email pattern
    url_name="profile-image",
    permission_classes=[AllowAny],  # Allow access without authentication
    )
    def get_image(self, request, email=None):
        """
        Endpoint to retrieve user profile picture by email.
        This endpoint is publicly accessible.
        """
        print(f"Fetching profile picture for email: {email}")
        try:
            print(f"Fetching profile picture for email: {email}")
            image_path = get_profile_picture(email)
            return FileResponse(open(image_path, 'rb'), content_type='image/jpeg')
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )