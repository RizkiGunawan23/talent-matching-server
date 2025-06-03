import os
from django.http import FileResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from core.services import user_service

class ProfileImageView(APIView):
    permission_classes = [AllowAny]  # Bisa diubah ke IsAuthenticated untuk security

    def get(self, request, email):
        """Serve profile image by email"""
        try:
            # Get user with profile picture path (property)
            user_data = user_service.get_user_with_profile_picture(email)

            if not user_data or not user_data.get('profile_image_path'):
                # Return default avatar atau 404
                return Response(
                    {"error": "Profile picture not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            file_path = user_data['profile_image_path']

            # Jika path relatif, gabungkan dengan BASE_DIR atau MEDIA_ROOT
            if not os.path.isabs(file_path):
                file_path = os.path.join(settings.BASE_DIR, file_path)

            # Check if file exists
            if not os.path.exists(file_path):
                return Response(
                    {"error": "Profile picture file not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Tentukan content type dari ekstensi file
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".png":
                content_type = "image/png"
            if ext == ".svg":
                content_type = "image/svg"
            else:
                content_type = "image/jpeg"

            return FileResponse(
                open(file_path, 'rb'),
                content_type=content_type,
                filename=os.path.basename(file_path)
            )

        except Exception as e:
            return Response(
                {"error": f"Error serving profile picture: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )