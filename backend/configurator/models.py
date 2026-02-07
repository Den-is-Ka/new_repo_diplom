from django.db import models
from django.conf import settings
from catalog.models import EquipmentType, EquipmentModule
import uuid


class ConfigurationStatus(models.TextChoices):
    """Статусы конфигурации"""
    DRAFT = 'draft', 'Черновик'
    VALID = 'valid', 'Валидная'
    INVALID = 'invalid', 'Невалидная'


class Configuration(models.Model):
    """Модель конфигурации оборудования с модулями"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='configurations',
        verbose_name='Пользователь'
    )
    name = models.CharField(
        max_length=255,
        default='Новая конфигурация',
        verbose_name='Название конфигурации'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание конфигурации'
    )
    status = models.CharField(
        max_length=20,
        choices=ConfigurationStatus.choices,
        default=ConfigurationStatus.DRAFT,
        verbose_name='Статус'
    )
    
    # Тип оборудования (EquipmentType)
    equipment_type = models.ForeignKey(
        EquipmentType,
        on_delete=models.CASCADE,
        related_name='configurations',
        verbose_name='Тип оборудования'
    )
    
    # Выбранные модули (EquipmentModule)
    modules = models.ManyToManyField(
        EquipmentModule,
        related_name='configurations',
        blank=True,
        verbose_name='Модули'
    )
    
    # Кэшированная стоимость (обновляется при сохранении)
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Общая стоимость'
    )
    
    # Валидация совместимости
    compatibility_errors = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Ошибки совместимости'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Конфигурация'
        verbose_name_plural = 'Конфигурации'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()}) - {self.user.email}"

    def calculate_total_price(self):
        """Расчет общей стоимости конфигурации"""
        # Для EquipmentType нет поля price, считаем только стоимость модулей
        total = 0
        
        if self.modules.exists():
            for module in self.modules.all():
                if module.price_type == module.PriceType.FIXED and module.price:
                    total += module.price
        
        return total

    def check_compatibility(self):
        """
        Проверка совместимости оборудования и модулей.
        Возвращает список ошибок совместимости.
        """
        errors = []
        
        # 1. Проверка совместимости модулей с типом оборудования
        for module in self.modules.all():
            # Проверяем, подходит ли модуль для данного типа оборудования
            if not module.equipment_type == self.equipment_type:
                errors.append(
                    f"Модуль '{module.name}' не совместим с типом оборудования "
                    f"'{self.equipment_type.name}'. "
                    f"Модуль предназначен для типа '{module.equipment_type.name}'."
                )
        
        # 2. Проверка правил совместимости
        selected_module_ids = list(self.modules.values_list('id', flat=True))
        
        # Получаем все активные правила совместимости для выбранных модулей
        from catalog.models import CompatibilityRule
        rules = CompatibilityRule.objects.filter(
            modules__id__in=selected_module_ids,
            is_active=True
        ).distinct()
        
        for rule in rules:
            if rule.rule_type == CompatibilityRule.RuleType.EXCLUSION:
                # Проверка взаимоисключений
                module_ids_in_rule = list(rule.modules.values_list('id', flat=True))
                selected_count = len(set(module_ids_in_rule) & set(selected_module_ids))
                
                if selected_count > 1:
                    module_names = rule.modules.filter(id__in=selected_module_ids).values_list('name', flat=True)
                    errors.append(
                        f"Взаимоисключение: модули {', '.join(module_names)} "
                        f"не могут быть выбраны вместе (правило: {rule.name})"
                    )
            
            elif rule.rule_type == CompatibilityRule.RuleType.REQUIREMENT:
                # Проверка требований
                if rule.required_module and rule.required_module.id not in selected_module_ids:
                    module_names = rule.modules.values_list('name', flat=True)
                    errors.append(
                        f"Требование: при выборе модулей {', '.join(module_names)} "
                        f"необходимо выбрать модуль {rule.required_module.name} "
                        f"(правило: {rule.name})"
                    )
            
            elif rule.rule_type == CompatibilityRule.RuleType.LIMIT:
                # Проверка ограничений количества
                if rule.max_quantity:
                    module_ids_in_rule = list(rule.modules.values_list('id', flat=True))
                    selected_count = len(set(module_ids_in_rule) & set(selected_module_ids))
                    
                    if selected_count > rule.max_quantity:
                        module_names = rule.modules.filter(id__in=selected_module_ids).values_list('name', flat=True)
                        errors.append(
                            f"Ограничение: нельзя выбрать более {rule.max_quantity} "
                            f"модулей из группы {', '.join(module_names)} "
                            f"(правило: {rule.name})"
                        )
        
        return errors

    def save(self, *args, **kwargs):
        """Переопределяем сохранение для автоматической проверки и расчета"""
        # Рассчитываем стоимость
        self.total_price = self.calculate_total_price()
        
        # Проверяем совместимость
        compatibility_errors = self.check_compatibility()
        self.compatibility_errors = compatibility_errors
        
        # Обновляем статус
        if compatibility_errors:
            self.status = ConfigurationStatus.INVALID
        else:
            self.status = ConfigurationStatus.VALID
        
        super().save(*args, **kwargs)

    def is_valid(self):
        """Быстрая проверка валидности конфигурации"""
        return self.status == ConfigurationStatus.VALID and not self.compatibility_errors

    @property
    def equipment_type_details(self):
        """Детали типа оборудования для API"""
        return {
            'id': str(self.equipment_type.id),
            'name': self.equipment_type.name,
            'description': self.equipment_type.description,
        }

    @property
    def modules_details(self):
        """Детали модулей для API"""
        return [
            {
                'id': str(module.id),
                'name': module.name,
                'description': module.description,
                'price_type': module.price_type,
                'price': str(module.price) if module.price else None,
                'display_price': module.display_price,
                'equipment_type': module.equipment_type.name,
            }
            for module in self.modules.all()
        ]