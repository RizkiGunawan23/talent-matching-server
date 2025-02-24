from rest_framework.exceptions import ValidationError


def custom_exception_handler(exc, context):
    # Pindahkan import ke sini agar dilakukan saat fungsi dipanggil, bukan pada inisialisasi modul
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)

    if response is not None and isinstance(exc, ValidationError):
        custom_response = {
            'message': 'Terjadi kesalahan validasi.',
            'errors': response.data,
        }
        response.data = custom_response

    return response
