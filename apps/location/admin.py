from django.contrib import admin

from .models import StorageNode


@admin.register(StorageNode)
class StorageNodeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "parent", "path_name", "order")
    list_filter = ("parent",)
    search_fields = ("name", "path_name")
    ordering = ("path_name", "order")
    list_per_page = 100

