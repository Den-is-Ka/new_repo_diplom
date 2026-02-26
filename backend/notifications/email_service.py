from __future__ import annotations

from typing import List, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from orders.models import Order

User = get_user_model()


def _get_customer_email(order: Order) -> Optional[str]:
    # 1) из snapshot
    try:
        email = (order.snapshot or {}).get("customer", {}).get("email")
        if email:
            return email
    except Exception:
        pass

    # 2) из user.email
    email = getattr(order.user, "email", None)
    return email or None


def _get_manufacturer_emails() -> List[str]:
    """
    Приоритет:
    1) settings.MANUFACTURER_NOTIFY_EMAIL (один email)
    2) все пользователи из группы manufacturer (у кого заполнен email)
    """
    direct = getattr(settings, "MANUFACTURER_NOTIFY_EMAIL", None)
    if direct:
        return [direct]

    try:
        g = Group.objects.get(name="manufacturer")
    except Group.DoesNotExist:
        return []

    qs = User.objects.filter(groups=g).exclude(email="").exclude(email__isnull=True)
    return list(qs.values_list("email", flat=True))


def _send_html_email(
    subject: str, to: List[str], template_name: str, context: dict
) -> None:
    """
    Отправка HTML письма. Ошибки не пробрасываем (чтобы submit не падал),
    но выводим в консоль через print, чтобы на защите было видно, если что.
    """
    if not to:
        return

    prefix = getattr(settings, "EMAIL_SUBJECT_PREFIX", "")
    full_subject = f"{prefix}{subject}".strip()

    try:
        html = render_to_string(template_name, context)
        msg = EmailMultiAlternatives(
            subject=full_subject,
            body="HTML версия письма (если клиент не поддерживает HTML — покажет этот текст).",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            to=to,
        )
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)
    except Exception as e:
        # На дипломе лучше видеть проблему, но не ломать процесс
        print(f"[email_service] Email send failed: {e}")


def send_order_created_emails(order: Order) -> None:
    """
    Отправляет 2 письма:
    1) Клиенту: подтверждение сформированной заявки
    2) Производителю: уведомление о новой заявке
    """
    # --- 1) клиент ---
    customer_email = _get_customer_email(order)
    if customer_email:
        _send_html_email(
            subject=f"Заявка {order.order_number} сформирована",
            to=[customer_email],
            template_name="email/order_created_customer.html",
            context={"order": order},
        )
    else:
        print(f"[email_service] Customer email not found for order {order.id}")

    # --- 2) производитель ---
    manufacturer_emails = _get_manufacturer_emails()
    if manufacturer_emails:
        _send_html_email(
            subject=f"Новая заявка {order.order_number}",
            to=manufacturer_emails,
            template_name="email/order_created_manufacturer.html",
            context={"order": order},
        )
    else:
        print(
            f"[email_service] Manufacturer emails not found (no MANUFACTURER_NOTIFY_EMAIL and no group users)."
        )
