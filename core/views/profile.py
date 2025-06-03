import os
import time

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.matchers.matchers_functions import update_user_skills_and_recalculate_matches
from core.serializers.profile import EditProfileSerializer, UserProfileSerializer
from core.services import user_service


class ProfileView(APIView):
    permission_classes = []

    def get(self, request):
        return Response({"message": "get ProfileViewwsssss"}, status=status.HTTP_200_OK)


class EditProfileView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = []

    def patch(self, request):  # Simulasi delay untuk testing
        serializer = EditProfileSerializer(data=request.data)
        if serializer.is_valid():
            print(f"Data yang diterima: {serializer.validated_data}")
            uid = serializer.validated_data["uid"]
            email = serializer.validated_data[
                "email"
            ]  # hanya untuk identifikasi, tidak diupdate
            profile_data = {}

            # Update name jika ada
            if "name" in serializer.validated_data:
                profile_data["name"] = serializer.validated_data["name"]

            # Update profile (name saja, email tidak diupdate)
            if profile_data:
                user_service.update_user_profile(email, profile_data)

            # Update foto profil jika ada
            profile_image = serializer.validated_data.get("profile_image")
            if profile_image:
                # Ambil data user lama untuk dapatkan path lama
                user_data = user_service.get_user_with_profile_picture(email)
                old_filepath = (
                    user_data.get("profile_image_path") if user_data else None
                )

                # Simpan file baru dan update path di Neo4j
                content_type = profile_image.content_type
                extension = {
                    "image/jpeg": ".jpg",
                    "image/jpg": ".jpg",
                    "image/png": ".png",
                }.get(content_type, ".jpg")
                filename = f"profile_{uid}{extension}"
                filepath = os.path.join("uploaded_files", "profile_images", filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "wb") as destination:
                    for chunk in profile_image.chunks():
                        destination.write(chunk)
                # Update path di Neo4j
                user_service.update_user_picture(uid, {"profile_image": filepath})

                # Hapus file lama jika berbeda dan ada
                if (
                    old_filepath
                    and old_filepath != filepath
                    and os.path.exists(old_filepath)
                ):
                    try:
                        os.remove(old_filepath)
                    except Exception as e:
                        print(f"Gagal menghapus file lama: {e}")

            # Update skills jika ada
            skills = serializer.validated_data.get("skills")
            print(f"Skills yang diterima: {skills}")
            # if skills is not None:
            #     user_service.update_user_skills(uid, skills)

            # Ambil data user terbaru untuk mendapatkan profile_image_url
            updated_user_data = user_service.get_user_with_skills_and_profile(email)

            update_user_skills_and_recalculate_matches(email, skills)

            # Ambil profile_image_url dan tambahkan domain
            profile_image_url = (
                updated_user_data.get("profile_image_url")
                if updated_user_data
                else None
            )
            if profile_image_url:
                profile_image_url = f"http://localhost:8000{profile_image_url}"

            # Buat response dengan profile_image_url yang sudah dimodifikasi
            response_data = {
                "success": True,
                "message": "Profil berhasil diupdate",
                "profile_image_url": profile_image_url,
            }

            return Response(response_data, status=status.HTTP_200_OK)
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class UserProfileView(APIView):
    def get(self, request):
        email = request.query_params.get("email")
        if not email:
            return Response(
                {"error": "Email harus disertakan di query parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_data = user_service.get_user_with_skills_and_profile(email)
        if not user_data:
            return Response(
                {"error": "User tidak ditemukan"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = UserProfileSerializer(user_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
