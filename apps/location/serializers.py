from rest_framework import serializers

from .models import StorageNode


class StorageNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageNode
        fields = ("id", "name", "parent", "path_name", "order", "image", "description")


class StorageNodeTreeSerializer(serializers.ModelSerializer):
    """
    位置树一次性下发用序列化器。
    前端可根据 parent/id 在内存中自行组装为树结构。
    """

    class Meta:
        model = StorageNode
        fields = ("id", "name", "parent", "path_name", "order")


