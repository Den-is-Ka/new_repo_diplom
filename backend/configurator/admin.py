from django.contrib import admin

from .models import Configuration, ConfigurationModule, ConfigurationEngineeringSystem


class ConfigurationModuleInline(admin.TabularInline):
    model = ConfigurationModule
    extra = 0


class ConfigurationEngineeringInline(admin.TabularInline):
    model = ConfigurationEngineeringSystem
    extra = 0


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "updated_at")
    list_filter = ("created_at",)
    search_fields = ("id", "user__email", "user__username")
    readonly_fields = ("created_at", "updated_at")
    inlines = (ConfigurationModuleInline, ConfigurationEngineeringInline)


@admin.register(ConfigurationModule)
class ConfigurationModuleAdmin(admin.ModelAdmin):
    list_display = ("id", "configuration", "module", "quantity")
    search_fields = ("configuration__id", "module__name")


@admin.register(ConfigurationEngineeringSystem)
class ConfigurationEngineeringSystemAdmin(admin.ModelAdmin):
    list_display = ("id", "configuration", "engineering_system", "quantity")
    search_fields = ("configuration__id", "engineering_system__title", "engineering_system__code")
