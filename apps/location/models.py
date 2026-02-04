from django.db import models


class StorageNode(models.Model):
    """
    物理收纳空间的树状结构节点：房间 -> 柜子 -> 层 -> 抽屉/格子 ...
    采用自关联设计，支持无限级层级。
    """

    name = models.CharField(max_length=50, verbose_name="节点名称")
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="storage_nodes",
        db_index=True,
        verbose_name="所属用户",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="父级节点",
    )
    path_name = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name="完整路径",
        help_text="冗余字段，例如：书房/书架A/第3层",
    )
    image = models.ImageField(
        upload_to="location/",
        null=True,
        blank=True,
        verbose_name="位置照片",
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="备注",
    )
    order = models.IntegerField(
        default=0,
        verbose_name="排序值",
        help_text="控制同级节点的展示顺序，值越小越靠前",
    )

    class Meta:
        verbose_name = "收纳节点"
        verbose_name_plural = "收纳节点"
        ordering = ["order", "id"]

    def __str__(self):
        return self.path_name or self.name
