from django.db import transaction
from rest_framework import serializers

from core.jwt import build_access_payload, encode_hs256

from .models import Role, User


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=6, max_length=128, write_only=True)

    def validate_username(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("username 不能为空")
        if User.objects.filter(username=v).exists():
            raise serializers.ValidationError("username 已存在")
        return v

    @transaction.atomic
    def create(self, validated_data):
        username = validated_data["username"]
        password = validated_data["password"]

        role, _ = Role.objects.get_or_create(name="User")
        user = User(username=username, role=role)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)


class UserMeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()


class TokenResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField()


def build_token_response(*, user: User, secret: str, ttl_seconds: int) -> dict:
    payload = build_access_payload(user_id=user.id, ttl_seconds=ttl_seconds)
    token = encode_hs256(payload, secret=secret)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": int(ttl_seconds),
    }

