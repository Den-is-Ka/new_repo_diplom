import uuid
from django.db import models
from django.contrib.auth import get_user_model
from catalog.models import EquipmentCategory, EquipmentModule
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Configuration(models.Model):
    """РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РѕР±РѕСЂСѓРґРѕРІР°РЅРёСЏ"""

    class Status(models.TextChoices):
        DRAFT = 'draft', _("Р§РµСЂРЅРѕРІРёРє")
        SUBMITTED = 'submitted', _("РћС‚РїСЂР°РІР»РµРЅ РїСЂРѕРёР·РІРѕРґРёС‚РµР»СЋ")
        PROCESSING = 'processing', _("Р’ РѕР±СЂР°Р±РѕС‚РєРµ")
        QUOTED = 'quoted', _("РЎС‡РµС‚ РІС‹СЃС‚Р°РІР»РµРЅ")
        COMPLETED = 'completed', _("Р—Р°РІРµСЂС€РµРЅ")

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='configurations',
        verbose_name=_("РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ")
    )

    # Р’С‹Р±СЂР°РЅРЅР°СЏ РѕСЃРЅРѕРІРЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ (1.1 РёР»Рё 1.2 РёР· РўР—)
    main_category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.CASCADE,
        related_name='configurations',
        verbose_name=_("РћСЃРЅРѕРІРЅРѕР№ С‚РёРї РѕР±РѕСЂСѓРґРѕРІР°РЅРёСЏ"),
        help_text=_("Р”Р“РЈ РёР»Рё РљРѕРјРїСЂРµСЃСЃРѕСЂРЅР°СЏ СѓСЃС‚Р°РЅРѕРІРєР°")
    )

    # Р’С‹Р±СЂР°РЅРЅР°СЏ РїРѕРґРєР°С‚РµРіРѕСЂРёСЏ (1.1.1, 1.2.2 Рё С‚.Рґ.)
    sub_category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.CASCADE,
        related_name='sub_configurations',
        verbose_name=_("РџРѕРґРєР°С‚РµРіРѕСЂРёСЏ"),
        help_text=_("РљРѕРЅРєСЂРµС‚РЅР°СЏ С…Р°СЂР°РєС‚РµСЂРёСЃС‚РёРєР°, РЅР°РїСЂРёРјРµСЂ: Р”Р“РЈ РґРѕ 50 РєР’С‚")
    )

    # РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РєРѕРЅС‚РµР№РЅРµСЂР° (СЂР°Р·РґРµР» 3 РёР· РўР—)
    container_config = models.JSONField(
        _("РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РєРѕРЅС‚РµР№РЅРµСЂР°"),
        default=dict,
        blank=True,
        help_text=_("РџР°СЂР°РјРµС‚СЂС‹ РєРѕРЅС‚РµР№РЅРµСЂР° РІ С„РѕСЂРјР°С‚Рµ JSON")
    )

    # РќР°Р·РІР°РЅРёРµ Рё РѕРїРёСЃР°РЅРёРµ
    name = models.CharField(_("РќР°Р·РІР°РЅРёРµ РєРѕРЅС„РёРіСѓСЂР°С†РёРё"), max_length=200)
    description = models.TextField(_("РћРїРёСЃР°РЅРёРµ"), blank=True)

    # Р’С‹Р±СЂР°РЅРЅС‹Рµ РјРѕРґСѓР»Рё
    modules = models.ManyToManyField(
        EquipmentModule,
        through='ConfigurationModule',
        related_name='configurations',
        verbose_name=_("Р’С‹Р±СЂР°РЅРЅС‹Рµ РјРѕРґСѓР»Рё")
    )

    # Р Р°СЃС‡РµС‚РЅС‹Рµ РїРѕР»СЏ
    total_price = models.DecimalField(
        _("РћР±С‰Р°СЏ СЃС‚РѕРёРјРѕСЃС‚СЊ"),
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # РЎС‚Р°С‚СѓСЃ
    status = models.CharField(
        _("РЎС‚Р°С‚СѓСЃ"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    order_number = models.CharField(
        _("РќРѕРјРµСЂ Р·Р°РєР°Р·Р°"),
        max_length=50,
        blank=True
    )

    # РљРѕРЅС‚Р°РєС‚РЅС‹Рµ РґР°РЅРЅС‹Рµ (РёР· РўР—)
    company_name = models.CharField(_("РќР°РёРјРµРЅРѕРІР°РЅРёРµ РїСЂРµРґРїСЂРёСЏС‚РёСЏ"), max_length=200, blank=True)
    phone = models.CharField(_("РўРµР»РµС„РѕРЅ"), max_length=20, blank=True)
    email = models.EmailField(_("Email"), blank=True)

    created_at = models.DateTimeField(_("Р”Р°С‚Р° СЃРѕР·РґР°РЅРёСЏ"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Р”Р°С‚Р° РѕР±РЅРѕРІР»РµРЅРёСЏ"), auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ")
        verbose_name_plural = _("РљРѕРЅС„РёРіСѓСЂР°С†РёРё")

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def calculate_total_price(self):
        """Р Р°СЃС‡РµС‚ РѕР±С‰РµР№ СЃС‚РѕРёРјРѕСЃС‚Рё"""
        total = 0
        for config_module in self.configurationmodule_set.all():
            if config_module.module.price_type == EquipmentModule.PriceType.FIXED:
                total += config_module.module.price * config_module.quantity
        return total

    def save(self, *args, **kwargs):
        # РђРІС‚РѕРјР°С‚РёС‡РµСЃРєРё СѓСЃС‚Р°РЅР°РІР»РёРІР°РµРј main_category РЅР° РѕСЃРЅРѕРІРµ sub_category
        if self.sub_category and not self.main_category:
            # РќР°С…РѕРґРёРј СЂРѕРґРёС‚РµР»СЊСЃРєСѓСЋ РєР°С‚РµРіРѕСЂРёСЋ СѓСЂРѕРІРЅСЏ 1.1 РёР»Рё 1.2
            current = self.sub_category
            while current.parent and current.parent.parent:  # РС‰РµРј РґРѕ РІС‚РѕСЂРѕРіРѕ СѓСЂРѕРІРЅСЏ
                current = current.parent
            self.main_category = current

        # РџРµСЂРµСЃС‡РёС‚С‹РІР°РµРј С†РµРЅСѓ
        self.total_price = self.calculate_total_price()

        # Р“РµРЅРµСЂРёСЂСѓРµРј РЅРѕРјРµСЂ Р·Р°РєР°Р·Р° РїСЂРё РѕС‚РїСЂР°РІРєРµ
        if self.status == self.Status.SUBMITTED and not self.order_number:
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            count = Configuration.objects.filter(
                status=self.Status.SUBMITTED,
                created_at__date=timezone.now().date()
            ).count()
            self.order_number = f"ORD-{date_str}-{count + 1:04d}"

        super().save(*args, **kwargs)


class ConfigurationModule(models.Model):
    """РЎРІСЏР·СЊ РєРѕРЅС„РёРіСѓСЂР°С†РёРё Рё РјРѕРґСѓР»РµР№ СЃ РєРѕР»РёС‡РµСЃС‚РІРѕРј"""
    configuration = models.ForeignKey(Configuration, on_delete=models.CASCADE)
    module = models.ForeignKey(EquipmentModule, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(_("РљРѕР»РёС‡РµСЃС‚РІРѕ"), default=1)

    class Meta:
        unique_together = [['configuration', 'module']]
        verbose_name = _("РњРѕРґСѓР»СЊ РІ РєРѕРЅС„РёРіСѓСЂР°С†РёРё")
        verbose_name_plural = _("РњРѕРґСѓР»Рё РІ РєРѕРЅС„РёРіСѓСЂР°С†РёСЏС…")

    def __str__(self):
        return f"{self.configuration.name} - {self.module.name} (x{self.quantity})"


