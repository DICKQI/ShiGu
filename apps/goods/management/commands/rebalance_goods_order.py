from django.core.management.base import BaseCommand
from django.db import transaction

from apps.goods.models import Goods


class Command(BaseCommand):
    """
    重排 Goods.order 为稀疏序列，消除历史上相同 order 的堆积。

    排序规则遵循模型默认：order, -created_at, id
    重新赋值为等差序列：step, 2*step, 3*step, ...
    """

    help = "Rebalance goods ordering to sparse increasing sequence."

    def add_arguments(self, parser):
        parser.add_argument(
            "--step",
            type=int,
            default=1000,
            help="稀疏步长，默认 1000",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="批量写入大小，默认 500",
        )

    def handle(self, *args, **options):
        step: int = options["step"]
        batch_size: int = options["batch_size"]

        if step <= 0:
            self.stderr.write(self.style.ERROR("step 必须为正整数"))
            return

        qs = Goods.objects.order_by("order", "-created_at", "id")
        total = qs.count()
        self.stdout.write(f"准备重排 {total} 条 Goods 记录，step={step} ...")

        updated = 0
        batch = []

        with transaction.atomic():
            for idx, obj in enumerate(qs.iterator()):
                new_order = (idx + 1) * step
                if obj.order != new_order:
                    obj.order = new_order
                    batch.append(obj)

                if len(batch) >= batch_size:
                    Goods.objects.bulk_update(batch, ["order"])
                    updated += len(batch)
                    batch.clear()

            if batch:
                Goods.objects.bulk_update(batch, ["order"])
                updated += len(batch)

        self.stdout.write(self.style.SUCCESS(f"重排完成，共更新 {updated}/{total} 条记录"))
