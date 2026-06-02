from __future__ import annotations

from django.test import TestCase
from rest_framework import status

from apps._test_helpers import (
    auth_client,
    create_admin_user,
    create_category,
    create_character,
    create_goods,
    create_ip,
    create_user,
)
from apps.goods.models import Category, IP, IPKeyword


class MetadataPermissionTestCase(TestCase):
    def setUp(self):
        self.admin = create_admin_user(username="metadata_admin")
        self.user = create_user(username="metadata_user")
        self.admin_client = auth_client(self.admin)
        self.user_client = auth_client(self.user)

    def test_metadata_read_requires_auth_and_write_requires_admin(self):
        create_ip(name="Readable IP")

        anonymous_response = auth_client().get("/api/ips/")
        user_get_response = self.user_client.get("/api/ips/")
        user_post_response = self.user_client.post(
            "/api/ips/",
            {"name": "User Cannot Create", "subject_type": 4},
            format="json",
        )
        admin_post_response = self.admin_client.post(
            "/api/ips/",
            {"name": "Admin Can Create", "subject_type": 4},
            format="json",
        )

        self.assertEqual(anonymous_response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_post_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(admin_post_response.status_code, status.HTTP_201_CREATED)


class IPApiTestCase(TestCase):
    def setUp(self):
        self.admin = create_admin_user(username="ip_admin")
        self.client = auth_client(self.admin)

    def test_create_update_search_and_characters_for_ip(self):
        create_ip(name="Other IP", keywords=("searchable",))

        create_response = self.client.post(
            "/api/ips/",
            {
                "name": "Test IP",
                "subject_type": 4,
                "keywords": [" alias ", "alias", "", "short"],
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        ip_id = create_response.json()["id"]
        self.assertEqual(
            set(IPKeyword.objects.filter(ip_id=ip_id).values_list("value", flat=True)),
            {"alias", "short"},
        )

        update_response = self.client.patch(
            f"/api/ips/{ip_id}/",
            {"keywords": ["short", "new"]},
            format="json",
        )
        search_response = self.client.get("/api/ips/?search=new")
        create_character(ip=IP.objects.get(id=ip_id), name="IP Character")
        characters_response = self.client.get(f"/api/ips/{ip_id}/characters/")

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(IPKeyword.objects.filter(ip_id=ip_id).values_list("value", flat=True)),
            {"short", "new"},
        )
        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(search_response.json()), 1)
        self.assertEqual(characters_response.status_code, status.HTTP_200_OK)
        self.assertEqual(characters_response.json()[0]["name"], "IP Character")

    def test_batch_update_order_validates_duplicates_and_missing_ids(self):
        first = create_ip(name="Order IP 1", order=10)
        second = create_ip(name="Order IP 2", order=20)

        duplicate_response = self.client.post(
            "/api/ips/batch-update-order/",
            {"items": [{"id": first.id, "order": 2}, {"id": first.id, "order": 1}]},
            format="json",
        )
        missing_response = self.client.post(
            "/api/ips/batch-update-order/",
            {"items": [{"id": 999999, "order": 1}]},
            format="json",
        )
        success_response = self.client.post(
            "/api/ips/batch-update-order/",
            {"items": [{"id": first.id, "order": 200}, {"id": second.id, "order": 100}]},
            format="json",
        )

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(success_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first.order, 200)
        self.assertEqual(second.order, 100)


class CharacterApiTestCase(TestCase):
    def setUp(self):
        self.admin = create_admin_user(username="character_admin")
        self.client = auth_client(self.admin)
        self.ip = create_ip(name="Character IP", keywords=("char-keyword",))

    def test_character_crud_filter_and_search(self):
        create_response = self.client.post(
            "/api/characters/",
            {
                "name": "Hero",
                "ip_id": self.ip.id,
                "gender": "female",
                "avatar": "https://example.com/hero.jpg",
            },
            format="json",
        )

        filter_response = self.client.get(f"/api/characters/?ip={self.ip.id}")
        search_response = self.client.get("/api/characters/?search=char-keyword")
        patch_response = self.client.patch(
            f"/api/characters/{create_response.json()['id']}/",
            {"gender": "other"},
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.json()["avatar"], "https://example.com/hero.jpg")
        self.assertEqual(filter_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(filter_response.json()), 1)
        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(search_response.json()), 1)
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.json()["gender"], "other")


class CategoryApiTestCase(TestCase):
    def setUp(self):
        self.admin = create_admin_user(username="category_admin")
        self.client = auth_client(self.admin)

    def test_category_tree_path_generation_and_update(self):
        root_response = self.client.post(
            "/api/categories/",
            {"name": "Merch", "color_tag": "#FF0000", "order": 1},
            format="json",
        )
        self.assertEqual(root_response.status_code, status.HTTP_201_CREATED)
        root_id = root_response.json()["id"]
        self.assertEqual(root_response.json()["path_name"], "Merch")

        child_response = self.client.post(
            "/api/categories/",
            {"name": "Badge", "parent": root_id},
            format="json",
        )
        tree_response = self.client.get("/api/categories/tree/")
        patch_response = self.client.patch(
            f"/api/categories/{child_response.json()['id']}/",
            {"name": "Round Badge"},
            format="json",
        )

        self.assertEqual(child_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(child_response.json()["path_name"], "Merch/Badge")
        self.assertEqual(tree_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(tree_response.json()), 2)
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.json()["path_name"], "Merch/Round Badge")

    def test_batch_update_order_and_destroy_protection(self):
        root = create_category(name="Root", order=10)
        child = create_category(name="Child", parent=root, order=20)
        goods_owner = create_user(username="category_goods_owner")
        create_goods(goods_owner, category=child)

        duplicate_response = self.client.post(
            "/api/categories/batch-update-order/",
            {"items": [{"id": root.id, "order": 2}, {"id": root.id, "order": 1}]},
            format="json",
        )
        success_response = self.client.post(
            "/api/categories/batch-update-order/",
            {"items": [{"id": root.id, "order": 200}, {"id": child.id, "order": 100}]},
            format="json",
        )
        delete_response = self.client.delete(f"/api/categories/{root.id}/")

        root.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(success_response.status_code, status.HTTP_200_OK)
        self.assertEqual(child.order, 100)
        self.assertEqual(root.order, 200)
        self.assertEqual(delete_response.status_code, status.HTTP_400_BAD_REQUEST)
