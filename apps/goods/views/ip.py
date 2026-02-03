"""
IP作品相关的视图
"""
from django.db import transaction
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import IP
from ..serializers import (
    IPBatchUpdateOrderSerializer,
    IPDetailSerializer,
    IPSimpleSerializer,
    CharacterSimpleSerializer,
)


class IPViewSet(viewsets.ModelViewSet):
    """
    IP作品CRUD接口。

    - list: 获取所有IP作品列表（包含关键词）
    - retrieve: 获取单个IP作品详情（包含关键词）
    - create: 创建新IP作品（支持同时创建关键词）
    - update: 更新IP作品（支持同时更新关键词）
    - partial_update: 部分更新IP作品（支持同时更新关键词）
    - destroy: 删除IP作品
    - characters: 获取指定IP下的所有角色列表（/api/ips/{id}/characters/）
    - batch_update_order: 批量更新IP作品排序（用于拖拽排序等功能）
    """

    filter_backends = (DjangoFilterBackend, drf_filters.SearchFilter)
    search_fields = ("name", "keywords__value")
    filterset_fields = {
        "name": ["exact", "icontains"],
        "subject_type": ["exact", "in"],  # exact: 精确匹配，in: 多值筛选（逗号分隔）
    }

    def get_queryset(self):
        """优化查询，预加载关键词并统计角色数量"""
        return (
            IP.objects.all()
            .prefetch_related("keywords")
            .annotate(character_count=Count("characters"))
            .order_by("order", "id")
        )

    def get_serializer_class(self):
        """根据操作类型选择序列化器"""
        if self.action in ("create", "update", "partial_update"):
            return IPDetailSerializer
        return IPSimpleSerializer

    @action(detail=True, methods=["get"], url_path="characters")
    def characters(self, request, pk=None):
        """
        获取指定IP下的所有角色列表
        URL: /api/ips/{id}/characters/
        """
        ip = self.get_object()
        characters = ip.characters.all().select_related("ip").order_by("created_at")
        serializer = CharacterSimpleSerializer(
            characters, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="batch-update-order")
    def batch_update_order(self, request):
        """
        批量更新IP作品排序接口
        URL: /api/ips/batch-update-order/

        用于前端通过拖拽等方式调整IP作品顺序后，批量更新排序值。
        支持同时更新多个IP作品的order字段。
        """
        serializer = IPBatchUpdateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data["items"]

        ip_ids = [item["id"] for item in items]
        existing_ips = IP.objects.filter(id__in=ip_ids)
        existing_ids = set(existing_ips.values_list("id", flat=True))

        missing_ids = set(ip_ids) - existing_ids
        if missing_ids:
            return Response(
                {"detail": f"以下IP作品ID不存在: {sorted(missing_ids)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                ip_dict = {obj.id: obj for obj in existing_ips}

                updated_ips = []
                for item in items:
                    ip_obj = ip_dict[item["id"]]
                    ip_obj.order = item["order"]
                    ip_obj.save(update_fields=["order"])
                    updated_ips.append(ip_obj)

                updated_ids = [obj.id for obj in updated_ips]
                result_ips = IP.objects.filter(id__in=updated_ids).order_by("order", "id")
                result_serializer = IPSimpleSerializer(
                    result_ips, many=True, context={"request": request}
                )

                return Response(
                    {
                        "detail": f"成功更新 {len(updated_ips)} 个IP作品的排序",
                        "updated_count": len(updated_ips),
                        "ips": result_serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            return Response(
                {"detail": f"更新排序失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
