from django.contrib import admin
from .models import Configuration, ConfigurationModule


class ConfigurationModuleInline(admin.TabularInline):
    """Inline для отображения модулей в конфигурации"""
    model = ConfigurationModule
    extra = 1
    readonly_fields = ['module_price', 'module_price_type']
    
    def module_price(self, obj):
        return obj.module.price if obj.module.price else "—"
    module_price.short_description = 'ена модуля'
    
    def module_price_type(self, obj):
        return obj.module.get_price_type_display()
    module_price_type.short_description = 'Тип цены'


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'name', 
        'user', 
        'main_category', 
        'sub_category', 
        'status',
        'total_price',
        'created_at'
    ]
    list_filter = ['status', 'main_category', 'sub_category', 'created_at']
    search_fields = ['name', 'description', 'user__username', 'order_number']
    readonly_fields = [
        'order_number', 
        'total_price', 
        'created_at', 
        'updated_at'
    ]
    fieldsets = (
        ('сновная информация', {
            'fields': (
                'name', 
                'description', 
                'user',
                'status',
                'order_number'
            )
        }),
        ('ыбор оборудования', {
            'fields': (
                'main_category', 
                'sub_category'
            )
        }),
        ('онфигурация контейнера', {
            'fields': ('container_config',),
            'classes': ('collapse',)
        }),
        ('онтактные данные', {
            'fields': ('company_name', 'phone', 'email'),
            'classes': ('collapse',)
        }),
        ('инансовые данные', {
            'fields': ('total_price',),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [ConfigurationModuleInline]
    list_select_related = ['user', 'main_category', 'sub_category']


@admin.register(ConfigurationModule)
class ConfigurationModuleAdmin(admin.ModelAdmin):
    list_display = ['id', 'configuration', 'module', 'quantity']
    list_filter = ['configuration__status']
    search_fields = [
        'configuration__name', 
        'module__name',
        'configuration__order_number'
    ]
