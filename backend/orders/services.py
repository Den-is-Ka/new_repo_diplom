from __future__ import annotations

from typing import Any, Dict, Tuple

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from configurator.models import Configuration
from orders.models import Order, OrderStatus, OrderStatusHistory

User = get_user_model()

# Разрешённые переходы статусов (матрица)
ALLOWED_TRANSITIONS = {
    OrderStatus.NEW: {OrderStatus.IN_REVIEW},
    OrderStatus.IN_REVIEW: {OrderStatus.APPROVED, OrderStatus.REJECTED},
    OrderStatus.APPROVED: {OrderStatus.IN_PRODUCTION},
    OrderStatus.REJECTED: set(),
    OrderStatus.IN_PRODUCTION: {OrderStatus.COMPLETED},
    OrderStatus.COMPLETED: set(),
}


def _is_manager(user: User) -> bool:
    """
    MVP: менеджер = staff/superuser.
    """
    if not user or not user.is_authenticated:
        return False
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))


def _require_manager(user: User) -> None:
    if not _is_manager(user):
        raise PermissionError("Only manager can perform this action.")


def _validate_transition(from_status: str, to_status: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ValueError(f"Transition {from_status} -> {to_status} is not allowed.")


def _generate_order_number() -> str:
    date_str = timezone.now().strftime("%Y%m%d")
    suffix = timezone.now().strftime("%H%M%S%f")[-8:]
    return f"ORD-{date_str}-{suffix}"


def _build_snapshot_min(cfg: Configuration) -> Dict[str, Any]:
    """
    Минимальный snapshot (достаточно для диплома/проверок).
    """
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

    return {
        "configuration": {
            "id": cfg.id,
            "status": cfg.status,
            "name": cfg.name,
        },
        "total_price": str(cfg.calculate_total_price()),
        "modules": modules,
    }


@transaction.atomic
def submit_configuration(configuration_id: int, user: User) -> Tuple[Order, bool]:
    """
    Идемпотентный submit:
      - select_for_update на Configuration
      - если Order уже есть -> created=False
      - фиксируем cfg.status=submitted ДО snapshot
      - создаём Order
    """
    cfg = Configuration.objects.select_for_update().get(id=configuration_id)

    # идемпотентность: 1 конфиг -> 1 order
    existing = getattr(cfg, "order", None)
    if existing:
        return existing, False

    # запрет пустой конфигурации
    if not cfg.module_items.exists() and not cfg.engineering_items.exists():
        raise ValueError("Configuration is empty. Add modules or engineering systems before submit.")

    # статус ДО snapshot
    if cfg.status != cfg.Status.SUBMITTED:
        cfg.status = cfg.Status.SUBMITTED
        if getattr(cfg, "submitted_at", None) is None:
            cfg.submitted_at = timezone.now()
        cfg.save(update_fields=["status", "submitted_at", "updated_at"])

    snapshot = _build_snapshot_min(cfg)
    snapshot["submitted_by"] = getattr(user, "id", None)
    snapshot["submitted_at"] = timezone.now().isoformat()

    total_price = cfg.calculate_total_price()

    order = Order.objects.create(
        user=cfg.user if getattr(cfg, "user_id", None) else user,
        configuration=cfg,
        order_number=_generate_order_number(),
        status=OrderStatus.NEW,
        total_price=total_price,
        snapshot=snapshot,
    )
    return order, True


@transaction.atomic
def assign_manager(order_id: int, manager_user: User, actor: User) -> Order:
    """
    Назначить менеджера на заказ.
    actor должен быть менеджером (или админом).

    ВАЖНО: НЕ делаем select_related("manager") под select_for_update(),
    потому что manager nullable -> LEFT JOIN -> Postgres ругается на FOR UPDATE.
    """
    _require_manager(actor)

    order = (
        Order.objects.select_for_update()
        .select_related("user")  # manager НЕ трогаем, он nullable
        .get(id=order_id)
    )

    if order.manager_id and order.manager_id != manager_user.id:
        raise ValueError("Manager is already assigned.")

    order.manager = manager_user
    order.save(update_fields=["manager", "updated_at"])
    return order


@transaction.atomic
def change_status(order_id: int, actor: User, new_status: str, comment: str = "") -> Order:
    """
    Смена статуса заказа менеджером.
    Пишем историю переходов.
    """
    _require_manager(actor)

    if new_status not in OrderStatus.values:
        raise ValueError(f"Unknown status: {new_status}")

    order = (
        Order.objects.select_for_update()
        .select_related("user")  # manager НЕ трогаем, он nullable
        .get(id=order_id)
    )

    # если менеджер назначен — менять может только он (или суперюзер)
    if order.manager_id and order.manager_id != actor.id and not getattr(actor, "is_superuser", False):
        raise PermissionError("Only assigned manager can change this order status.")

    old_status = order.status
    if old_status == new_status:
        return order  # no-op

    _validate_transition(old_status, new_status)

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order,
        from_status=old_status,
        to_status=new_status,
        changed_by=actor,
        comment=comment or "",
    )

    return order


def manager_orders_qs(user: User) -> QuerySet[Order]:
    """
    QuerySet заказов для менеджера (для views).
    """
    _require_manager(user)
    return Order.objects.all().select_related("user", "manager").order_by("-id")


def user_orders_qs(user: User) -> QuerySet[Order]:
    """
    Заказы текущего клиента.
    """
    return Order.objects.filter(user=user).select_related("user", "manager").order_by("-id")
