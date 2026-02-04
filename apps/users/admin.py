from django.contrib import admin

from .models import Permission, Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)
    ordering = ("id",)
    readonly_fields = ("created_at",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "role", "is_active", "created_at", "updated_at")
    list_filter = ("role", "is_active", "created_at")
    search_fields = ("username",)
    autocomplete_fields = ("role",)
    ordering = ("id",)
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 50


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "created_at")
    search_fields = ("code", "name")
    ordering = ("id",)
    readonly_fields = ("created_at",)

