from django.contrib import admin
from .models import EquipmentType, EquipmentModule, CompatibilityRule


@admin.register(EquipmentType)
class EquipmentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'module_count']
    list_editable = ['order']
    search_fields = ['name']

    def module_count(self, obj):
        return obj.modules.count()

    module_count.short_description = 'Кол-во модулей'


@admin.register(EquipmentModule)
class EquipmentModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'equipment_type', 'price_type', 'price', 'is_active', 'is_default']
    list_filter = ['equipment_type', 'price_type', 'is_active']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'is_default']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'equipment_type', 'description', 'is_active', 'is_default')
        }),
        ('Цена', {
            'fields': ('price_type', 'price')
        }),
        ('Изображения', {
            'fields': ('main_image',)
        }),
        ('Технические характеристики', {
            'fields': ('power_consumption', 'dimensions', 'weight'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CompatibilityRule)
class CompatibilityRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'is_active']
    list_filter = ['rule_type', 'is_active']
    filter_horizontal = ['modules']
    list_editable = ['is_active']
