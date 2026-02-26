from django.contrib import admin

from .models import (
    CompatibilityRule,
    EquipmentCategory,
    EquipmentModule,
    EquipmentPhysicalType,
)


@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "parent",
        "equipment_type",
        "order",
        "is_active",
        "module_count",
    ]
    list_editable = ["order", "is_active"]
    list_filter = ["equipment_type", "is_active", "parent"]
    search_fields = ["name", "description"]
    fields = [
        "name",
        "parent",
        "equipment_type",
        "code",
        "description",
        "order",
        "is_active",
    ]
    readonly_fields = ["code"]

    def module_count(self, obj):
        return obj.modules_by_category.count()

    module_count.short_description = "Количество модулей"


@admin.register(EquipmentPhysicalType)
class EquipmentPhysicalTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "applicable_category", "order", "module_count"]
    list_editable = ["order"]
    list_filter = ["applicable_category"]
    search_fields = ["name"]

    def module_count(self, obj):
        return obj.modules_by_type.count()

    module_count.short_description = "Количество модулей"


@admin.register(EquipmentModule)
class EquipmentModuleAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "physical_type",
        "applicable_to",
        "price_type",
        "price",
        "is_active",
        "is_default",
    ]
    list_filter = [
        "category",
        "physical_type",
        "applicable_to",
        "price_type",
        "is_active",
    ]
    search_fields = ["name", "description"]
    list_editable = ["is_active", "is_default"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "name",
                    "category",
                    "physical_type",
                    "applicable_to",
                    "description",
                    "is_active",
                    "is_default",
                )
            },
        ),
        ("Цена", {"fields": ("price_type", "price")}),
        ("Изображения", {"fields": ("main_image",)}),
        (
            "Технические характеристики",
            {
                "fields": (
                    "power_consumption",
                    "dimensions",
                    "weight",
                    "specifications",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Системная информация",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(CompatibilityRule)
class CompatibilityRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "rule_type", "category", "is_active"]
    list_filter = ["rule_type", "is_active"]
    filter_horizontal = ["modules"]
    list_editable = ["is_active"]
