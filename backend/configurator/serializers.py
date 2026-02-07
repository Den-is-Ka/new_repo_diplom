from rest_framework import serializers
from .models import Configuration
from catalog.models import EquipmentType, EquipmentModule
from users.serializers import UserSerializer


class ConfigurationSerializer(serializers.ModelSerializer):
    """Сериализатор для вывода конфигурации"""
    user = UserSerializer(read_only=True)
    equipment_type = serializers.StringRelatedField(read_only=True)
    modules = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Configuration
        fields = [
            'id', 'name', 'description', 'status',
            'user', 'equipment_type', 'modules',
            'total_price', 'compatibility_errors',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'total_price',
            'compatibility_errors', 'created_at', 'updated_at'
        ]


class ConfigurationCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/обновления конфигурации"""
    equipment_type_id = serializers.PrimaryKeyRelatedField(
        queryset=EquipmentType.objects.all(),
        source='equipment_type',
        write_only=True
    )
    module_ids = serializers.PrimaryKeyRelatedField(
        queryset=EquipmentModule.objects.all(),
        many=True,
        source='modules',
        write_only=True,
        required=False
    )

    class Meta:
        model = Configuration
        fields = [
            'id', 'name', 'description',
            'equipment_type_id', 'module_ids'
        ]

    def create(self, validated_data):
        # Добавляем текущего пользователя
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Сохраняем и автоматически проверяем совместимость
        instance = super().update(instance, validated_data)
        instance.save()  # Вызовет проверку совместимости и расчет цены
        return instance


class ConfigurationValidateSerializer(serializers.Serializer):
    """Сериализатор для валидации конфигурации"""
    is_valid = serializers.BooleanField(read_only=True)
    errors = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    total_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )