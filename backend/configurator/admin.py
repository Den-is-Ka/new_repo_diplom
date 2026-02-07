from django.contrib import admin
from .models import Configuration


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'equipment_type', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'user__email', 'equipment_type__name')
    readonly_fields = ('total_price', 'compatibility_errors', 'created_at', 'updated_at')
    filter_horizontal = ('modules',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'name', 'description', 'status')
        }),
        ('Оборудование и модули', {
            'fields': ('equipment_type', 'modules')
        }),
        ('Расчеты и проверки', {
            'fields': ('total_price', 'compatibility_errors')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        }),
    )
