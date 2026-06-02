from __future__ import annotations

from django.test import TestCase
from rest_framework import status

from apps._test_helpers import (
    TempMediaRootMixin,
    add_showcase_goods,
    auth_client,
    create_admin_user,
    create_goods,
    create_showcase,
    create_theme,
    create_user,
    uploaded_image,
)
from apps.goods.models import ShowcaseGoods, ThemeImage


class ThemeApiTestCase(TempMediaRootMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = create_user(username="theme_user")
        self.other_user = create_user(username="other_theme_user")
        self.admin = create_admin_user(username="theme_admin")
        self.client = auth_client(self.user)
        self.other_client = auth_client(self.other_user)
        self.admin_client = auth_client(self.admin)
        self.theme = create_theme(self.user, name="Theme A")
        self.other_theme = create_theme(self.other_user, name="Theme B")

    def test_theme_crud_is_scoped_to_owner_and_admin_sees_all(self):
        list_response = self.client.get("/api/themes/")
        admin_list_response = self.admin_client.get("/api/themes/")
        other_detail_response = self.client.get(f"/api/themes/{self.other_theme.id}/")
        create_response = self.client.post(
            "/api/themes/",
            {"name": "Created Theme", "description": "created"},
            format="json",
        )
        patch_response = self.client.patch(
            f"/api/themes/{self.theme.id}/",
            {"description": "updated"},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.json()), 1)
        self.assertEqual(admin_list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(admin_list_response.json()), 2)
        self.assertEqual(other_detail_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.json()["description"], "updated")

    def test_non_admin_cannot_assign_theme_user_but_admin_can(self):
        user_response = self.client.post(
            "/api/themes/",
            {"name": "Bad Assigned Theme", "user_id": self.other_user.id},
            format="json",
        )
        admin_response = self.admin_client.post(
            "/api/themes/",
            {"name": "Admin Assigned Theme", "user_id": self.other_user.id},
            format="json",
        )

        self.assertEqual(user_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(admin_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.other_user.themes.filter(name="Admin Assigned Theme").exists())

    def test_theme_image_upload_update_and_delete(self):
        upload_response = self.client.post(
            f"/api/themes/{self.theme.id}/upload-images/",
            {"additional_photos": [uploaded_image("theme.jpg")], "label": "poster"},
            format="multipart",
        )
        image = ThemeImage.objects.get(theme=self.theme)
        label_response = self.client.post(
            f"/api/themes/{self.theme.id}/upload-images/",
            {"photo_ids": [str(image.id)], "label": "updated"},
            format="multipart",
        )
        image.refresh_from_db()
        delete_response = self.client.delete(f"/api/themes/{self.theme.id}/images/{image.id}/")

        self.assertEqual(upload_response.status_code, status.HTTP_200_OK)
        self.assertEqual(label_response.status_code, status.HTTP_200_OK)
        self.assertEqual(image.label, "updated")
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        self.assertFalse(ThemeImage.objects.filter(id=image.id).exists())

    def test_theme_image_upload_validates_inputs(self):
        missing_response = self.client.post(
            f"/api/themes/{self.theme.id}/upload-images/",
            {},
            format="multipart",
        )
        bad_id_response = self.client.post(
            f"/api/themes/{self.theme.id}/upload-images/",
            {"photo_ids": ["999999"], "label": "bad"},
            format="multipart",
        )
        delete_missing_response = self.client.delete(
            f"/api/themes/{self.theme.id}/images/999999/"
        )

        self.assertEqual(missing_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_id_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(delete_missing_response.status_code, status.HTTP_404_NOT_FOUND)


class ShowcaseApiTestCase(TempMediaRootMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = create_user(username="showcase_user")
        self.other_user = create_user(username="other_showcase_user")
        self.admin = create_admin_user(username="showcase_admin")
        self.client = auth_client(self.user)
        self.other_client = auth_client(self.other_user)
        self.admin_client = auth_client(self.admin)
        self.goods = create_goods(self.user, name="Showcase Goods")
        self.second_goods = create_goods(self.user, name="Second Showcase Goods")
        self.other_goods = create_goods(self.other_user, name="Other Showcase Goods")
        self.public_showcase = create_showcase(self.user, name="Public Showcase", is_public=True)
        self.private_showcase = create_showcase(self.user, name="Private Showcase", is_public=False)
        self.other_private = create_showcase(self.other_user, name="Other Private", is_public=False)
        self.other_public = create_showcase(self.other_user, name="Other Public", is_public=True)

    def test_showcase_list_detail_public_private_visibility(self):
        list_response = self.client.get("/api/showcases/")
        public_response = auth_client().get("/api/showcases/public/")
        private_response = self.client.get("/api/showcases/private/")
        other_private_detail = self.client.get(f"/api/showcases/{self.other_private.id}/")
        other_public_detail = self.client.get(f"/api/showcases/{self.other_public.id}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.json()["count"], 3)
        self.assertEqual(public_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["name"] for item in public_response.json()["results"]},
            {"Public Showcase", "Other Public"},
        )
        self.assertEqual(private_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["name"] for item in private_response.json()["results"]},
            {"Public Showcase", "Private Showcase"},
        )
        self.assertEqual(other_private_detail.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(other_public_detail.status_code, status.HTTP_200_OK)

    def test_create_update_and_cover_upload(self):
        create_response = self.client.post(
            "/api/showcases/",
            {"name": "Created Showcase", "description": "created", "is_public": False},
            format="json",
        )
        showcase_id = create_response.json()["id"]
        patch_response = self.client.patch(
            f"/api/showcases/{showcase_id}/",
            {"is_public": True},
            format="json",
        )
        cover_response = self.client.post(
            f"/api/showcases/{showcase_id}/upload-cover-image/",
            {"cover_image": uploaded_image("cover.jpg")},
            format="multipart",
        )
        missing_cover_response = self.client.post(
            f"/api/showcases/{showcase_id}/upload-cover-image/",
            {},
            format="multipart",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertTrue(patch_response.json()["is_public"])
        self.assertEqual(cover_response.status_code, status.HTTP_200_OK)
        self.assertTrue(cover_response.json()["cover_image"])
        self.assertEqual(missing_cover_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_remove_move_goods_and_duplicate_cross_user_rules(self):
        add_response = self.client.post(
            f"/api/showcases/{self.public_showcase.id}/add-goods/",
            {"goods_id": str(self.goods.id), "notes": "first"},
            format="json",
        )
        duplicate_response = self.client.post(
            f"/api/showcases/{self.public_showcase.id}/add-goods/",
            {"goods_id": str(self.goods.id)},
            format="json",
        )
        second_add_response = self.client.post(
            f"/api/showcases/{self.public_showcase.id}/add-goods/",
            {"goods_id": str(self.second_goods.id)},
            format="json",
        )
        cross_user_response = self.client.post(
            f"/api/showcases/{self.public_showcase.id}/add-goods/",
            {"goods_id": str(self.other_goods.id)},
            format="json",
        )
        goods_response = self.client.get(f"/api/showcases/{self.public_showcase.id}/goods/")
        move_response = self.client.post(
            f"/api/showcases/{self.public_showcase.id}/move-goods/",
            {
                "goods_id": str(self.goods.id),
                "anchor_goods_id": str(self.second_goods.id),
                "position": "after",
            },
            format="json",
        )
        self_move_response = self.client.post(
            f"/api/showcases/{self.public_showcase.id}/move-goods/",
            {
                "goods_id": str(self.goods.id),
                "anchor_goods_id": str(self.goods.id),
                "position": "after",
            },
            format="json",
        )
        remove_response = self.client.post(
            f"/api/showcases/{self.public_showcase.id}/remove-goods/",
            {"goods_id": str(self.goods.id)},
            format="json",
        )
        remove_missing_response = self.client.post(
            f"/api/showcases/{self.public_showcase.id}/remove-goods/",
            {"goods_id": str(self.goods.id)},
            format="json",
        )

        self.assertEqual(add_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(second_add_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(cross_user_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(goods_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(goods_response.json()), 2)
        self.assertEqual(move_response.status_code, status.HTTP_200_OK)
        self.assertEqual(self_move_response.status_code, status.HTTP_200_OK)
        self.assertEqual(remove_response.status_code, status.HTTP_200_OK)
        self.assertEqual(remove_missing_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_modify_showcase_even_when_public(self):
        response = self.other_client.patch(
            f"/api/showcases/{self.public_showcase.id}/",
            {"description": "bad"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_showcase_goods_relation_cascades_when_goods_deleted(self):
        relation = add_showcase_goods(self.public_showcase, self.goods)

        self.goods.delete()

        self.assertFalse(ShowcaseGoods.objects.filter(id=relation.id).exists())
