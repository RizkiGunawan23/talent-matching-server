from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from core.models import User


class Neo4jJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication yang mengambil user dari Neo4j menggunakan neomodel.
    """

    def get_user(self, validated_token):
        # Ambil klaim 'user_id' yang telah kita sisipkan saat pembuatan token.
        uid = validated_token.get('user_id')
        if uid is None:
            raise AuthenticationFailed(
                'Token contained no recognizable user identification',
                code='token_not_valid'
            )
        try:
            # Gunakan neomodel untuk mendapatkan user berdasarkan uid (yang merupakan string)
            user = User.nodes.get(uid=uid)
        except Exception:
            raise AuthenticationFailed('User not found', code='user_not_found')
        return user
