from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.goods.models import Category, Character, Goods, IP
from apps.users.models import Role, User


class GoodsDraftFlowTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(name="draft-role")
        self.user = User.objects.create(
            username="draft_user",
            password="testpass123",
            role=self.role,
        )
        self.client.force_authenticate(user=self.user)

        self.ip = IP.objects.create(name="Draft IP", subject_type=4)
        self.category = Category.objects.create(name="Draft Category")
        self.character = Character.objects.create(
            ip=self.ip,
            name="Draft Character",
            gender="female",
        )

    def test_create_draft_with_missing_required_fields(self):
        payload = {
            "name": "Draft Goods A",
            "status": "draft",
            "ip_id": self.ip.id,
            "category_id": self.category.id,
            "quantity": 1,
        }

        response = self.client.post("/api/goods/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data.get("saved_as_draft"))
        self.assertEqual(data.get("status"), "draft")

    def test_create_non_draft_requires_required_fields(self):
        payload = {
            "name": "Formal Goods A",
            "status": "in_cabinet",
            "quantity": 1,
        }

        response = self.client.post("/api/goods/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("ip_id", data)
        self.assertIn("character_ids", data)
        self.assertIn("category_id", data)

    def test_create_draft_skips_duplicate_conflict(self):
        goods = Goods.objects.create(
            user=self.user,
            name="Duplicate Draft Goods",
            ip=self.ip,
            category=self.category,
            price=Decimal("66.00"),
            purchase_date=date(2025, 1, 1),
        )
        goods.characters.add(self.character)

        payload = {
            "name": "Duplicate Draft Goods",
            "status": "draft",
            "ip_id": self.ip.id,
            "category_id": self.category.id,
            "character_ids": [self.character.id],
            "price": "66.00",
            "purchase_date": "2025-01-01",
            "merge_strategy": "auto",
        }

        response = self.client.post("/api/goods/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.json().get("saved_as_draft"))

    def test_publish_draft_requires_required_fields(self):
        draft = Goods.objects.create(
            user=self.user,
            name="Draft To Publish",
            ip=self.ip,
            category=self.category,
            status="draft",
        )
        draft.characters.clear()

        response = self.client.patch(
            f"/api/goods/{draft.id}/",
            {"status": "in_cabinet"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("character_ids", response.json())
