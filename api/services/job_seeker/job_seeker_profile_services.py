import os

from rest_framework import status
from rest_framework.exceptions import APIException

from api.models import User
from api.serializers.job_seeker.profile.job_seeker_profile_serializers import (
    EditProfileSerializer,
)
from api.services.matchers.matchers_neo4j_services import (
    get_jobs_from_neo4j,
    update_neo4j_for_specific_user,
)
from api.services.matchers.matchers_ontology_services import (
    add_user_job_matches_to_ontology,
    apply_dynamic_categorization_pipeline,
    build_temp_graph_for_user,
    calculate_user_job_similarity_for_specific_user,
    extract_categorized_matches_for_user,
    load_base_ontology,
)


def get_profile_info(user_uid) -> dict[str, str] | None:
    """Get user profile information including name, email, profile_image_url, and skills"""
    user = User.get_by_uid(user_uid=user_uid)
    if user is None:
        raise APIException(
            detail="User tidak ditemukan",
            code=status.HTTP_404_NOT_FOUND,
        )

    # Get user skills
    user_skills = [skill.name for skill in user.has_skill.all()]

    # Generate profile image URL
    profile_image_url = None
    if user.profilePicture:
        profile_image_url = f"http://localhost:8000/api/profile/image/{user.email}/"

    return {
        "name": user.name,
        "email": user.email,
        "profile_image_url": profile_image_url,
        "skills": user_skills,
    }


def change_profile_and_match(pk, request_data: dict[str, any]) -> dict[str, str] | None:
    serializer = EditProfileSerializer(data=request_data)
    serializer.is_valid(raise_exception=True)
    validated_data = serializer.validated_data

    user = User.get_by_uid(user_uid=pk)
    if user is None:
        raise APIException(
            detail="User tidak ditemukan",
            code=status.HTTP_404_NOT_FOUND,
        )

    user_email = user.email
    new_skills = validated_data.get("skills")
    name = validated_data.get("name")
    profile_image = validated_data.get("profile_image")

    old_skills = [skill.name for skill in user.has_skill.all()]

    skills_changed = set(old_skills) != set(new_skills)

    if name and name != user.name:
        user.name = name
        user.save()

    filepath = None
    if profile_image:
        content_type = profile_image.content_type
        extension = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
        }.get(content_type, ".jpg")

        filename = f"profile_{pk}{extension}"
        filepath = os.path.join("uploaded_files", "profile_pictures", filename)

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Save file
        with open(filepath, "wb") as destination:
            for chunk in profile_image.chunks():
                destination.write(chunk)

        # Update profile picture path in user
        user.profilePicture = filepath
        user.save()

    # Jika skills tidak berubah, hanya update nama dan foto profil
    if not skills_changed:
        return {
            "name": user.name,
            "email": user_email,
            "profile_image": f"http://localhost:8000/api/profile/image/{user_email}/",
            "skills": new_skills,
        }

    base_graph = load_base_ontology()

    jobs_data = get_jobs_from_neo4j()

    temp_graph, user_uri = build_temp_graph_for_user(
        base_graph, jobs_data, user_email, new_skills
    )

    new_matches = calculate_user_job_similarity_for_specific_user(temp_graph, user_uri)

    temp_graph = add_user_job_matches_to_ontology(temp_graph, new_matches)

    temp_graph = apply_dynamic_categorization_pipeline(temp_graph)

    categorized_matches = extract_categorized_matches_for_user(temp_graph, user_uri)

    update_neo4j_for_specific_user(user_email, new_skills, categorized_matches)

    return {
        "name": name,
        "email": user_email,
        "profile_image": f"http://localhost:8000/api/profile/image/{user_email}/",
        "skills": new_skills,
    }
