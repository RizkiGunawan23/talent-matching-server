from django.contrib.auth.hashers import make_password, check_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from typing import Any, Dict
from ..models import User


class SignUpSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'Email harus diisi.',
            'blank': 'Email harus diisi.',
            'invalid': 'Format email tidak valid.'
        }
    )
    password = serializers.RegexField(
        regex=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
        required=True,
        write_only=True,
        error_messages={
            'required': 'Password harus diisi.',
            'blank': 'Password harus diisi.',
            'invalid': 'Password minimal 8 karakter dan harus memiliki setidaknya 1 huruf kapital, 1 huruf kecil, 1 angka, dan 1 simbol.'
        }
    )
    name = serializers.CharField(
        required=True,
        error_messages={
            'required': 'Nama harus diisi.',
            'blank': 'Nama harus diisi.',
        }
    )
    role = serializers.ChoiceField(
        choices=['user', 'admin'],
        default='user',
        error_messages={
            'invalid_choice': "Role harus berisi 'user' atau 'admin'."
        }
    )

    def validate_email(self, value: str):
        user: User | None = User.nodes.get_or_none(email=value)

        if not user:
            return value

        raise serializers.ValidationError("Email already exists")

    def create(self, validated_data: Dict[str, str]):
        user: User = User(
            email=validated_data['email'],
            password=make_password(validated_data['password'], ),
            name=validated_data['name'],
            role=validated_data['role']
        )
        user.save()
        return user


class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'Email harus diisi.',
            'blank': 'Email harus diisi.',
            'invalid': 'Format email tidak valid.'
        }
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        error_messages={
            'required': 'Password harus diisi.',
            'blank': 'Password harus diisi.',
        }
    )

    def validate(self, attrs: Dict[str, str]):
        email = attrs['email']
        password = attrs['password']

        user: User | None = User.nodes.get_or_none(email=email)

        if not user or not check_password(password, user.password):
            raise serializers.ValidationError(
                "Email atau password tidak valid")

        attrs['user'] = user
        return attrs


class CustomTokenSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = serializers.DictField(read_only=True)

    @classmethod
    def get_token(cls, user: User) -> Dict[str, str | Dict[str, str]]:
        refresh: RefreshToken = RefreshToken()
        refresh['user_id'] = user.uid
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'uid': user.uid,
                'email': user.email,
                'name': user.name
            }
        }
