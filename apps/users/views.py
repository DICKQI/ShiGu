from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import User
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserMeSerializer,
    build_token_response,
)


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    secret = getattr(settings, "JWT_SECRET", settings.SECRET_KEY)
    ttl = int(getattr(settings, "JWT_ACCESS_TTL_SECONDS", 7 * 24 * 3600))
    data = build_token_response(user=user, secret=secret, ttl_seconds=ttl)
    return Response(data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    username = (serializer.validated_data.get("username") or "").strip()
    password = serializer.validated_data.get("password") or ""

    try:
        user = User.objects.select_related("role").get(username=username)
    except User.DoesNotExist:
        return Response({"detail": "用户名或密码错误"}, status=status.HTTP_400_BAD_REQUEST)

    if not user.is_active:
        return Response({"detail": "账号已停用"}, status=status.HTTP_403_FORBIDDEN)

    if not user.check_password(password):
        return Response({"detail": "用户名或密码错误"}, status=status.HTTP_400_BAD_REQUEST)

    secret = getattr(settings, "JWT_SECRET", settings.SECRET_KEY)
    ttl = int(getattr(settings, "JWT_ACCESS_TTL_SECONDS", 7 * 24 * 3600))
    data = build_token_response(user=user, secret=secret, ttl_seconds=ttl)
    return Response(data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    payload = {
        "id": user.id,
        "username": getattr(user, "username", ""),
        "role": getattr(getattr(user, "role", None), "name", None),
    }
    return Response(UserMeSerializer(payload).data, status=status.HTTP_200_OK)

