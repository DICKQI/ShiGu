from rest_framework import generics

from .models import StorageNode
from .serializers import StorageNodeSerializer, StorageNodeTreeSerializer


class StorageNodeListCreateView(generics.ListCreateAPIView):
    """
    基础的收纳节点列表 / 创建接口。
    一般后台维护使用，非高频调用。
    """

    queryset = StorageNode.objects.all().order_by("order", "id")
    serializer_class = StorageNodeSerializer


class StorageNodeTreeView(generics.ListAPIView):
    """
    位置树一次性下发接口：
    - 返回所有节点的扁平列表（带 parent），前端在 Pinia 中组装为树。
    - 更新频率极低，后续可在此视图外层加缓存（例如 Redis）。
    """

    queryset = StorageNode.objects.all().order_by("path_name", "order")
    serializer_class = StorageNodeTreeSerializer

