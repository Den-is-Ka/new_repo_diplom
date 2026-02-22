from rest_framework import serializers

from .models import Configuration, ConfigurationModule
from catalog.models import EquipmentCategory, EquipmentModule, EngineeringSystemOption
from users.serializers import UserSerializer


class ConfigurationSerializer(serializers.ModelSerializer):
    """Сериализатор для вывода конфигурации"""
    user = UserSerializer(read_only=True)
    main_category = serializers.StringRelatedField(read_only=True)
    sub_category = serializers.StringRelatedField(read_only=True)
    modules = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Configuration
        fields = [
            "id",
            "name",
            "description",
            "status",
            "user",
            "main_category",
            "sub_category",
            "modules",
            "total_price",
            "container_config",
            "company_name",
            "phone",
            "email",
            "order_number",
            "submitted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "total_price",
            "order_number",
            "submitted_at",
            "created_at",
            "updated_at",
        ]


class ConfigurationCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/обновления конфигурации"""
    main_category_id = serializers.PrimaryKeyRelatedField(
        queryset=EquipmentCategory.objects.filter(
            parent__isnull=False, parent__parent__isnull=True
        ),
        source="main_category",
        write_only=True,
        required=False,
        help_text="ID основной категории (1.1 или 1.2)",
    )

    sub_category_id = serializers.PrimaryKeyRelatedField(
        queryset=EquipmentCategory.objects.filter(
            parent__isnull=False, parent__parent__isnull=False
        ),
        source="sub_category",
        write_only=True,
        required=True,
        help_text="ID подкатегории (1.1.1, 1.2.2 и т.д.)",
    )

    module_ids = serializers.PrimaryKeyRelatedField(
        queryset=EquipmentModule.objects.filter(is_active=True),
        many=True,
        source="modules",
        write_only=True,
        required=False,
    )

    container_config = serializers.JSONField(
        required=False, help_text="Конфигурация контейнера в формате JSON"
    )

    class Meta:
        model = Configuration
        fields = [
            "id",
            "name",
            "description",
            "main_category_id",
            "sub_category_id",
            "module_ids",
            "container_config",
            "company_name",
            "phone",
            "email",
        ]

    def validate(self, data):
        """Валидация данных конфигурации"""
        sub_category = data.get("sub_category")
        main_category = data.get("main_category")

        # Автоопределение main_category по sub_category
        if sub_category and not main_category:
            current = sub_category
            while current.parent and current.parent.parent:
                current = current.parent
            data["main_category"] = current

        # Проверка принадлежности sub_category к main_category
        elif sub_category and main_category:
            current = sub_category
            while current.parent and current.parent != main_category and current.parent.parent:
                current = current.parent

            if current.parent != main_category:
                raise serializers.ValidationError(
                    {"sub_category_id": "Выбранная подкатегория не принадлежит указанной основной категории"}
                )

        # Проверяем совместимость модулей
        modules = data.get("modules", [])
        equipment_type = (
            data.get("main_category").equipment_type if data.get("main_category") else None
        )

        if equipment_type and modules:
            for module in modules:
                # В твоём проекте уже есть метод is_compatible_with
                if hasattr(module, "is_compatible_with") and not module.is_compatible_with(equipment_type):
                    raise serializers.ValidationError(
                        {"module_ids": f'Модуль "{module.name}" не совместим с выбранным типом оборудования'}
                    )

        return data

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        modules = validated_data.pop("modules", [])

        configuration = Configuration.objects.create(**validated_data)

        for module in modules:
            ConfigurationModule.objects.create(
                configuration=configuration, module=module, quantity=1
            )

        configuration.total_price = configuration.calculate_total_price()
        configuration.save()
        return configuration


class ConfigurationModuleSerializer(serializers.ModelSerializer):
    """Сериализатор для связи конфигурации и модулей"""
    module_name = serializers.CharField(source="module.name", read_only=True)
    module_price = serializers.DecimalField(
        source="module.price", max_digits=10, decimal_places=2, read_only=True
    )
    module_price_type = serializers.CharField(source="module.price_type", read_only=True)

    class Meta:
        model = ConfigurationModule
        fields = [
            "id",
            "configuration",
            "module",
            "module_name",
            "module_price",
            "module_price_type",
            "quantity",
        ]


class ConfigurationValidateSerializer(serializers.Serializer):
    """Сериализатор для валидации конфигурации"""
    is_valid = serializers.BooleanField(read_only=True)
    errors = serializers.ListField(child=serializers.CharField(), read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


class ConfigurationSetEngineeringSerializer(serializers.Serializer):
    """
    Для action set_engineering:
    присылаем список id опций инженерных систем.
    """
    engineering_option_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
        required=True,
    )

    def validate_engineering_option_ids(self, value):
        # проверим что все id существуют и активны
        qs = EngineeringSystemOption.objects.filter(id__in=value, is_active=True)
        found = set(qs.values_list("id", flat=True))
        missing = [x for x in value if x not in found]
        if missing:
            raise serializers.ValidationError(f"Engineering options not found or inactive: {missing}")
        return value
