from django.apps import AppConfig


class GoodsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.goods'

    def ready(self):
        # 导入信号，确保模型文件清理逻辑生效
        import apps.goods.signals  # noqa: F401
