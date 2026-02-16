from django.contrib import admin
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .models import Configuration, ConfigurationModule, ConfigurationEngineeringSystem


class ConfigurationModuleInline(admin.TabularInline):
    model = ConfigurationModule
    extra = 0
    autocomplete_fields = ("module",)
    fields = ("module", "quantity")
    show_change_link = True


class ConfigurationEngineeringInline(admin.TabularInline):
    model = ConfigurationEngineeringSystem
    extra = 0
    autocomplete_fields = ("engineering_system",)
    fields = ("engineering_system", "quantity", "price_at_selection", "custom_parameters")
    show_change_link = True


@admin.action(description=_("Пересчитать total_price"))
def recalc_total_price(modeladmin, request, queryset):
    # пересчитываем аккуратно и атомарно
    with transaction.atomic():
        for cfg in queryset.select_for_update():
            new_total = cfg.calculate_total_price()
            if cfg.total_price != new_total:
                cfg.total_price = new_total
                cfg.save(update_fields=["total_price", "updated_at"])


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "user",
        "status",
        "main_category",
        "sub_category",
        "total_price",
        "order_number",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "main_category", "created_at")
    search_fields = ("id", "name", "user__email", "user__username", "order_number")
    readonly_fields = ("created_at", "updated_at", "total_price")
    inlines = (ConfigurationModuleInline, ConfigurationEngineeringInline)
    actions = [recalc_total_price]

    # чтобы не загружать огромные списки FK в форме
    autocomplete_fields = ("user", "main_category", "sub_category")

    fieldsets = (
        (_("Основное"), {
            "fields": ("user", "name", "description", "status")
        }),
        (_("Категории (Раздел 1 ТЗ)"), {
            "fields": ("main_category", "sub_category")
        }),
        (_("Контейнер (пока JSON)"), {
            "fields": ("container_config",)
        }),
        (_("Контакты/заказ"), {
            "fields": ("company_name", "phone", "email", "order_number")
        }),
        (_("Итоги"), {
            "fields": ("total_price", "created_at", "updated_at")
        }),
    )


@admin.register(ConfigurationModule)
class ConfigurationModuleAdmin(admin.ModelAdmin):
    list_display = ("id", "configuration", "module", "quantity")
    search_fields = ("configuration__id", "module__name")
    autocomplete_fields = ("configuration", "module")


@admin.register(ConfigurationEngineeringSystem)
class ConfigurationEngineeringSystemAdmin(admin.ModelAdmin):
    list_display = ("id", "configuration", "engineering_system", "quantity", "price_at_selection")
    search_fields = ("configuration__id", "engineering_system__title", "engineering_system__code")
    autocomplete_fields = ("configuration", "engineering_system")
