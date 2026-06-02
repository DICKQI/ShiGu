from __future__ import annotations

from django.test import TestCase
from rest_framework import status

from apps._test_helpers import auth_client, create_admin_user, create_role, create_user
from apps.users.models import User


class AdminApiTestCase(TestCase):
    def setUp(self):
        self.admin = create_admin_user(username="admin_user")
        self.user = create_user(username="normal_user")
        self.user_role = create_role("User")
        self.admin_client = auth_client(self.admin)
        self.user_client = auth_client(self.user)
        self.anonymous_client = auth_client()

    def test_admin_user_list_requires_admin(self):
        admin_response = self.admin_client.get("/api/admin/users/")
        user_response = self.user_client.get("/api/admin/users/")
        anonymous_response = self.anonymous_client.get("/api/admin/users/")

        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(anonymous_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_user_without_password_in_response(self):
        response = self.admin_client.post(
            "/api/admin/users/",
            {
                "username": "created_by_admin",
                "password": "testpass123",
                "role_id": self.user_role.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["username"], "created_by_admin")
        self.assertNotIn("password", data)
        created = User.objects.get(username="created_by_admin")
        self.assertTrue(created.check_password("testpass123"))

    def test_admin_can_update_role_password_and_active_state(self):
        new_role = create_role("Editor")

        response = self.admin_client.patch(
            f"/api/admin/users/{self.user.id}/",
            {"role_id": new_role.id, "password": "newpass123", "is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role_id, new_role.id)
        self.assertFalse(self.user.is_active)
        self.assertTrue(self.user.check_password("newpass123"))

    def test_admin_roles_list_requires_admin(self):
        admin_response = self.admin_client.get("/api/admin/roles/")
        user_response = self.user_client.get("/api/admin/roles/")

        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertGreaterEqual(len(admin_response.json()), 1)
