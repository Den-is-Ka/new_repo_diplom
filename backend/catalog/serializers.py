from rest_framework import serializers
from .models import EquipmentType, EquipmentModule, CompatibilityRule

class EquipmentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentType
        fields = '__all__'

class EquipmentModuleSerializer(serializers.ModelSerializer):
    equipment_type = EquipmentTypeSerializer(read_only=True)
    equipment_type_id = serializers.PrimaryKeyRelatedField(
        queryset=EquipmentType.objects.all(),
        source='equipment_type',
        write_only=True
    )
    
    class Meta:
        model = EquipmentModule
        fields = '__all__'

class CompatibilityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompatibilityRule
        fields = '__all__'
