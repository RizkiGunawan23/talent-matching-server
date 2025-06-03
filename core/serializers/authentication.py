import os
import uuid
from typing import Dict

from django.contrib.auth.hashers import check_password, make_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from core.matchers.matchers_functions import create_user_and_calculate_matches
from core.models import User
from core.services import user_service


class SignUpSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "Email harus diisi.",
            "blank": "Email harus diisi.",
            "invalid": "Format email tidak valid.",
        },
    )
    password = serializers.CharField(
        min_length=8,
        required=True,
        write_only=True,
        error_messages={
            "required": "Password harus diisi.",
            "blank": "Password harus diisi.",
            "min_length": "Password minimal 8 karakter.",
        },
    )
    name = serializers.CharField(
        required=True,
        error_messages={
            "required": "Nama harus diisi.",
            "blank": "Nama harus diisi.",
        },
    )
    role = serializers.ChoiceField(
        choices=["user", "admin"],
        default="user",
        error_messages={"invalid_choice": "Role harus berisi 'user' atau 'admin'."},
    )

    profile_picture = serializers.FileField(
        required=False,
        allow_empty_file=False,
        error_messages={
            "invalid": "File tidak valid.",
        },
    )

    # Skills field - list of skill names
    skills = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        error_messages={
            "invalid": "Skills harus berupa list.",
        },
    )

    def validate_email(self, value: str):
        user_data = user_service.find_user_by_email(value)

        if not user_data:
            return value

        raise serializers.ValidationError("Email already exists")

    def validate_skills(self, value: list[str]):
        """Validate skills - at least 1 skill required"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least 1 skill is required")

        return value

    def create(self, validated_data: dict):
        if validated_data.get("role") == "admin":
            created_user = user_service.create_admin(validated_data)
            return type("User", (), created_user)()
        elif validated_data.get("role") == "user":
            uid = str(uuid.uuid4())

            profile_picture = validated_data.pop("profile_picture", None)
            skills = validated_data.pop("skills", [])

            filepath = None
            if profile_picture:
                content_type = profile_picture.content_type
                extension = {
                    "image/jpeg": ".jpg",
                    "image/jpg": ".jpg",
                    "image/png": ".png",
                }.get(
                    content_type, ".jpg"
                )  # Default to jpg if unknown

                # Save the file to storage with proper extension
                filename = f"profile_{uid}{extension}"
                filepath = os.path.join("uploaded_files", "profile_images", filename)

            # Create user using user_service with skills
            user_data = {
                "uid": str(uid),
                "name": validated_data["name"],
                "email": validated_data["email"],
                "password": make_password(validated_data["password"]),
                "profile_image": filepath,
                "role": validated_data["role"],
                "skills": skills,
            }

            # Create user with skills
            created_user = create_user_and_calculate_matches(user_data)

            if profile_picture and created_user:
                # Ensure directory exists
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                # Save file
                with open(filepath, "wb") as destination:
                    for chunk in profile_picture.chunks():
                        destination.write(chunk)

            # Return user object for compatibility
            return type("User", (), created_user)()


class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "Email harus diisi.",
            "blank": "Email harus diisi.",
            "invalid": "Format email tidak valid.",
        },
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        error_messages={
            "required": "Password harus diisi.",
            "blank": "Password harus diisi.",
        },
    )

    def validate(self, attrs: Dict[str, str]):
        email = attrs["email"]
        password = attrs["password"]

        user: User | None = User.nodes.get_or_none(email=email)

        print(user)

        if not user or not check_password(password, user.password):
            raise serializers.ValidationError("Email atau password tidak valid")

        attrs["user"] = user
        return attrs


class CustomTokenSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = serializers.DictField(read_only=True)

    @classmethod
    def get_token(cls, user: User) -> Dict[str, str | Dict[str, str]]:
        refresh: RefreshToken = RefreshToken()
        refresh["user_id"] = user.uid

        user_data = {
            "uid": user.uid,
            "email": user.email,
            "name": user.name,
            "role": getattr(user, "role", "user"),
            "profile_picture_url": None,
        }

        # Add profile picture URL if available
        if hasattr(user, "profile_image_path") and user.profile_image_path:
            # Create proper URL for profile picture
            profile_picture_url = (
                f"http://localhost:8000/api/profile/image/{user.email}/"
            )
            user_data["profile_picture_url"] = profile_picture_url

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": user_data,
        }
