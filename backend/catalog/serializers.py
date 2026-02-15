from rest_framework import serializers

from .models import (
    EquipmentCategory,
    EquipmentPhysicalType,
    EquipmentModule,
    CompatibilityRule,
    EngineeringSystemGroup,
    EngineeringSystemOption,
)


class EquipmentCategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категорий оборудования"""
    parent = serializers.PrimaryKeyRelatedField(
        queryset=EquipmentCategory.objects.all(),
        required=False,
        allow_null=True
    )
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    children_count = serializers.IntegerField(source='children.count', read_only=True)
    modules_count = serializers.IntegerField(source='modules_by_category.count', read_only=True)

    class Meta:
        model = EquipmentCategory
        fields = [
            'id',
            'name',
            'parent',
            'parent_name',
            'equipment_type',
            'description',
            'order',
            'code',
            'is_active',
            'children_count',
            'modules_count',
        ]
        read_only_fields = ['code']


class EquipmentPhysicalTypeSerializer(serializers.ModelSerializer):
    """Сериализатор для физических типов оборудования"""
    modules_count = serializers.IntegerField(source='modules_by_type.count', read_only=True)

    class Meta:
        model = EquipmentPhysicalType
        fields = [
            'id',
            'name',
            'description',
            'image',
            'order',
            'applicable_category',
            'modules_count'
        ]


class EquipmentModuleSerializer(serializers.ModelSerializer):
    """Сериализатор для модулей оборудования"""
    category = EquipmentCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=EquipmentCategory.objects.all(),
        source='category',
        write_only=True
    )

    physical_type = EquipmentPhysicalTypeSerializer(read_only=True)
    physical_type_id = serializers.PrimaryKeyRelatedField(
        queryset=EquipmentPhysicalType.objects.all(),
        source='physical_type',
        write_only=True,
        required=False,
        allow_null=True,
    )

    display_price = serializers.CharField(read_only=True)

    class Meta:
        model = EquipmentModule
        fields = [
            'id',
            'name',
            'category',
            'category_id',
            'physical_type',
            'physical_type_id',
            'applicable_to',
            'description',
            'price_type',
            'price',
            'display_price',
            'main_image',
            'power_consumption',
            'dimensions',
            'weight',
            'specifications',
            'is_active',
            'is_default',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class CompatibilityRuleSerializer(serializers.ModelSerializer):
    """Сериализатор для правил совместимости"""
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = CompatibilityRule
        fields = [
            'id',
            'name',
            'rule_type',
            'description',
            'category',
            'category_name',
            'excluded_categories',
            'modules',
            'max_quantity',
            'required_module',
            'is_active'
        ]


# =========================
# Раздел 2 ТЗ: Инженерные системы
# =========================

class EngineeringSystemGroupSerializer(serializers.ModelSerializer):
    """Группы инженерных систем (2.1–2.9)"""

    class Meta:
        model = EngineeringSystemGroup
        fields = (
            "id",
            "key",
            "code",
            "title",
            "selection_mode",
            "order",
            "is_active",
        )
        read_only_fields = fields


class EngineeringSystemOptionSerializer(serializers.ModelSerializer):
    """Опции инженерных систем (2.1.1, 2.1.2, …)"""
    group_code = serializers.CharField(source="group.code", read_only=True)
    group_title = serializers.CharField(source="group.title", read_only=True)

    class Meta:
        model = EngineeringSystemOption
        fields = (
            "id",
            "group",
            "group_code",
            "group_title",
            "code",
            "title",
            "applicability",
            "price_type",
            "price",
            "order",
            "is_active",
        )
        read_only_fields = fields
