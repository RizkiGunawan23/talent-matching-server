from typing import Tuple

from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings

from api.models import User


class Neo4jJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication for Neo4j.
    """

    def get_user(self, validated_token):
        """
        Attempt to find and return a user using the given validated token.
        """
        user_id_claim = api_settings.USER_ID_CLAIM

        if user_id_claim not in validated_token:
            raise InvalidToken()

        user_id = validated_token[user_id_claim]

        try:
            user = User.nodes.get(uid=user_id)
            return user
        except Exception:
            raise AuthenticationFailed()
