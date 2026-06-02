from __future__ import annotations

import time

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework import status

from apps._test_helpers import auth_client, create_user
from apps.users.models import Role, User
from core.jwt import JWTError, build_access_payload, decode_hs256, encode_hs256


class AuthEndpointTestCase(TestCase):
    def test_register_creates_user_with_default_role_and_token(self):
        client = auth_client()

        response = client.post(
            "/api/auth/register/",
            {"username": "new_user", "password": "testpass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["token_type"], "Bearer")
        self.assertIn("access_token", data)
        user = User.objects.get(username="new_user")
        self.assertEqual(user.role.name, "User")
        self.assertTrue(user.check_password("testpass123"))

    def test_register_rejects_duplicate_username(self):
        create_user(username="duplicate")

        response = auth_client().post(
            "/api/auth/register/",
            {"username": "duplicate", "password": "testpass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_token_for_valid_credentials(self):
        create_user(username="login_user", password="testpass123")

        response = auth_client().post(
            "/api/auth/login/",
            {"username": "login_user", "password": "testpass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["token_type"], "Bearer")

    def test_login_rejects_wrong_password_and_inactive_user(self):
        create_user(username="inactive", password="testpass123", is_active=False)
        create_user(username="wrong_password", password="testpass123")

        wrong_password = auth_client().post(
            "/api/auth/login/",
            {"username": "wrong_password", "password": "badpass"},
            format="json",
        )
        inactive = auth_client().post(
            "/api/auth/login/",
            {"username": "inactive", "password": "testpass123"},
            format="json",
        )

        self.assertEqual(wrong_password.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(inactive.status_code, status.HTTP_403_FORBIDDEN)

    def test_me_and_logout_require_authentication(self):
        user = create_user(username="me_user")
        authed = auth_client(user)
        anonymous = auth_client()

        me_response = authed.get("/api/auth/me/")
        logout_response = authed.delete("/api/auth/logout/")
        anonymous_me = anonymous.get("/api/auth/me/")

        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.json()["username"], "me_user")
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(anonymous_me.status_code, status.HTTP_403_FORBIDDEN)


class JWTTestCase(TestCase):
    def test_encode_decode_hs256_round_trip(self):
        token = encode_hs256({"user_id": 123, "exp": int(time.time()) + 60}, "secret")

        payload = decode_hs256(token, "secret")

        self.assertEqual(payload["user_id"], 123)

    def test_decode_rejects_bad_signature_and_expired_token(self):
        valid = encode_hs256({"user_id": 123, "exp": int(time.time()) + 60}, "secret")
        expired = encode_hs256({"user_id": 123, "exp": int(time.time()) - 1}, "secret")

        with self.assertRaises(JWTError):
            decode_hs256(valid, "wrong")
        with self.assertRaises(JWTError):
            decode_hs256(expired, "secret")

    def test_build_access_payload_includes_expiry(self):
        payload = build_access_payload(user_id=5, ttl_seconds=30)

        self.assertEqual(payload["user_id"], 5)
        self.assertGreaterEqual(payload["exp"] - payload["iat"], 30)


class JWTAuthenticationTestCase(TestCase):
    @override_settings(JWT_SECRET="test-secret")
    def test_bearer_token_authenticates_request(self):
        user = create_user(username="jwt_user")
        token = encode_hs256(build_access_payload(user.id, 60), settings.JWT_SECRET)
        client = auth_client()

        response = client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["username"], "jwt_user")

    @override_settings(JWT_SECRET="test-secret")
    def test_invalid_and_inactive_token_users_are_rejected(self):
        inactive = create_user(username="inactive_jwt", is_active=False)
        inactive_token = encode_hs256(build_access_payload(inactive.id, 60), settings.JWT_SECRET)
        bad_payload = encode_hs256({"sub": inactive.id}, settings.JWT_SECRET)
        client = auth_client()

        inactive_response = client.get(
            "/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {inactive_token}"
        )
        bad_payload_response = client.get(
            "/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {bad_payload}"
        )
        malformed_response = client.get("/api/auth/me/", HTTP_AUTHORIZATION="Bearer bad")

        self.assertEqual(inactive_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(bad_payload_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(malformed_response.status_code, status.HTTP_403_FORBIDDEN)
