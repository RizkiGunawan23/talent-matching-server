from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.services.job_seeker.job_seeker_profile_services import (
    change_profile_and_match,
    get_profile_info,
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
