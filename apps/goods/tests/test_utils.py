from __future__ import annotations

import random
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from PIL import Image
from rest_framework import serializers

from apps._test_helpers import TempMediaRootMixin, uploaded_image
from apps.goods.serializers.fields import AvatarField, KeywordsField
from apps.goods.utils import compress_image


class CompressImageTestCase(TestCase):
    def test_compress_image_returns_none_for_empty_or_small_image(self):
        self.assertIsNone(compress_image(None))
        self.assertIsNone(compress_image(uploaded_image("small.jpg"), max_size_kb=300))

    def test_compress_image_returns_jpeg_when_image_exceeds_limit(self):
        random.seed(1)
        image = Image.new("RGB", (900, 900))
        image.putdata(
            [
                (
                    random.randrange(256),
                    random.randrange(256),
                    random.randrange(256),
                )
                for _ in range(900 * 900)
            ]
        )
        image_io = BytesIO()
        image.save(image_io, format="JPEG", quality=95)
        image_file = SimpleUploadedFile(
            "large.jpg", image_io.getvalue(), content_type="image/jpeg"
        )

        compressed = compress_image(image_file, max_size_kb=20)

        self.assertIsNotNone(compressed)
        self.assertTrue(compressed.name.endswith(".jpg"))
        self.assertLessEqual(compressed.size, 20 * 1024)


class SerializerFieldTestCase(TempMediaRootMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_keywords_field_accepts_list_and_deduplicates(self):
        field = KeywordsField()

        self.assertEqual(field.to_internal_value([" a ", "a", "", None, "b"]), ["a", "b"])
        with self.assertRaises(serializers.ValidationError):
            field.to_internal_value("not-a-list")

    def test_avatar_field_represents_external_and_local_urls(self):
        request = self.factory.get("/")
        class AvatarSerializer(serializers.Serializer):
            avatar = AvatarField()

        field_with_request = AvatarSerializer(context={"request": request}).fields["avatar"]
        field_without_request = AvatarSerializer().fields["avatar"]

        self.assertEqual(
            field_with_request.to_representation("https://example.com/avatar.jpg"),
            "https://example.com/avatar.jpg",
        )
        self.assertEqual(
            field_without_request.to_representation("characters/avatar.jpg"),
            "/media/characters/avatar.jpg",
        )
        self.assertTrue(
            field_with_request.to_representation("characters/avatar.jpg").endswith(
                "/media/characters/avatar.jpg"
            )
        )

    def test_avatar_field_accepts_url_relative_path_and_file_upload(self):
        field = AvatarField()

        self.assertEqual(
            field.to_internal_value("https://example.com/avatar.jpg"),
            "https://example.com/avatar.jpg",
        )
        self.assertEqual(field.to_internal_value("/media/characters/local.jpg"), "characters/local.jpg")

        uploaded = field.to_internal_value(uploaded_image("avatar.jpg"))
        self.assertTrue(uploaded.startswith("characters/"))
        self.assertTrue(uploaded.endswith(".jpg"))

        with self.assertRaises(serializers.ValidationError):
            field.to_internal_value(object())
