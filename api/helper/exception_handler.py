from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, ValidationError
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)
    request = context['request']

    if isinstance(exc, NotAuthenticated):
        return Response({
            "message": "Token tidak ditemukan atau user belum login",
        }, status=status.HTTP_401_UNAUTHORIZED)

    if isinstance(exc, AuthenticationFailed):
        message = getattr(exc, 'detail', str(exc))
        if isinstance(message, dict) and 'detail' in message:
            message = message['detail']

        response_data = {
            "message": str(message) or "Token tidak valid atau user tidak ditemukan"
        }

        if getattr(request, '_user_not_found', False):
            res = Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
            res.delete_cookie("access")
            res.delete_cookie("refresh")
            return res

        return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)

    if response is not None and isinstance(exc, ValidationError):
        custom_response = {
            'message': 'Terjadi kesalahan validasi',
            'errors': response.data,
        }
        response.data = custom_response

    return response
