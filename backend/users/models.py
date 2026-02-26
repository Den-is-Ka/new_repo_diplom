import secrets

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Кастомная модель пользователя по ТЗ"""

    # 1. ОБЯЗАТЕЛЬНЫЕ ПОЛЯ ПО ТЗ:
    # ============================
    company_name = models.CharField(
        _("Название предприятия"),
        max_length=200,
        help_text=_("Обязательное поле по ТЗ"),
    )

    # Делаем email обязательным и уникальным (переопределяем поле из AbstractUser)
    email = models.EmailField(
        _("Email адрес"),
        unique=True,  # Email должен быть уникальным
        help_text=_("Обязательное поле по ТЗ"),
    )

    # Телефон (переименуем существующее поле для соответствия ТЗ)
    phone = models.CharField(
        _("Телефон"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Необязательное поле по ТЗ"),
    )

    # 2. ПОДТВЕРЖДЕНИЕ EMAIL ПО ТЗ:
    # =============================
    email_confirmed = models.BooleanField(
        _("Email подтверждён"),
        default=False,
        help_text=_("После подтверждения email появляется доступ к форме предрасчёта"),
    )

    confirmation_token = models.CharField(
        _("Токен подтверждения"),
        max_length=64,  # Увеличим для безопасности
        blank=True,
        default="",
    )

    confirmation_sent_at = models.DateTimeField(
        _("Токен отправлен"), blank=True, null=True
    )

    # 3. ДОПОЛНИТЕЛЬНЫЕ ПОЛЯ ДЛЯ БИЗНЕС-ЛОГИКИ:
    # =========================================
    position = models.CharField(_("Должность"), max_length=100, blank=True)

    is_customer = models.BooleanField(_("Заказчик"), default=True)

    is_manager = models.BooleanField(_("Менеджер"), default=False)

    is_blocked = models.BooleanField(
        _("Заблокирован"),
        default=False,
        help_text=_("Пользователь заблокирован и не может создавать конфигурации"),
    )

    registration_ip = models.GenericIPAddressField(
        _("IP регистрации"), blank=True, null=True
    )

    last_activity = models.DateTimeField(_("Последняя активность"), auto_now=True)

    # 4. ИСПРАВЛЕНИЕ КОНФЛИКТОВ (ваш существующий код):
    # =================================================
    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name=_("Группы"),
        blank=True,
        help_text=_("Группы, к которым принадлежит пользователь."),
        related_name="custom_user_set",  # Уникальный related_name
        related_query_name="user",
    )

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name=_("Права пользователя"),
        blank=True,
        help_text=_("Конкретные права для этого пользователя."),
        related_name="custom_user_set",  # Уникальный related_name
        related_query_name="user",
    )

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")
        ordering = ["-date_joined"]  # Сортировка по дате регистрации (новые сверху)

    def __str__(self):
        """Строковое представление"""
        return self.email or self.username

    # 5. МЕТОДЫ ДЛЯ ПОДТВЕРЖДЕНИЯ EMAIL:
    # ===================================
    def generate_confirmation_token(self):
        """Генерация токена для подтверждения email"""
        from django.utils import timezone

        # Генерируем криптографически безопасный токен
        self.confirmation_token = secrets.token_urlsafe(48)
        self.confirmation_sent_at = timezone.now()
        self.email_confirmed = False  # Сбрасываем статус подтверждения
        self.save()

        return self.confirmation_token

    def confirm_email(self, token):
        """Подтверждение email по токену"""
        from datetime import timedelta

        from django.utils import timezone

        # Проверяем, не истек ли токен (48 часов)
        if self.confirmation_sent_at:
            token_age = timezone.now() - self.confirmation_sent_at
            if token_age > timedelta(hours=48):
                return False, "Срок действия токена истек"

        # Проверяем токен
        if secrets.compare_digest(token, self.confirmation_token):
            self.email_confirmed = True
            self.confirmation_token = ""  # Очищаем использованный токен
            self.confirmation_sent_at = None
            self.save()
            return True, "Email успешно подтвержден"

        return False, "Неверный токен подтверждения"

    def can_access_configurator(self):
        """
        Проверка доступа к конфигуратору по ТЗ
        По ТЗ: доступ к форме предрасчёта только после подтверждения email
        """
        return self.email_confirmed and not self.is_blocked

    # 6. ПЕРЕОПРЕДЕЛЕНИЕ save() ДЛЯ ВАЛИДАЦИИ:
    # ========================================
    def save(self, *args, **kwargs):
        """Дополнительная валидация при сохранении"""

        # Проверяем обязательные поля по ТЗ
        if not self.company_name:
            raise ValueError("Поле 'Название предприятия' обязательно по ТЗ")

        if not self.email:
            raise ValueError("Поле 'Email' обязательно по ТЗ")

        # Если это новый пользователь, генерируем токен подтверждения
        is_new = self.pk is None

        # Сохраняем пользователя
        super().save(*args, **kwargs)

        # Для нового пользователя генерируем токен
        if is_new:
            self.generate_confirmation_token()
