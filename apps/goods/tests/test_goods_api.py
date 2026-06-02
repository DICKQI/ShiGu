from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status

from apps._test_helpers import (
    TempMediaRootMixin,
    auth_client,
    create_admin_user,
    create_category,
    create_character,
    create_goods,
    create_ip,
    create_storage_node,
    create_theme,
    create_user,
    uploaded_image,
)
from apps.goods.models import Goods, GuziImage


class GoodsApiTestCase(TempMediaRootMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = create_user(username="goods_user")
        self.other_user = create_user(username="other_goods_user")
        self.admin = create_admin_user(username="goods_admin")
        self.client = auth_client(self.user)
        self.other_client = auth_client(self.other_user)
        self.admin_client = auth_client(self.admin)

        self.ip = create_ip(name="Goods IP", keywords=("goods-keyword",))
        self.other_ip = create_ip(name="Other Goods IP", subject_type=2)
        self.character = create_character(ip=self.ip, name="Goods Hero")
        self.other_character = create_character(ip=self.other_ip, name="Other Villain")
        self.category_root = create_category(name="Goods Category")
        self.category_child = create_category(name="Goods Child Category", parent=self.category_root)
        self.other_category = create_category(name="Other Category")
        self.location_root = create_storage_node(self.user, name="Goods Room")
        self.location_child = create_storage_node(self.user, name="Goods Shelf", parent=self.location_root)
        self.other_location = create_storage_node(self.other_user, name="Other Room")
        self.theme = create_theme(self.user, name="Goods Theme")
        self.other_theme = create_theme(self.other_user, name="Other Theme")

        self.goods = create_goods(
            self.user,
            name="Primary Goods",
            ip=self.ip,
            category=self.category_child,
            characters=[self.character],
            location=self.location_child,
            theme=self.theme,
            quantity=2,
            price=Decimal("12.50"),
            purchase_date=date(2025, 1, 15),
            is_official=True,
            status="in_cabinet",
            order=1000,
        )
        self.sold_goods = create_goods(
            self.user,
            name="Sold Goods",
            ip=self.other_ip,
            category=self.other_category,
            characters=[self.other_character],
            quantity=1,
            price=Decimal("20.00"),
            purchase_date=date(2025, 2, 10),
            is_official=False,
            status="sold",
            order=2000,
        )
        self.other_user_goods = create_goods(
            self.other_user,
            name="Other User Goods",
            ip=self.ip,
            category=self.category_child,
            characters=[self.character],
            location=self.other_location,
        )

    def test_protected_list_requires_authentication_and_scopes_by_user(self):
        anonymous_response = auth_client().get("/api/goods/")
        user_response = self.client.get("/api/goods/")
        admin_response = self.admin_client.get("/api/goods/")

        self.assertEqual(anonymous_response.status_code, status.HTTP_200_OK)
        self.assertEqual(anonymous_response.json()["count"], 0)
        self.assertEqual(user_response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_response.json()["count"], 2)
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertEqual(admin_response.json()["count"], 3)

    def test_list_pagination_shape(self):
        response = self.client.get("/api/goods/?page=1&page_size=1")
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(data), {"count", "page", "page_size", "next", "previous", "results"})
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 1)
        self.assertEqual(len(data["results"]), 1)

    def test_filters_and_search_return_expected_goods(self):
        cases = [
            (f"/api/goods/?ip={self.ip.id}", {"Primary Goods"}),
            (f"/api/goods/?character={self.character.id}", {"Primary Goods"}),
            (f"/api/goods/?category={self.category_root.id}", {"Primary Goods"}),
            (f"/api/goods/?location={self.location_root.id}", {"Primary Goods"}),
            (f"/api/goods/?theme={self.theme.id}", {"Primary Goods"}),
            ("/api/goods/?status=sold", {"Sold Goods"}),
            ("/api/goods/?status__in=in_cabinet,sold", {"Primary Goods", "Sold Goods"}),
            ("/api/goods/?is_official=false", {"Sold Goods"}),
            ("/api/goods/?search=goods-keyword", {"Primary Goods"}),
            ("/api/goods/?search=Goods Hero", {"Primary Goods"}),
        ]

        for url, expected_names in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                names = {item["name"] for item in response.json()["results"]}
                self.assertEqual(names, expected_names)

    def test_group_by_validates_value_and_returns_paginated_shape(self):
        valid_response = self.client.get("/api/goods/?group_by=ip")
        invalid_response = self.client.get("/api/goods/?group_by=bad")

        self.assertEqual(valid_response.status_code, status.HTTP_200_OK)
        self.assertIn("results", valid_response.json())
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_retrieve_patch_and_delete_goods(self):
        payload = {
            "name": "Created Goods",
            "ip_id": self.ip.id,
            "character_ids": [self.character.id],
            "category_id": self.category_child.id,
            "theme_id": self.theme.id,
            "location": self.location_child.id,
            "quantity": 3,
            "price": "33.30",
            "purchase_date": "2025-03-01",
            "status": "in_cabinet",
            "merge_strategy": "new",
        }

        create_response = self.client.post("/api/goods/", payload, format="json")
        goods_id = create_response.json()["id"]
        retrieve_response = self.client.get(f"/api/goods/{goods_id}/")
        patch_response = self.client.patch(
            f"/api/goods/{goods_id}/",
            {"quantity": 5, "character_ids": [self.character.id, self.other_character.id]},
            format="json",
        )
        delete_response = self.client.delete(f"/api/goods/{goods_id}/")

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.json()["quantity"], 5)
        self.assertEqual(len(patch_response.json()["characters"]), 2)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_non_admin_cannot_reference_other_users_private_theme_or_location(self):
        response = self.client.post(
            "/api/goods/",
            {
                "name": "Cross Private Goods",
                "ip_id": self.ip.id,
                "character_ids": [self.character.id],
                "category_id": self.category_child.id,
                "theme_id": self.other_theme.id,
                "location": self.other_location.id,
                "merge_strategy": "new",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("theme_id", response.json())
        self.assertIn("location", response.json())

    def test_admin_can_create_goods_for_specified_user(self):
        response = self.admin_client.post(
            "/api/goods/",
            {
                "name": "Admin Assigned Goods",
                "ip_id": self.ip.id,
                "character_ids": [self.character.id],
                "category_id": self.category_child.id,
                "user_id": self.other_user.id,
                "merge_strategy": "new",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Goods.objects.get(id=response.json()["id"])
        self.assertEqual(created.user_id, self.other_user.id)

    def test_duplicate_auto_merge_and_new_strategies(self):
        duplicate_payload = {
            "name": self.goods.name,
            "ip_id": self.ip.id,
            "character_ids": [self.character.id],
            "category_id": self.category_child.id,
            "quantity": 4,
            "price": "12.50",
            "purchase_date": "2025-01-15",
        }

        auto_response = self.client.post(
            "/api/goods/",
            {**duplicate_payload, "merge_strategy": "auto"},
            format="json",
        )
        merge_response = self.client.post(
            "/api/goods/",
            {**duplicate_payload, "merge_strategy": "merge"},
            format="json",
        )
        new_response = self.client.post(
            "/api/goods/",
            {**duplicate_payload, "merge_strategy": "new"},
            format="json",
        )

        self.goods.refresh_from_db()
        self.assertEqual(auto_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(auto_response.json()["code"], "goods_duplicate")
        self.assertEqual(merge_response.status_code, status.HTTP_200_OK)
        self.assertTrue(merge_response.json()["merged"])
        self.assertEqual(self.goods.quantity, 6)
        self.assertEqual(new_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Goods.objects.filter(user=self.user, name=self.goods.name).count(), 2)

    def test_merge_requires_target_when_multiple_candidates(self):
        duplicate = create_goods(
            self.user,
            name="Multi Duplicate",
            ip=self.ip,
            category=self.category_child,
            characters=[self.character],
            price=Decimal("9.00"),
            purchase_date=date(2025, 4, 1),
        )
        second_duplicate = create_goods(
            self.user,
            name="Multi Duplicate",
            ip=self.ip,
            category=self.category_child,
            characters=[self.character],
            price=Decimal("9.00"),
            purchase_date=date(2025, 4, 1),
        )

        base_payload = {
            "name": "Multi Duplicate",
            "ip_id": self.ip.id,
            "character_ids": [self.character.id],
            "category_id": self.category_child.id,
            "quantity": 2,
            "price": "9.00",
            "purchase_date": "2025-04-01",
            "merge_strategy": "merge",
        }
        missing_target = self.client.post("/api/goods/", base_payload, format="json")
        bad_target = self.client.post(
            "/api/goods/",
            {**base_payload, "merge_target_id": str(self.goods.id)},
            format="json",
        )
        good_target = self.client.post(
            "/api/goods/",
            {**base_payload, "merge_target_id": str(second_duplicate.id)},
            format="json",
        )

        second_duplicate.refresh_from_db()
        duplicate.refresh_from_db()
        self.assertEqual(missing_target.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_target.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(good_target.status_code, status.HTTP_200_OK)
        self.assertEqual(second_duplicate.quantity, 3)
        self.assertEqual(duplicate.quantity, 1)

    def test_draft_creation_and_publish_validation(self):
        draft_response = self.client.post(
            "/api/goods/",
            {
                "name": "Draft Goods",
                "status": "draft",
                "ip_id": self.ip.id,
                "category_id": self.category_child.id,
            },
            format="json",
        )
        draft_id = draft_response.json()["id"]
        publish_fail = self.client.patch(
            f"/api/goods/{draft_id}/",
            {"status": "in_cabinet"},
            format="json",
        )
        publish_success = self.client.patch(
            f"/api/goods/{draft_id}/",
            {"status": "in_cabinet", "character_ids": [self.character.id]},
            format="json",
        )

        self.assertEqual(draft_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(draft_response.json()["saved_as_draft"])
        self.assertEqual(publish_fail.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("character_ids", publish_fail.json())
        self.assertEqual(publish_success.status_code, status.HTTP_200_OK)
        self.assertEqual(publish_success.json()["status"], "in_cabinet")

    def test_move_before_after_self_invalid_and_cross_user_anchor(self):
        first = create_goods(
            self.user,
            name="Move First",
            ip=self.ip,
            category=self.category_child,
            characters=[self.character],
            order=100,
        )
        second = create_goods(
            self.user,
            name="Move Second",
            ip=self.ip,
            category=self.category_child,
            characters=[self.character],
            order=200,
        )
        third = create_goods(
            self.user,
            name="Move Third",
            ip=self.ip,
            category=self.category_child,
            characters=[self.character],
            order=300,
        )

        before_response = self.client.post(
            f"/api/goods/{third.id}/move/",
            {"anchor_id": str(first.id), "position": "before"},
            format="json",
        )
        after_response = self.client.post(
            f"/api/goods/{first.id}/move/",
            {"anchor_id": str(second.id), "position": "after"},
            format="json",
        )
        self_response = self.client.post(
            f"/api/goods/{second.id}/move/",
            {"anchor_id": str(second.id), "position": "after"},
            format="json",
        )
        missing_anchor = self.client.post(
            f"/api/goods/{second.id}/move/",
            {"anchor_id": "00000000-0000-0000-0000-000000000000", "position": "after"},
            format="json",
        )
        cross_user_anchor = self.client.post(
            f"/api/goods/{second.id}/move/",
            {"anchor_id": str(self.other_user_goods.id), "position": "after"},
            format="json",
        )

        self.assertEqual(before_response.status_code, status.HTTP_200_OK)
        self.assertEqual(after_response.status_code, status.HTTP_200_OK)
        self.assertEqual(self_response.status_code, status.HTTP_200_OK)
        self.assertEqual(missing_anchor.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(cross_user_anchor.status_code, status.HTTP_404_NOT_FOUND)

    def test_stats_returns_overview_distributions_trends_and_defaults_group_by(self):
        response = self.client.get(
            "/api/goods/stats/?purchase_start=2025-01-01&purchase_end=2025-01-31&group_by=bad&top=1"
        )
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["meta"]["group_by"], "month")
        self.assertEqual(data["meta"]["top"], 1)
        self.assertEqual(data["overview"]["goods_count"], 1)
        self.assertIn("status", data["distributions"])
        self.assertIn("purchase_date", data["trends"])
        self.assertGreaterEqual(len(data["trends"]["purchase_date"]), 1)

    def test_media_upload_actions_use_temp_media_root(self):
        main_response = self.client.post(
            f"/api/goods/{self.goods.id}/upload-main-photo/",
            {"main_photo": uploaded_image("main.jpg")},
            format="multipart",
        )
        additional_response = self.client.post(
            f"/api/goods/{self.goods.id}/upload-additional-photos/",
            {"additional_photos": [uploaded_image("extra.jpg")], "label": "detail"},
            format="multipart",
        )
        label_response = self.client.post(
            f"/api/goods/{self.goods.id}/upload-additional-photos/",
            {"photo_ids": [str(GuziImage.objects.get(guzi=self.goods).id)], "label": "updated"},
            format="multipart",
        )

        self.goods.refresh_from_db()
        image = GuziImage.objects.get(guzi=self.goods)
        self.assertEqual(main_response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.goods.main_photo.name)
        self.assertEqual(additional_response.status_code, status.HTTP_200_OK)
        self.assertEqual(label_response.status_code, status.HTTP_200_OK)
        image.refresh_from_db()
        self.assertEqual(image.label, "updated")

    def test_media_upload_actions_validate_required_files_and_ids(self):
        missing_main = self.client.post(
            f"/api/goods/{self.goods.id}/upload-main-photo/",
            {},
            format="multipart",
        )
        missing_additional = self.client.post(
            f"/api/goods/{self.goods.id}/upload-additional-photos/",
            {},
            format="multipart",
        )
        bad_photo_id = self.client.post(
            f"/api/goods/{self.goods.id}/upload-additional-photos/",
            {"photo_ids": ["999999"], "label": "bad"},
            format="multipart",
        )

        self.assertEqual(missing_main.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing_additional.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_photo_id.status_code, status.HTTP_400_BAD_REQUEST)
