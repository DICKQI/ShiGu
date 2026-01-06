from rest_framework import serializers

from .models import StorageNode


class StorageNodeSerializer(serializers.ModelSerializer):
    path_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="完整路径，如果不提供则根据父节点自动生成，例如：书房/书架A/第3层",
    )

    class Meta:
        model = StorageNode
        fields = ("id", "name", "parent", "path_name", "order", "image", "description")

    def create(self, validated_data):
        """创建节点时，如果未提供 path_name，则根据父节点自动生成"""
        path_name = validated_data.get("path_name")
        parent = validated_data.get("parent")
        name = validated_data.get("name")

        # 如果 path_name 为空或未提供，则根据父节点自动生成
        if not path_name:
            if parent:
                # 有父节点：父节点路径 + "/" + 当前节点名称
                parent_path = parent.path_name or parent.name
                path_name = f"{parent_path}/{name}"
            else:
                # 无父节点（根节点）：直接使用节点名称
                path_name = name

        validated_data["path_name"] = path_name
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新节点时，如果父节点或名称改变，自动更新 path_name"""
        parent = validated_data.get("parent", instance.parent)
        name = validated_data.get("name", instance.name)
        path_name = validated_data.get("path_name")

        # 如果用户明确提供了 path_name，使用用户提供的值
        # 如果未提供 path_name，但父节点或名称改变了，需要重新生成
        if path_name is None:
            # 检查是否需要重新生成 path_name
            parent_changed = parent != instance.parent
            name_changed = name != instance.name

            if parent_changed or name_changed:
                # 重新生成 path_name
                if parent:
                    parent_path = parent.path_name or parent.name
                    path_name = f"{parent_path}/{name}"
                else:
                    path_name = name
                validated_data["path_name"] = path_name

        return super().update(instance, validated_data)


class StorageNodeTreeSerializer(serializers.ModelSerializer):
    """
    位置树一次性下发用序列化器。
    前端可根据 parent/id 在内存中自行组装为树结构。
    """

    class Meta:
        model = StorageNode
        fields = ("id", "name", "parent", "path_name", "order")


