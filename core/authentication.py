from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.users.models import User
from core.jwt import JWTError, decode_hs256


class JWTAuthentication(BaseAuthentication):
    """
    Authorization: Bearer <jwt>
    Payload must contain: user_id
    """

    keyword = "Bearer"

    def authenticate(self, request):
        auth = request.headers.get("Authorization", "")
        if not auth:
            return None

        parts = auth.split()
        if len(parts) != 2:
            raise AuthenticationFailed("Invalid Authorization header.")

        if parts[0] != self.keyword:
            return None

        token = parts[1].strip()
        if not token:
            raise AuthenticationFailed("Invalid token.")

        secret = getattr(settings, "JWT_SECRET", settings.SECRET_KEY)
        try:
            payload = decode_hs256(token, secret=secret)
        except JWTError:
            raise AuthenticationFailed("Invalid token.")

        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationFailed("Invalid token payload.")

        try:
            user = User.objects.select_related("role").get(id=int(user_id))
        except Exception:
            raise AuthenticationFailed("User not found.")

        if not getattr(user, "is_active", True):
            raise AuthenticationFailed("User inactive.")

        return (user, token)

