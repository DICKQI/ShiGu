from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase
from rest_framework import status

from apps._test_helpers import auth_client, create_user
from apps.goods.models import Character, IP


class BGMApiTestCase(TestCase):
    def setUp(self):
        self.user = create_user(username="bgm_user")
        self.client = auth_client(self.user)

    @patch("apps.goods.views.bgm.search_ip_characters")
    def test_search_characters_success_and_not_found(self, mock_search):
        mock_search.return_value = (
            "Bangumi IP",
            [{"name": "Hero", "relation": "main", "avatar": "https://example.com/a.jpg"}],
        )

        response = self.client.post(
            "/api/bgm/search-characters/",
            {"ip_name": "Bangumi", "subject_type": 4},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["ip_name"], "Bangumi IP")
        mock_search.assert_called_once_with("Bangumi", 4)

        mock_search.return_value = (None, [])
        not_found = self.client.post(
            "/api/bgm/search-characters/",
            {"ip_name": "Missing"},
            format="json",
        )
        self.assertEqual(not_found.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.goods.views.bgm.search_subjects_list")
    def test_search_subjects_success_and_exception(self, mock_search_subjects):
        mock_search_subjects.return_value = [
            {
                "id": 100,
                "name": "Original",
                "name_cn": "CN",
                "type": 4,
                "type_name": "game",
                "image": "https://example.com/cover.jpg",
            }
        ]

        response = self.client.post(
            "/api/bgm/search-subjects/",
            {"keyword": "Original", "subject_type": 4},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["subjects"][0]["id"], 100)
        mock_search_subjects.assert_called_once_with("Original", 4)

        mock_search_subjects.side_effect = RuntimeError("network blocked")
        error_response = self.client.post(
            "/api/bgm/search-subjects/",
            {"keyword": "Original"},
            format="json",
        )
        self.assertEqual(error_response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch("apps.goods.views.bgm.get_characters")
    @patch("apps.goods.views.bgm.get_subject_info")
    def test_get_characters_by_subject_id_success_not_found_and_error(
        self, mock_subject_info, mock_get_characters
    ):
        mock_subject_info.return_value = {"display_name": "Subject Name"}
        mock_get_characters.return_value = [
            {"name": "Hero", "relation": "main", "avatar": "https://example.com/a.jpg"}
        ]

        response = self.client.post(
            "/api/bgm/get-characters-by-id/",
            {"subject_id": 123},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["subject_name"], "Subject Name")
        mock_subject_info.assert_called_once_with(123)
        mock_get_characters.assert_called_once_with(123)

        mock_subject_info.return_value = None
        not_found = self.client.post(
            "/api/bgm/get-characters-by-id/",
            {"subject_id": 404},
            format="json",
        )
        self.assertEqual(not_found.status_code, status.HTTP_404_NOT_FOUND)

        mock_subject_info.side_effect = RuntimeError("service failed")
        error = self.client.post(
            "/api/bgm/get-characters-by-id/",
            {"subject_id": 500},
            format="json",
        )
        self.assertEqual(error.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_create_characters_creates_updates_and_skips_existing_records(self):
        ip = IP.objects.create(name="Existing IP")
        Character.objects.create(ip=ip, name="Existing Hero")

        response = self.client.post(
            "/api/bgm/create-characters/",
            {
                "characters": [
                    {
                        "ip_name": "Existing IP",
                        "character_name": "Existing Hero",
                        "subject_type": 4,
                        "avatar": "https://example.com/existing.jpg",
                    },
                    {
                        "ip_name": "New IP",
                        "character_name": "New Hero",
                        "subject_type": 4,
                        "avatar": "https://example.com/new.jpg",
                    },
                    {
                        "ip_name": "No Avatar IP",
                        "character_name": "No Avatar Hero",
                    },
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["created"], 2)
        self.assertEqual(data["skipped"], 1)
        ip.refresh_from_db()
        self.assertEqual(ip.subject_type, 4)
        existing = Character.objects.get(ip=ip, name="Existing Hero")
        self.assertEqual(existing.avatar, "https://example.com/existing.jpg")
        self.assertTrue(Character.objects.filter(ip__name="New IP", name="New Hero").exists())
