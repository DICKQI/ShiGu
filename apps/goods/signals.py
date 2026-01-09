from django.core.files.storage import default_storage
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Character, Goods


@receiver(post_delete, sender=Character)
def delete_avatar_on_character_delete(sender, instance, **kwargs):
    """
    删除角色时同步删除存储中的头像文件，避免残留。
    只删除本地文件，不删除外部URL。
    """
    avatar = getattr(instance, "avatar", None)
    if avatar and isinstance(avatar, str):
        # 判断是否为本地路径（不是http://或https://开头的URL）
        if not avatar.startswith('http://') and not avatar.startswith('https://'):
            # 是本地路径，删除文件
            if default_storage.exists(avatar):
                default_storage.delete(avatar)


@receiver(pre_save, sender=Character)
def delete_old_avatar_on_update(sender, instance, **kwargs):
    """
    更新角色头像时删除旧文件，避免废弃文件占用存储。
    只删除本地文件，不删除外部URL。
    """
    if not instance.pk:
        return

    try:
        old = Character.objects.get(pk=instance.pk)
    except Character.DoesNotExist:
        return

    old_avatar = getattr(old, "avatar", None)
    new_avatar = getattr(instance, "avatar", None)

    # 只有当旧头像和新头像不同，且旧头像是本地路径时，才删除
    if old_avatar and isinstance(old_avatar, str) and old_avatar != new_avatar:
        # 判断是否为本地路径（不是http://或https://开头的URL）
        if not old_avatar.startswith('http://') and not old_avatar.startswith('https://'):
            # 是本地路径，删除文件
            if default_storage.exists(old_avatar):
                default_storage.delete(old_avatar)


@receiver(post_delete, sender=Goods)
def delete_main_photo_on_goods_delete(sender, instance, **kwargs):
    """
    删除谷子时同步删除主图文件。
    """
    main_photo = getattr(instance, "main_photo", None)
    if main_photo and main_photo.name:
        storage = main_photo.storage
        name = main_photo.name
        if storage.exists(name):
            storage.delete(name)


@receiver(pre_save, sender=Goods)
def delete_old_main_photo_on_update(sender, instance, **kwargs):
    """
    更新谷子主图时删除旧文件。
    """
    if not instance.pk:
        return

    try:
        old = Goods.objects.get(pk=instance.pk)
    except Goods.DoesNotExist:
        return

    old_photo = getattr(old, "main_photo", None)
    new_photo = getattr(instance, "main_photo", None)

    if old_photo and old_photo.name and old_photo != new_photo:
        storage = old_photo.storage
        name = old_photo.name
        if storage.exists(name):
            storage.delete(name)

