from rest_framework import serializers
from django.contrib.auth.hashers import check_password, make_password
from core.services import user_service


class ChangePasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        write_only=True,
        error_messages={
            "required": "Email harus diisi.",
            "blank": "Email harus diisi.",
        },
    )
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

    def get_user_data(self, email):
        user_data = user_service.find_user_by_email(email)
        if not user_data:
            raise serializers.ValidationError("User tidak ditemukan.")
        return user_data

    def validate(self, attrs):
        email = attrs.get('email')
        current_password = attrs.get('current_password')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        user_data = self.get_user_data(email)
        if not user_data or not check_password(current_password, user_data['password']):
            raise serializers.ValidationError({"current_password": "Password lama tidak benar."})

        if new_password != confirm_password:
            raise serializers.ValidationError({
                "confirm_password": "Password baru dan konfirmasi password tidak cocok."
            })

        self.user_data = user_data  # Simpan untuk save()
        return attrs

    def save(self):
        new_password = self.validated_data['new_password']
        hashed_password = make_password(new_password)
        user_data = getattr(self, 'user_data', None)
        result = user_service.update_user_password(user_data['uid'], hashed_password)
        if not result:
            raise serializers.ValidationError("Gagal mengubah password. Silakan coba lagi.")
        return result