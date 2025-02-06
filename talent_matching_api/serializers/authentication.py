from rest_framework import serializers
from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.tokens import RefreshToken
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

    def validate_email(self, value):
        try:
            User.nodes.get(email=value)
        except User.DoesNotExist:
            return value
        raise serializers.ValidationError("Email already exists")

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            password=make_password(validated_data['password']),
            name=validated_data['name']
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

    def validate(self, attrs):
        email = attrs['email']
        password = attrs['password']

        try:
            user = User.nodes.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Credentials are not valid')

        if not check_password(password, user.password):
            raise serializers.ValidationError('Credentials are not valid')

        attrs['user'] = user
        return attrs


class CustomTokenSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = serializers.DictField(read_only=True)

    @classmethod
    def get_token(cls, user):
        refresh = RefreshToken()
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
