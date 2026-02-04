from __future__ import annotations

from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="角色名")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "角色"
        verbose_name_plural = "角色"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name


class User(models.Model):
    username = models.CharField(max_length=150, unique=True, db_index=True, verbose_name="用户名")
    password = models.CharField(max_length=255, verbose_name="密码哈希")
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
        verbose_name="角色",
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.username

    @property
    def is_authenticated(self) -> bool:
        # DRF's IsAuthenticated relies on this.
        return True

    def set_password(self, raw_password: str) -> None:
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password)


class Permission(models.Model):
    """
    预留：细粒度权限表。当前版本主要按 Role + policy 控制。
    """

    code = models.CharField(max_length=100, unique=True, db_index=True, verbose_name="权限编码")
    name = models.CharField(max_length=100, verbose_name="权限名称")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "权限"
        verbose_name_plural = "权限"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.code

