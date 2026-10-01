from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from core.models import User
from core.security import decode_access_token


class BearerTokenAuthentication(TokenAuthentication):
    keyword = "Bearer"

    def authenticate_credentials(self, key):
        user_id = decode_access_token(key)
        if not user_id:
            raise AuthenticationFailed("Invalid or expired token")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found")

        return (user, key)
