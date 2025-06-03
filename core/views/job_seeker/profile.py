import os
import uuid

from django.conf import settings
from neomodel import db
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import UploadedFile, User
from core.serializers.job_seeker.profile import ProfileSerializer

# Direktori untuk menyimpan foto profil
PROFILE_IMAGES_DIR = os.path.join(settings.BASE_DIR, "uploaded_files/profile_images")
os.makedirs(PROFILE_IMAGES_DIR, exist_ok=True)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get(self, request):
        """Get current user profile information"""
        user = request.user

        # # Buat dictionary profil lengkap
        # profile_data = {
        #     "uid": user.uid,
        #     "name": user.name,
        #     "email": user.email,
        #     "role": user.role,
        #     "skills": [],
        #     "education": [],
        #     "experience": [],
        #     "profile_image": None,
        # }

        # # Ambil skills dari relasi user (jika ada)
        # if hasattr(user, "skills"):
        #     skills = list(user.skills.all())
        #     profile_data["skills"] = [
        #         {"uid": skill.uid, "name": skill.name} for skill in skills
        #     ]

        # # Ambil foto profil (jika ada)
        # profile_image = (
        #     UploadedFile.nodes.filter(file_type="profile_image")
        #     .filter(user__uid=user.uid)
        #     .first_or_none()
        # )

        # if profile_image:
        #     profile_data["profile_image"] = {
        #         "uid": profile_image.uid,
        #         "filename": profile_image.filename,
        #         "url": f"/api/profile/image/{profile_image.uid}/",
        #         "uploaded_at": profile_image.created_at,
        #     }

        return Response({"message": "Success with tokennnn"}, status=status.HTTP_200_OK)

    def patch(self, request):
        """Update user profile information"""
        user = request.user

        # Mulai transaksi database
        db.begin()
        try:
            # Update informasi dasar user
            updatable_fields = ["name", "email"]
            for field in updatable_fields:
                if field in request.data:
                    setattr(user, field, request.data[field])

            # Simpan perubahan user
            user.save()

            # Update skills jika ada dalam request
            if "skills" in request.data and isinstance(request.data["skills"], list):
                from core.models import Skill

                # Hapus semua relasi skill yang ada
                for skill in user.skills.all():
                    user.skills.disconnect(skill)

                # Tambahkan skill baru
                for skill_data in request.data["skills"]:
                    # Cari skill berdasarkan uid atau nama
                    if isinstance(skill_data, dict) and "uid" in skill_data:
                        skill = Skill.nodes.get_or_none(uid=skill_data["uid"])
                    elif isinstance(skill_data, dict) and "name" in skill_data:
                        skill = Skill.nodes.get_or_none(name=skill_data["name"])
                    elif isinstance(skill_data, str):
                        # Jika hanya nama skill yang diberikan
                        skill = Skill.nodes.get_or_none(name=skill_data)
                        # Jika skill tidak ditemukan, buat skill baru
                        if not skill:
                            skill = Skill(name=skill_data).save()

                    if skill:
                        user.skills.connect(skill)

            # Commit semua perubahan
            db.commit()

            # Ambil data user yang sudah diupdate
            profile_data = {
                "uid": user.uid,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "skills": [
                    {"uid": skill.uid, "name": skill.name}
                    for skill in user.skills.all()
                ],
            }

            return Response(profile_data, status=status.HTTP_200_OK)

        except Exception as e:
            # Rollback transaksi jika terjadi error
            db.rollback()
            return Response(
                {"error": f"Failed to update profile: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request):
        """Upload profile image"""
        if "profile_image" not in request.FILES:
            return Response(
                {"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        uploaded_file = request.FILES["profile_image"]
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()

        # Validasi file
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif"]
        if file_extension not in allowed_extensions:
            return Response(
                {"error": "Only image files (JPG, JPEG, PNG, GIF) are allowed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if uploaded_file.size > 5 * 1024 * 1024:  # 5MB limit
            return Response(
                {"error": "File too large. Maximum size is 5MB"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mulai transaksi database
        db.begin()
        try:
            # Hapus foto profil lama jika ada
            old_profile_image = (
                UploadedFile.nodes.filter(file_type="profile_image")
                .filter(user__uid=user.uid)
                .first_or_none()
            )

            if old_profile_image:
                # Hapus file fisik
                if os.path.exists(old_profile_image.file_path):
                    os.remove(old_profile_image.file_path)
                # Hapus record dari database
                old_profile_image.delete()

            # Buat nama file unik
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(PROFILE_IMAGES_DIR, unique_filename)

            # Simpan file ke disk
            with open(file_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Buat record file baru
            file_record = UploadedFile(
                filename=unique_filename,
                original_filename=uploaded_file.name,
                file_path=file_path,
                content_type=uploaded_file.content_type,
                file_size=uploaded_file.size,
                file_type="profile_image",
                description="Profile image",
            ).save()

            # Hubungkan dengan user
            file_record.user.connect(user)

            # Commit transaksi
            db.commit()

            return Response(
                {
                    "message": "Profile image uploaded successfully",
                    "image_uid": file_record.uid,
                    "filename": file_record.filename,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            # Rollback jika terjadi error
            db.rollback()
            return Response(
                {"error": f"Failed to upload profile image: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
