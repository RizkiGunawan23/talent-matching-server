import os
import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.utils.datastructures import MultiValueDict
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import User
from api.serializers.authentication_serializers import (
    LoginSerializer,
    RegisterSerializer,
)
from api.serializers.job_seeker.profile.change_password_serializers import (
    ChangePasswordSerializer,
)
from api.services.matchers.matchers_neo4j_services import (
    create_calculated_user,
    get_jobs_from_neo4j,
)
from api.services.matchers.matchers_ontology_services import (
    add_user_job_matches_to_ontology,
    apply_dynamic_categorization_pipeline,
    build_temp_graph_for_user,
    calculate_user_job_similarity_for_specific_user,
    extract_categorized_matches_for_user,
    load_base_ontology,
)


def get_token(user: User) -> dict[str, str]:
    """
    Generate JWT tokens for the user.
    """
    refresh = RefreshToken()
    refresh["user_id"] = user.uid

    user_data = {
        "uid": user.uid,
        "email": user.email,
        "name": user.name,
        "role": user.role or "user",
        "profile_picture_url": None,
    }

    if user.profilePicture:
        profile_picture_url = f"http://localhost:8000/api/profile/image/{user.email}/"
        user_data["profile_picture_url"] = profile_picture_url

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": user_data,
    }


def check_email_availability(email: str) -> dict[str, any]:
    """
    Check if email is available for registration.
    Returns availability status and appropriate message.
    """
    if not email:
        raise APIException(
            detail="Email is required",
            code=status.HTTP_400_BAD_REQUEST,
        )

    user = User.get_by_email(email=email)

    if user:
        return {
            "available": False,
            "message": "Email address is already registered",
            "status_code": status.HTTP_400_BAD_REQUEST,
        }
    else:
        return {
            "available": True,
            "message": "Email address is available",
        }


def register_user_and_match(request_data: dict[str, any]) -> dict[str, str] | None:
    uid = str(uuid.uuid4())

    serializer = RegisterSerializer(data=request_data)
    serializer.is_valid(raise_exception=True)
    attrs = serializer.validated_data
    attrs["uid"] = uid

    if User.get_by_email(email=attrs["email"]) is not None:
        raise APIException(
            detail="Email sudah terdaftar",
            code=status.HTTP_400_BAD_REQUEST,
        )

    user_email = attrs["email"]
    user_skills = attrs["skills"]

    base_graph = load_base_ontology()

    jobs_data = get_jobs_from_neo4j()

    temp_graph, user_uri = build_temp_graph_for_user(
        base_graph, jobs_data, user_email, user_skills
    )

    new_matches = calculate_user_job_similarity_for_specific_user(temp_graph, user_uri)

    temp_graph = add_user_job_matches_to_ontology(temp_graph, new_matches)

    temp_graph = apply_dynamic_categorization_pipeline(temp_graph)

    categorized_matches = extract_categorized_matches_for_user(temp_graph, user_uri)

    filepath = None
    profile_picture = attrs.get("profile_picture", None)
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
        filepath = os.path.join("uploaded_files", "profile_pictures", filename)
        attrs["profile_image"] = filepath

    attrs["password"] = make_password(attrs["password"])
    created_user = create_calculated_user(attrs, categorized_matches)

    if profile_picture and created_user:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Save file
        with open(filepath, "wb") as destination:
            for chunk in profile_picture.chunks():
                destination.write(chunk)


def authenticate_user(request_data: dict[str, str]) -> dict[str, str] | None:
    """
    Authenticate user and return JWT tokens.
    """
    serializer = LoginSerializer(data=request_data)
    serializer.is_valid(raise_exception=True)
    attrs = serializer.validated_data

    email = attrs["email"]
    password = attrs["password"]

    user = User.get_by_email(email=email)

    if not user or not check_password(password, user.password):
        raise APIException(
            detail="Email atau password tidak valid",
            code=status.HTTP_401_UNAUTHORIZED,
        )

    response_data = get_token(user)

    return response_data
