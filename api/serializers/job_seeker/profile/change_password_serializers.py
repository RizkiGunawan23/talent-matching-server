from rest_framework import serializers
from django.contrib.auth.hashers import check_password, make_password

from api.models import User

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        required=True,
        write_only=True,
        error_messages={
            "required": "Password lama harus diisi.",
            "blank": "Password lama harus diisi.",
        },
    )
    new_password = serializers.CharField(
        min_length=8,
        required=True,
        write_only=True,
        error_messages={
            "required": "Password baru harus diisi.",
            "blank": "Password baru harus diisi.",
            "min_length": "Password baru minimal 8 karakter.",
        },
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        error_messages={
            "required": "Konfirmasi password harus diisi.",
            "blank": "Konfirmasi password harus diisi.",
        },
    )
    
    def validate(self, attrs):
        current_password = attrs.get('current_password')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        email = self.context.get('email')
        if not email:
            raise serializers.ValidationError({"email": "Email tidak ditemukan dalam token."})

        user_data = User.get_by_email(email=email)
        if not user_data or not check_password(current_password, user_data.password):
            raise serializers.ValidationError({"current_password": "Password lama tidak benar."})

        if new_password != confirm_password:
            raise serializers.ValidationError({
                "confirm_password": "Password baru dan konfirmasi password tidak cocok."
            })

        self.user_data = user_data
        return attrs