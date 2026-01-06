from rest_framework import serializers

from .models import Category, Character, Goods, GuziImage, IP, IPKeyword
from .utils import compress_image


class IPKeywordSerializer(serializers.ModelSerializer):
    """IP关键词序列化器"""

    class Meta:
        model = IPKeyword
        fields = ("id", "value")


class KeywordsField(serializers.Field):
    """自定义关键词字段：读取时返回对象数组，写入时接收字符串数组"""

    def to_representation(self, value):
        """读取时：返回关键词对象数组"""
        if value is None:
            return []
        # value是RelatedManager，需要调用all()获取查询集
        return [{"id": kw.id, "value": kw.value} for kw in value.all()]

    def to_internal_value(self, data):
        """写入时：接收字符串数组"""
        if data is None:
            return []
        if not isinstance(data, list):
            raise serializers.ValidationError("关键词必须是数组格式")
        # 去重、去空、去除前后空格
        keywords = [str(item).strip() for item in data if item and str(item).strip()]
        # 去重（保持顺序）
        seen = set()
        result = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)
        return result


class IPSimpleSerializer(serializers.ModelSerializer):
    """IP简单序列化器（用于列表和嵌套显示）"""

    keywords = IPKeywordSerializer(many=True, read_only=True, help_text="IP关键词列表")

    class Meta:
        model = IP
        fields = ("id", "name", "keywords")


class IPDetailSerializer(serializers.ModelSerializer):
    """IP详情序列化器（用于创建和更新，支持关键词操作）"""

    keywords = KeywordsField(required=False, allow_null=True, help_text="关键词列表，例如：['星铁', '崩铁', 'HSR']")

    class Meta:
        model = IP
        fields = ("id", "name", "keywords")

    def create(self, validated_data):
        """创建IP时同时创建关键词"""
        keywords_data = validated_data.pop("keywords", [])
        ip = IP.objects.create(**validated_data)

        # 创建关键词
        if keywords_data:
            for keyword_value in keywords_data:
                if keyword_value and keyword_value.strip():  # 忽略空字符串
                    IPKeyword.objects.get_or_create(ip=ip, value=keyword_value.strip())

        return ip

    def update(self, instance, validated_data):
        """更新IP时同步更新关键词"""
        keywords_data = validated_data.pop("keywords", None)

        # 更新IP基本信息
        instance.name = validated_data.get("name", instance.name)
        instance.save()

        # 如果提供了keywords字段，则更新关键词
        if keywords_data is not None:
            # 获取当前关键词值集合
            existing_keywords = set(instance.keywords.values_list("value", flat=True))
            new_keywords = {kw.strip() for kw in keywords_data if kw and kw.strip()}

            # 删除不再存在的关键词
            to_delete = existing_keywords - new_keywords
            if to_delete:
                instance.keywords.filter(value__in=to_delete).delete()

            # 添加新关键词
            to_add = new_keywords - existing_keywords
            for keyword_value in to_add:
                IPKeyword.objects.get_or_create(ip=instance, value=keyword_value)

        return instance


class CharacterSimpleSerializer(serializers.ModelSerializer):
    ip = IPSimpleSerializer(read_only=True)
    ip_id = serializers.PrimaryKeyRelatedField(
        queryset=IP.objects.all(),
        source="ip",
        write_only=True,
        required=True,
        help_text="所属IP作品ID",
    )

    class Meta:
        model = Character
        fields = ("id", "name", "ip", "ip_id", "avatar")

    def create(self, validated_data):
        """创建角色时自动压缩头像"""
        avatar = validated_data.get('avatar')
        if avatar:
            compressed_image = compress_image(avatar, max_size_kb=300)
            if compressed_image:
                validated_data['avatar'] = compressed_image
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新角色时自动压缩头像"""
        avatar = validated_data.get('avatar')
        if avatar:
            compressed_image = compress_image(avatar, max_size_kb=300)
            if compressed_image:
                validated_data['avatar'] = compressed_image
        return super().update(instance, validated_data)


class CategorySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")


class GuziImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuziImage
        fields = ("id", "image", "label")

    def create(self, validated_data):
        """创建补充图片时自动压缩"""
        image = validated_data.get('image')
        if image:
            compressed_image = compress_image(image, max_size_kb=300)
            if compressed_image:
                validated_data['image'] = compressed_image
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新补充图片时自动压缩"""
        image = validated_data.get('image')
        if image:
            compressed_image = compress_image(image, max_size_kb=300)
            if compressed_image:
                validated_data['image'] = compressed_image
        return super().update(instance, validated_data)


class GoodsListSerializer(serializers.ModelSerializer):
    """
    列表用“瘦身”序列化器，仅返回检索页所需字段。
    """

    ip = IPSimpleSerializer(read_only=True)
    character = CharacterSimpleSerializer(read_only=True)
    category = CategorySimpleSerializer(read_only=True)
    location_path = serializers.SerializerMethodField()

    class Meta:
        model = Goods
        fields = (
            "id",
            "name",
            "ip",
            "character",
            "category",
            "location_path",
            "main_photo",
            "status",
            "quantity",
        )

    def get_location_path(self, obj):
        if obj.location:
            return obj.location.path_name or obj.location.name
        return None


class GoodsDetailSerializer(serializers.ModelSerializer):
    """
    详情页序列化器，返回完整信息及补充图片。
    """

    ip = IPSimpleSerializer(read_only=True)
    ip_id = serializers.PrimaryKeyRelatedField(
        queryset=IP.objects.all(),
        source="ip",
        write_only=True,
        required=False,
        help_text="所属IP作品ID",
    )
    character = CharacterSimpleSerializer(read_only=True)
    character_id = serializers.PrimaryKeyRelatedField(
        queryset=Character.objects.all(),
        source="character",
        write_only=True,
        required=False,
        help_text="所属角色ID",
    )
    category = CategorySimpleSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        help_text="品类ID",
    )
    location_path = serializers.SerializerMethodField()
    additional_photos = GuziImageSerializer(many=True, read_only=True)

    class Meta:
        model = Goods
        fields = (
            "id",
            "name",
            "ip_id",
            "ip",
            "character_id",
            "character",
            "category_id",
            "category",
            "location_path",
            "location",
            "main_photo",
            "quantity",
            "price",
            "purchase_date",
            "is_official",
            "status",
            "notes",
            "created_at",
            "updated_at",
            "additional_photos",
        )

    def get_location_path(self, obj):
        if obj.location:
            return obj.location.path_name or obj.location.name
        return None

    def validate(self, attrs):
        """
        保证创建时必填外键，更新时允许部分字段缺省。
        """
        if self.instance is None:
            required_fields = {
                "ip": "ip_id",
                "character": "character_id",
                "category": "category_id",
            }
            missing = [
                alias for key, alias in required_fields.items() if key not in attrs
            ]
            if missing:
                raise serializers.ValidationError(
                    {field: "创建时必填" for field in missing}
                )
        return attrs

    def create(self, validated_data):
        """创建谷子时自动压缩主图"""
        main_photo = validated_data.get('main_photo')
        if main_photo:
            compressed_image = compress_image(main_photo, max_size_kb=300)
            if compressed_image:
                validated_data['main_photo'] = compressed_image
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新谷子时自动压缩主图"""
        main_photo = validated_data.get('main_photo')
        if main_photo:
            compressed_image = compress_image(main_photo, max_size_kb=300)
            if compressed_image:
                validated_data['main_photo'] = compressed_image
        return super().update(instance, validated_data)


