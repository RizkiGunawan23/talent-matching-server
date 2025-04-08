from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from ..serializers import SignUpSerializer, SignInSerializer, CustomTokenSerializer


class SignUpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            token_data = CustomTokenSerializer.get_token(user)

            response: Response = Response({
                "user": token_data["user"]
            }, status=status.HTTP_201_CREATED)

            # Simpan token di cookie (HTTP-only)
            response.set_cookie(
                key="access",
                value=token_data["access"],
                httponly=True,
                secure=False,  # ❗ Set True di production (HTTPS)
                samesite='Lax'  # Bisa diubah jadi 'Strict' atau 'None'
            )
            response.set_cookie(
                key="refresh",
                value=token_data["refresh"],
                httponly=True,
                secure=False,
                samesite='Lax'
            )
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = SignInSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data['user']
            token_data = CustomTokenSerializer.get_token(user)

            response: Response = Response({
                "user": token_data["user"]
            }, status=status.HTTP_200_OK)

            response.set_cookie(
                key="access",
                value=token_data["access"],
                httponly=True,
                secure=True,
                samesite='Lax'
            )
            response.set_cookie(
                key="refresh",
                value=token_data["refresh"],
                httponly=True,
                secure=True,
                samesite='Lax'
            )
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignOutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        try:
            refresh_token: str | None = request.COOKIES.get(
                "refresh") or request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

            response: Response = Response(
                {"message": "Successfully logged out"}, status=status.HTTP_200_OK)
            # Hapus cookies
            response.delete_cookie("access")
            response.delete_cookie("refresh")
            return response

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ForgetPasswordView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"message": "get ForgetPasswordApiView"}, status=status.HTTP_200_OK)
