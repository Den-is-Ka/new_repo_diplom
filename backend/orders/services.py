from __future__ import annotations

from typing import Any, Dict, Tuple

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from configurator.models import Configuration
from configurator.services import validate_configuration_for_submit
from orders.models import Order, OrderStatus, OrderStatusHistory
from users.roles import can_manage_orders

User = get_user_model()


def _is_manager(user: User) -> bool:
    """
    Менеджер по ТЗ:
    - user.is_manager == True
    - либо staff/superuser (админка)
    """
    if not user or not user.is_authenticated:
        return False
    return bool(
        getattr(user, "is_manager", False)
        or getattr(user, "is_staff", False)
        or getattr(user, "is_superuser", False)
    )


def _require_manager(user: User) -> None:
    if not _is_manager(user):
        raise PermissionError("Only manager can perform this action.")


def _can_change_order_status(actor: User) -> bool:
    """
    Менять статус могут:
    - manager (is_manager=True) / staff / superuser
    - manufacturer (группа manufacturer)
    """
    return bool(actor and actor.is_authenticated and can_manage_orders(actor))


def _generate_order_number() -> str:
    date_str = timezone.now().strftime("%Y%m%d")
    suffix = timezone.now().strftime("%H%M%S%f")[-8:]
    return f"ORD-{date_str}-{suffix}"


def _build_snapshot_min(cfg: Configuration) -> Dict[str, Any]:
    """
    Snapshot для диплома:
    - modules (id, name, price, quantity, price_type)
    - engineering_systems (id, title, group title, price, quantity)
    - контакты
    - total_price
    """

    # ---------- modules ----------
    modules = []
    for item in cfg.module_items.select_related("module").all():
        m = item.module
        modules.append(
            {
                "id": m.id,
                "name": m.name,
                "price": str(m.price) if m.price is not None else None,
                "quantity": item.quantity,
                "price_type": m.price_type,
            }
        )

    # ---------- engineering systems ----------
    engineering_systems = []
    engineering_rel = getattr(cfg, "engineering_items", None)

    if engineering_rel is not None:
        items = engineering_rel.select_related(
            "engineering_system", "engineering_system__group"
        ).all()

        for item in items:
            es = item.engineering_system  # EngineeringSystemOption
            es_title = getattr(es, "title", None) or getattr(es, "name", None)

            group_obj = getattr(es, "group", None)
            group_title = None
            if group_obj is not None:
                group_title = getattr(group_obj, "title", None) or getattr(
                    group_obj, "name", None
                )

            price_at_selection = getattr(item, "price_at_selection", None)
            if price_at_selection is None:
                price_at_selection = getattr(es, "price", None)

            engineering_systems.append(
                {
                    "id": es.id,
                    "code": getattr(es, "code", None),
                    "title": es_title,
                    "group": group_title,
                    "price": (
                        str(price_at_selection)
                        if price_at_selection is not None
                        else None
                    ),
                    "quantity": getattr(item, "quantity", 1),
                }
            )

    # ---------- contacts ----------
    u = getattr(cfg, "user", None)

    company_name = getattr(cfg, "company_name", None) or (
        getattr(u, "company_name", None) if u else None
    )
    email = getattr(cfg, "email", None) or (getattr(u, "email", None) if u else None)
    phone = (
        getattr(cfg, "phone", None)
        or (getattr(u, "phone", None) if u else None)
        or (getattr(u, "phone_number", None) if u else None)
    )

    return {
        "configuration": {
            "id": cfg.id,
            "status": cfg.status,
            "name": cfg.name,
        },
        "customer": {
            "company_name": company_name,
            "email": email,
            "phone": phone,
        },
        "total_price": str(cfg.calculate_total_price()),
        "modules": modules,
        "engineering_systems": engineering_systems,
    }


@transaction.atomic
def submit_configuration(configuration_id: int, user: User) -> Tuple[Order, bool]:
    """
    Submit строго по ТЗ:
      - конфигурация только владельца
      - submit только из DRAFT
      - 1 конфиг -> 1 order (идемпотентно)
      - status=submitted фиксируется через cfg.save()
      - после создания заказа отправляем уведомления (клиенту + производителю)
    """
    cfg = (
        Configuration.objects.select_for_update()
        .select_related("user")
        .get(id=configuration_id, user=user)
    )

    existing = getattr(cfg, "order", None)
    if existing:
        return existing, False

    if cfg.status != cfg.Status.DRAFT:
        raise ValueError("Configuration can be submitted only from DRAFT status.")

    validate_configuration_for_submit(cfg)

    cfg.status = cfg.Status.SUBMITTED
    cfg.save()

    snapshot = _build_snapshot_min(cfg)
    snapshot["submitted_by"] = getattr(user, "id", None)
    snapshot["submitted_at"] = timezone.now().isoformat()

    total_price = cfg.calculate_total_price()

    order = Order.objects.create(
        user=cfg.user,
        configuration=cfg,
        order_number=_generate_order_number(),
        status=OrderStatus.NEW,
        total_price=total_price,
        snapshot=snapshot,
    )

    # ✅ отправка писем строго после коммита транзакции
    def _send_emails_after_commit(order_id: int) -> None:
        from notifications.email_service import send_order_created_emails

        try:
            fresh = Order.objects.select_related("user").get(id=order_id)
            send_order_created_emails(fresh)
        except Exception:
            # для диплома не валим submit из-за email
            pass

    transaction.on_commit(lambda: _send_emails_after_commit(order.id))

    return order, True


@transaction.atomic
def assign_manager(order_id: int, manager_user: User, actor: User) -> Order:
    """
    Назначить менеджера на заказ.
    В дипломной версии это админская операция: только staff.
    """
    if not (actor and actor.is_authenticated and getattr(actor, "is_staff", False)):
        raise PermissionError("Only staff can assign manager.")

    order = Order.objects.select_for_update().select_related("user").get(id=order_id)

    if order.status != OrderStatus.NEW:
        raise ValueError("Manager can be assigned only to NEW order")

    if order.manager_id and order.manager_id != manager_user.id:
        raise ValueError("Manager is already assigned.")

    order.manager = manager_user
    order.save(update_fields=["manager", "updated_at"])
    return order


@transaction.atomic
def change_status(
    order_id: int, actor: User, new_status: str, comment: str = ""
) -> Order:
    """
    Смена статуса заказа:
    - manager (is_manager=True) / staff / superuser
    - manufacturer

    Переходы валидируются через Order.transition_to() (матрица в models.py).
    Пишем историю переходов.
    """
    if not _can_change_order_status(actor):
        raise PermissionError(
            "Only manager/staff/manufacturer can perform this action."
        )

    if new_status not in OrderStatus.values:
        raise ValueError(f"Unknown status: {new_status}")

    order = Order.objects.select_for_update().select_related("user").get(id=order_id)

    # ✅ ВАЖНО ДЛЯ ТЗ:
    # По ТЗ менеджер может менять статусы заказов.
    # Поэтому НЕ ограничиваем manager1 "только назначенным менеджером".
    # (Иначе менеджер видит все, но менять почти ничего не может.)
    #
    # Если когда-нибудь нужно вернуть ограничение — делаем это отдельным флагом/настройкой.

    old_status = order.status
    if old_status == new_status:
        return order

    order.transition_to(new_status)
    order.save()

    OrderStatusHistory.objects.create(
        order=order,
        from_status=old_status,
        to_status=new_status,
        changed_by=actor,
        comment=comment or "",
    )

    return order


def manager_orders_qs(user: User) -> QuerySet[Order]:
    _require_manager(user)
    return Order.objects.all().select_related("user", "manager").order_by("-id")


def user_orders_qs(user: User) -> QuerySet[Order]:
    return (
        Order.objects.filter(user=user)
        .select_related("user", "manager")
        .order_by("-id")
    )
