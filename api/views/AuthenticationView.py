from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from api.services.authentication_services import (
    authenticate_user,
    check_email_availability,
    register_user_and_match,
)


class AuthenticationView(ViewSet):
    @action(
        methods=["post"],
        detail=False,
        url_path="sign-up",
        url_name="auth-signup",
        permission_classes=[AllowAny],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def register(self, request: Request) -> Response:
        """
        Endpoint for registering a new user.
        """
        register_user_and_match(request.data)

        return Response(
            {"message": "Register berhasil"},
            status=status.HTTP_201_CREATED,
        )

    @action(
        methods=["post"],
        detail=False,
        url_path="sign-in",
        url_name="auth-signin",
        permission_classes=[AllowAny],
    )
    def login(self, request: Request) -> Response:
        """
        Endpoint for user sign-in.
        """
        responseData = authenticate_user(request.data)
        return Response(
            {
                "message": "Login berhasil",
                "data": responseData,
            },
            status=status.HTTP_200_OK,
        )
    
    @action(
        methods=["post"],
        detail=False,
        url_path="check-email",
        url_name="auth-check-email",
        permission_classes=[AllowAny],
        parser_classes=[MultiPartParser, FormParser, JSONParser], 
    )
    def check_email(self, request: Request) -> Response:
        """
        Endpoint for checking email availability.
        """
        email = request.data.get("email")
        result = check_email_availability(email)

        return Response(
            {
                "available": result["available"],
                "message": result["message"]
            },
            status=status.HTTP_200_OK,
        )

