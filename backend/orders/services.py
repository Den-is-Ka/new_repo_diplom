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
    Расширенный snapshot для диплома:
    - modules
    - engineering_systems
    - контакты (company_name/email/phone)
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

    # --- ✅ ШАГ 3: engineering systems (под твою схему: engineering_system) ---
    engineering_systems = []
    engineering_rel = getattr(cfg, "engineering_items", None)
    if engineering_rel is not None:
        # В твоей модели связь называется engineering_system (а не option)
        try:
            items = engineering_rel.select_related(
                "engineering_system",
                "engineering_system__group",  # если group есть у engineering_system
            ).all()
        except Exception:
            # если group нет — или select_related не подходит — просто all()
            items = engineering_rel.all()

        for item in items:
            # основное: engineering_system
            es = getattr(item, "engineering_system", None)

            # группа, если есть
            group = getattr(es, "group", None) if es is not None else None

            # цена: в конфиге обычно хранится price_at_selection
            price_at_selection = getattr(item, "price_at_selection", None)

            engineering_systems.append(
                {
                    "id": getattr(es, "id", None) if es is not None else getattr(item, "id", None),
                    "name": getattr(es, "name", None) if es is not None else None,
                    "group": getattr(group, "name", None) if group is not None else None,
                    "quantity": getattr(item, "quantity", None),
                    "price": (
                        str(price_at_selection)
                        if price_at_selection is not None
                        else (
                            str(getattr(es, "price", None))
                            if es is not None and getattr(es, "price", None) is not None
                            else None
                        )
                    ),
                }
            )

    # --- ✅ ШАГ 3: контакты ---
    u = getattr(cfg, "user", None)

    # ✅ FIX: приоритет выражений сделан однозначным
    company_name = getattr(cfg, "company_name", None) or (
        getattr(u, "company_name", None) if u is not None else None
    )
    email = getattr(cfg, "email", None) or (getattr(u, "email", None) if u is not None else None)
    phone = (
        getattr(cfg, "phone", None)
        or (getattr(u, "phone", None) if u is not None else None)
        or (getattr(u, "phone_number", None) if u is not None else None)
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

    # ✅ STEP 1: назначать менеджера можно ТОЛЬКО на NEW заказ
    if order.status != OrderStatus.NEW:
        raise ValueError("Manager can be assigned only to NEW order")

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

    update_fields = ["status", "updated_at"]

    # ✅ ШАГ 2: бизнес-фиксация дат (не перетираем, если уже стоят)
    if new_status == OrderStatus.APPROVED and getattr(order, "quoted_at", None) is None:
        order.quoted_at = timezone.now()
        update_fields.append("quoted_at")

    if new_status == OrderStatus.COMPLETED and getattr(order, "completed_at", None) is None:
        order.completed_at = timezone.now()
        update_fields.append("completed_at")

    order.save(update_fields=update_fields)

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
