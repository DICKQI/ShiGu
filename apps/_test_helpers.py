from __future__ import annotations

import shutil
import tempfile
from datetime import date
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.goods.models import (
    Category,
    Character,
    Goods,
    IP,
    IPKeyword,
    Showcase,
    ShowcaseGoods,
    Theme,
)
from apps.location.models import StorageNode
from apps.users.models import Role, User


def unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def create_role(name: str = "User") -> Role:
    role, _ = Role.objects.get_or_create(name=name)
    return role


def create_user(
    username: str | None = None,
    password: str = "testpass123",
    role_name: str = "User",
    is_active: bool = True,
) -> User:
    user = User(username=username or unique_name("user"), role=create_role(role_name), is_active=is_active)
    user.set_password(password)
    user.save()
    return user


def create_admin_user(username: str | None = None, password: str = "testpass123") -> User:
    return create_user(username=username or unique_name("admin"), password=password, role_name="admin")


def auth_client(user: User | None = None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def create_ip(
    name: str | None = None,
    subject_type: int | None = 4,
    order: int = 0,
    keywords: tuple[str, ...] | list[str] = (),
) -> IP:
    ip = IP.objects.create(name=name or unique_name("ip"), subject_type=subject_type, order=order)
    for value in keywords:
        IPKeyword.objects.create(ip=ip, value=value)
    return ip


def create_character(
    ip: IP | None = None,
    name: str | None = None,
    gender: str = "other",
    avatar: str | None = None,
) -> Character:
    return Character.objects.create(
        ip=ip or create_ip(),
        name=name or unique_name("character"),
        gender=gender,
        avatar=avatar,
    )


def create_category(
    name: str | None = None,
    parent: Category | None = None,
    order: int = 0,
    color_tag: str | None = None,
    path_name: str | None = None,
) -> Category:
    category_name = name or unique_name("category")
    if path_name is None:
        parent_path = parent.path_name or parent.name if parent else None
        path_name = f"{parent_path}/{category_name}" if parent_path else category_name
    return Category.objects.create(
        name=category_name,
        parent=parent,
        path_name=path_name,
        order=order,
        color_tag=color_tag,
    )


def create_storage_node(
    user: User,
    name: str | None = None,
    parent: StorageNode | None = None,
    order: int = 0,
    path_name: str | None = None,
) -> StorageNode:
    node_name = name or unique_name("node")
    if path_name is None:
        parent_path = parent.path_name or parent.name if parent else None
        path_name = f"{parent_path}/{node_name}" if parent_path else node_name
    return StorageNode.objects.create(
        user=user,
        name=node_name,
        parent=parent,
        path_name=path_name,
        order=order,
    )


def create_theme(user: User, name: str | None = None, description: str = "theme") -> Theme:
    return Theme.objects.create(user=user, name=name or unique_name("theme"), description=description)


def create_goods(
    user: User,
    name: str | None = None,
    ip: IP | None = None,
    category: Category | None = None,
    characters: list[Character] | tuple[Character, ...] | None = None,
    location: StorageNode | None = None,
    theme: Theme | None = None,
    quantity: int = 1,
    price: Decimal | str | None = Decimal("10.00"),
    purchase_date: date | None = date(2025, 1, 1),
    is_official: bool = True,
    status: str = "in_cabinet",
    order: int = 0,
) -> Goods:
    ip_obj = ip or create_ip()
    category_obj = category or create_category()
    goods = Goods.objects.create(
        user=user,
        name=name or unique_name("goods"),
        ip=ip_obj,
        category=category_obj,
        location=location,
        theme=theme,
        quantity=quantity,
        price=Decimal(price) if price is not None else None,
        purchase_date=purchase_date,
        is_official=is_official,
        status=status,
        order=order,
    )
    if characters is None:
        characters = [create_character(ip=ip_obj)]
    if characters:
        goods.characters.set(characters)
    return goods


def create_showcase(
    user: User,
    name: str | None = None,
    is_public: bool = True,
    order: int = 0,
) -> Showcase:
    return Showcase.objects.create(
        user=user,
        name=name or unique_name("showcase"),
        is_public=is_public,
        order=order,
    )


def add_showcase_goods(
    showcase: Showcase,
    goods: Goods,
    order: int = 0,
    notes: str = "",
) -> ShowcaseGoods:
    return ShowcaseGoods.objects.create(showcase=showcase, goods=goods, order=order, notes=notes)


def uploaded_image(
    name: str = "test.jpg",
    size: tuple[int, int] = (64, 64),
    color: tuple[int, int, int] = (255, 0, 0),
    image_format: str = "JPEG",
) -> SimpleUploadedFile:
    image_io = BytesIO()
    Image.new("RGB", size, color).save(image_io, format=image_format)
    content_type = "image/png" if image_format.upper() == "PNG" else "image/jpeg"
    return SimpleUploadedFile(name, image_io.getvalue(), content_type=content_type)


class TempMediaRootMixin:
    def setUp(self):
        super().setUp()
        self._media_root = tempfile.mkdtemp()
        self._media_override = override_settings(MEDIA_ROOT=self._media_root)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        self.addCleanup(shutil.rmtree, self._media_root, True)
