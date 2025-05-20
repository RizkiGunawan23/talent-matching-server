from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.serializers import CustomTokenSerializer, SignInSerializer, SignUpSerializer


class SignUpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            token_data = CustomTokenSerializer.get_token(user)

            # Return tokens in response body instead of cookies
            return Response(
                {
                    "message": "User registered successfully",
                    "user": token_data["user"],
                    "tokens": {
                        "access": token_data["access"],
                        "refresh": token_data["refresh"],
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = SignInSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data["user"]
            token_data = CustomTokenSerializer.get_token(user)

            # Return tokens in response body
            return Response(
                {
                    "message": "Login successful",
                    "user": token_data["user"],
                    "tokens": {
                        "access": token_data["access"],
                        "refresh": token_data["refresh"],
                    },
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignOutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        try:
            # Token-based logout doesn't require server action
            # It's handled client-side by discarding the tokens
            # But we can blacklist the refresh token if needed

            refresh_token = request.data.get("refresh")
            if refresh_token:
                # Optional: Blacklist the refresh token
                # token = RefreshToken(refresh_token)
                # token.blacklist()
                pass

            return Response(
                {"message": "Successfully logged out"}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ForgetPasswordView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(
            {"message": "get ForgetPasswordApiView"}, status=status.HTTP_200_OK
        )
