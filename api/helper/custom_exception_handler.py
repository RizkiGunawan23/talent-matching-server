from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, APIException):
        codes = exc.get_codes()
        if isinstance(codes, int) and (100 <= codes <= 599):
            status_code = codes
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response({"message": exc.detail}, status=status_code)

    if isinstance(exc, NotAuthenticated):
        return Response(
            {"message": "Token tidak ditemukan atau user belum login"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, AuthenticationFailed):
        return Response(
            {"message": "Token tidak valid atau user tidak ditemukan"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, InvalidToken):
        return Response(
            {"message": "Token tidak valid atau sudah kedaluwarsa"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if response is not None and isinstance(exc, ValidationError):
        custom_response = {
            "message": "Terjadi kesalahan validasi",
            "errors": response.data,
        }
        response.data = custom_response

    return response
