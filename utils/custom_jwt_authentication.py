from typing import Tuple
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework_simplejwt.tokens import Token, UntypedToken
from core.models import User


class Neo4jJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication yang mengambil user dari Neo4j menggunakan neomodel.
    """

    def get_user(self, validated_token: UntypedToken, request: Request | None = None) -> User:
        # Ambil klaim 'user_id' yang telah kita sisipkan saat pembuatan token.
        uid: str | None = validated_token.get('user_id')
        if not uid:
            raise AuthenticationFailed(
                'Token tidak valid, id user tidak ditemukan')

        user: User | None = User.nodes.get_or_none(uid=uid)

        if not user:
            if request is not None:
                setattr(request, '_user_not_found', True)
            self.user_not_found = True
            raise AuthenticationFailed('User tidak ditemukan')

        return user


class CookieJWTAuthentication(Neo4jJWTAuthentication):
    """
    Ambil JWT dari cookie HTTP-only, bukan dari Authorization header.
    """

    def authenticate(self, request: Request) -> Tuple[User, Token] | None:
        raw_token: str | None = request.COOKIES.get("access")
        if raw_token is None:
            return None  # Tidak ada token

        validated_token: Token = self.get_validated_token(raw_token)
        return self.get_user(validated_token, request), validated_token
