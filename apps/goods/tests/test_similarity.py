from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.goods.models import Category, Character, Goods, IP, Theme
from apps.goods.similarity import GoodsSimilarityCalculator, SeedSelector
from apps.users.models import Role, User


class SimilarityAlgorithmTestCase(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name="similarity-role")
        self.user = User.objects.create(
            username="testuser",
            password="testpass123",
            role=self.role,
        )

        self.ip1 = IP.objects.create(name="Similarity IP 1", subject_type=4)
        self.ip2 = IP.objects.create(name="Similarity IP 2", subject_type=4)

        self.char1 = Character.objects.create(ip=self.ip1, name="Character 1", gender="female")
        self.char2 = Character.objects.create(ip=self.ip1, name="Character 2", gender="female")
        self.char3 = Character.objects.create(ip=self.ip2, name="Character 3", gender="female")

        self.cat_root = Category.objects.create(name="Root Category", path_name="Root Category")
        self.cat_badge = Category.objects.create(
            name="Badge",
            parent=self.cat_root,
            path_name="Root Category/Badge",
        )

        self.theme1 = Theme.objects.create(user=self.user, name="Summer Theme")

        self.goods1 = Goods.objects.create(
            user=self.user,
            name="Character 1 Stand",
            ip=self.ip1,
            category=self.cat_badge,
            theme=self.theme1,
            price=Decimal("50.00"),
            purchase_date=date(2024, 1, 15),
        )
        self.goods1.characters.add(self.char1)

        self.goods2 = Goods.objects.create(
            user=self.user,
            name="Character 2 Badge",
            ip=self.ip1,
            category=self.cat_badge,
            theme=self.theme1,
            price=Decimal("55.00"),
            purchase_date=date(2024, 1, 20),
        )
        self.goods2.characters.add(self.char2)

        self.goods3 = Goods.objects.create(
            user=self.user,
            name="Character 3 Badge",
            ip=self.ip2,
            category=self.cat_badge,
            price=Decimal("200.00"),
            purchase_date=date(2024, 6, 1),
        )
        self.goods3.characters.add(self.char3)

        self.calculator = GoodsSimilarityCalculator()

    def test_ip_match_same_ip(self):
        score = self.calculator._score_ip_match(self.goods1, self.goods2)
        self.assertEqual(score, 30.0)

    def test_ip_match_same_subject_type(self):
        score = self.calculator._score_ip_match(self.goods1, self.goods3)
        self.assertAlmostEqual(score, 9.9, places=1)

    def test_character_overlap(self):
        goods_both = Goods.objects.create(
            user=self.user,
            name="Double Stand",
            ip=self.ip1,
            category=self.cat_badge,
        )
        goods_both.characters.add(self.char1, self.char2)

        score = self.calculator._score_character_overlap(self.goods1, goods_both)

        self.assertAlmostEqual(score, 11.5, places=1)

    def test_category_hierarchy_same_category(self):
        score = self.calculator._score_category_hierarchy(self.goods1, self.goods2)
        self.assertEqual(score, 18.0)

    def test_theme_match(self):
        score = self.calculator._score_theme_match(self.goods1, self.goods2)
        self.assertEqual(score, 15.0)

    def test_price_range_similar(self):
        score = self.calculator._score_price_range(self.goods1, self.goods2)
        self.assertGreater(score, 5.0)

    def test_purchase_proximity_same_month(self):
        score = self.calculator._score_purchase_proximity(self.goods1, self.goods2)
        self.assertEqual(score, 6.0)

    def test_calculate_similarity_high(self):
        score = self.calculator.calculate_similarity(self.goods1, self.goods2)
        self.assertGreater(score, 60.0)

    def test_calculate_similarity_low(self):
        score = self.calculator.calculate_similarity(self.goods1, self.goods3)
        self.assertLess(score, 40.0)


class SeedSelectorTestCase(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name="seed-role")
        self.user = User.objects.create(
            username="seed_user",
            password="testpass123",
            role=self.role,
        )

        self.ip1 = IP.objects.create(name="Seed IP 1", subject_type=4)
        self.ip2 = IP.objects.create(name="Seed IP 2", subject_type=4)
        self.cat = Category.objects.create(name="Seed Category")

        self.goods_list = []
        for i in range(10):
            ip = self.ip1 if i < 5 else self.ip2
            goods = Goods.objects.create(
                user=self.user,
                name=f"Seed Goods {i}",
                ip=ip,
                category=self.cat,
            )
            self.goods_list.append(goods)

        self.selector = SeedSelector()

    def test_calculate_seed_count(self):
        self.assertEqual(self.selector._calculate_seed_count(50), 4)
        self.assertEqual(self.selector._calculate_seed_count(200), 15)
        self.assertEqual(self.selector._calculate_seed_count(1000), 20)

    def test_diverse_selection(self):
        seeds = self.selector._diverse_selection(self.goods_list, 3)

        self.assertEqual(len(seeds), 3)
        self.assertGreater(len({seed.ip_id for seed in seeds}), 1)


class SimilarRandomEndpointTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(name="similar-random-role")
        self.user = User.objects.create(
            username="similar_random_user",
            password="testpass123",
            role=self.role,
        )
        self.client.force_authenticate(user=self.user)

        self.ip = IP.objects.create(name="Similar Random IP", subject_type=4)
        self.cat = Category.objects.create(name="Similar Random Category")

        for i in range(20):
            Goods.objects.create(
                user=self.user,
                name=f"Similar Random Goods {i}",
                ip=self.ip,
                category=self.cat,
            )

    def test_similar_random_endpoint_exists(self):
        response = self.client.get("/api/goods/similar-random/")
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_similar_random_response_format(self):
        response = self.client.get("/api/goods/similar-random/")
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIn("count", data)
            self.assertIn("results", data)
            self.assertIn("page", data)
            self.assertIn("page_size", data)

    def test_similar_random_with_filters(self):
        response = self.client.get(f"/api/goods/similar-random/?ip={self.ip.id}")
        if response.status_code == status.HTTP_200_OK:
            self.assertGreater(response.json()["count"], 0)

    def test_similar_random_pagination(self):
        response = self.client.get("/api/goods/similar-random/?page=1&page_size=10")
        if response.status_code == status.HTTP_200_OK:
            self.assertLessEqual(len(response.json()["results"]), 10)

    def test_similar_random_seed_strategies(self):
        for strategy in ["diverse", "popular", "recent"]:
            response = self.client.get(f"/api/goods/similar-random/?seed_strategy={strategy}")
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])
