from rest_framework import serializers

from catalog.models import EquipmentCategory, EquipmentModule, EngineeringSystemOption
from .models import Configuration, ConfigurationModule, ConfigurationEngineeringSystem


class ConfigurationModuleWriteSerializer(serializers.Serializer):
    module_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class ConfigurationEngineeringWriteSerializer(serializers.Serializer):
    engineering_system_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    custom_parameters = serializers.JSONField(required=False, allow_null=True)
    price_at_selection = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )


class ConfigurationModuleReadSerializer(serializers.ModelSerializer):
    module = serializers.IntegerField(source="module_id", read_only=True)
    quantity = serializers.IntegerField()

    class Meta:
        model = ConfigurationModule
        fields = ("module", "quantity")


class ConfigurationEngineeringReadSerializer(serializers.ModelSerializer):
    engineering_system = serializers.IntegerField(source="engineering_system_id", read_only=True)
    quantity = serializers.IntegerField()
    custom_parameters = serializers.JSONField(required=False, allow_null=True)
    price_at_selection = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = ConfigurationEngineeringSystem
        fields = ("engineering_system", "quantity", "custom_parameters", "price_at_selection")


class ConfigurationSerializer(serializers.ModelSerializer):
    # ✅ FK -> отдаём как id (а не объект)
    main_category = serializers.IntegerField(source="main_category_id", read_only=True)

    # sub_category можно менять руками, валидируем существование
    sub_category = serializers.PrimaryKeyRelatedField(
        queryset=EquipmentCategory.objects.all(),
        required=False,
        allow_null=True,
    )

    # READ: отдаём выбранные позиции
    modules = ConfigurationModuleReadSerializer(source="module_items", many=True, read_only=True)
    engineering_systems = ConfigurationEngineeringReadSerializer(source="engineering_items", many=True, read_only=True)

    # WRITE: принимаем payload списков
    modules_payload = ConfigurationModuleWriteSerializer(many=True, write_only=True, required=False)
    engineering_systems_payload = ConfigurationEngineeringWriteSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Configuration
        fields = (
            "id",
            "user",
            "name",
            "description",
            "status",
            "order_number",
            "company_name",
            "phone",
            "email",
            "main_category",
            "sub_category",
            "container_config",
            "modules",
            "engineering_systems",
            "modules_payload",
            "engineering_systems_payload",
            "total_price",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "order_number",
            "total_price",
            "created_at",
            "updated_at",
            "main_category",
            "modules",
            "engineering_systems",
        )

    def create(self, validated_data):
        modules_payload = validated_data.pop("modules_payload", [])
        eng_payload = validated_data.pop("engineering_systems_payload", [])

        request = self.context.get("request")
        user = getattr(request, "user", None)

        cfg = Configuration.objects.create(user=user, **validated_data)

        self._apply_modules(cfg, modules_payload, replace=True)
        self._apply_engineering(cfg, eng_payload, replace=True)

        cfg.save()  # пересчитает total_price и main_category в модели
        return cfg

    def update(self, instance, validated_data):
        modules_payload = validated_data.pop("modules_payload", None)
        eng_payload = validated_data.pop("engineering_systems_payload", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if modules_payload is not None:
            self._apply_modules(instance, modules_payload, replace=True)

        if eng_payload is not None:
            self._apply_engineering(instance, eng_payload, replace=True)

        instance.save()
        return instance

    def _apply_modules(self, cfg: Configuration, items, replace: bool = True):
        if replace:
            cfg.module_items.all().delete()

        if not items:
            return

        ids = [it["module_id"] for it in items]
        existing = set(EquipmentModule.objects.filter(id__in=ids).values_list("id", flat=True))
        missing = [mid for mid in ids if mid not in existing]
        if missing:
            raise serializers.ValidationError({"modules_payload": [f"Unknown module_id: {missing}"]})

        for it in items:
            ConfigurationModule.objects.create(
                configuration=cfg,
                module_id=it["module_id"],
                quantity=it.get("quantity") or 1,
            )

    def _apply_engineering(self, cfg: Configuration, items, replace: bool = True):
        if replace:
            cfg.engineering_items.all().delete()

        if not items:
            return

        ids = [it["engineering_system_id"] for it in items]
        existing = set(EngineeringSystemOption.objects.filter(id__in=ids).values_list("id", flat=True))
        missing = [eid for eid in ids if eid not in existing]
        if missing:
            raise serializers.ValidationError({"engineering_systems_payload": [f"Unknown engineering_system_id: {missing}"]})

        for it in items:
            ConfigurationEngineeringSystem.objects.create(
                configuration=cfg,
                engineering_system_id=it["engineering_system_id"],
                quantity=it.get("quantity") or 1,
                custom_parameters=it.get("custom_parameters", None),
                price_at_selection=it.get("price_at_selection", None),
            )
