# backend/orders/services.py
from decimal import Decimal
from typing import Any, Dict, Tuple

from django.db import transaction
from django.utils import timezone

from configurator.models import Configuration
from .models import Order


def _cat_to_dict(cat) -> Dict[str, Any] | None:
    if not cat:
        return None
    return {
        "id": cat.id,
        "code": getattr(cat, "code", None),
        "name": getattr(cat, "name", str(cat)),
        "parent_id": getattr(cat, "parent_id", None),
    }


def build_order_snapshot(cfg: Configuration) -> Dict[str, Any]:
    main_cat = getattr(cfg, "main_category", None)
    sub_cat = getattr(cfg, "sub_category", None)

    modules = []
    for item in cfg.module_items.select_related("module", "module__category").all():
        m = item.module
        qty = int(item.quantity or 0)
        unit_price = m.price if m.price is not None else Decimal("0.00")
        line_total = unit_price * qty

        modules.append(
            {
                "id": m.id,
                "name": m.name,
                "category": _cat_to_dict(getattr(m, "category", None)),
                "price_type": getattr(m, "price_type", None),
                "unit_price": str(unit_price),
                "quantity": qty,
                "line_total": str(line_total),
            }
        )

    eng = []
    for item in cfg.engineering_items.select_related("engineering_system").all():
        s = item.engineering_system
        qty = int(item.quantity or 0)
        unit_price = item.price_at_selection if item.price_at_selection is not None else (s.price or Decimal("0.00"))
        line_total = (unit_price or Decimal("0.00")) * qty

        eng.append(
            {
                "id": s.id,
                "code": getattr(s, "code", None),
                "title": getattr(s, "title", str(s)),
                "price_type": getattr(s, "price_type", None),
                "unit_price": str(unit_price),
                "quantity": qty,
                "line_total": str(line_total),
                "custom_parameters": item.custom_parameters,
            }
        )

    total = cfg.calculate_total_price()

    return {
        "configuration_id": cfg.id,
        "configuration_name": cfg.name,
        "submitted_at": timezone.now().isoformat(),
        "main_category": _cat_to_dict(main_cat),
        "sub_category": _cat_to_dict(sub_cat),
        "container_config": cfg.container_config or {},
        "modules": modules,
        "engineering_systems": eng,
        "total_price": str(total),
    }


def create_order_from_configuration(cfg: Configuration) -> Tuple[Order, bool]:
    """
    Идемпотентно создает Order по configuration:
    - если заказа нет -> создаёт и фиксирует snapshot
    - если заказ есть -> возвращает его (created=False), ничего не перетирая,
      но может ДОЗАПОЛНИТЬ пустые поля (snapshot/order_number/total_price)
    """
    if not cfg.order_number:
        raise ValueError("Configuration has no order_number. Submit must set it first.")

    snapshot = build_order_snapshot(cfg)
    total_decimal = cfg.calculate_total_price()

    user = cfg.user
    company_name = cfg.company_name or getattr(user, "company_name", "") or ""
    phone = cfg.phone or getattr(user, "phone", "") or ""
    email = cfg.email or getattr(user, "email", "") or ""

    defaults = {
        "user": user,
        "order_number": cfg.order_number,
        "status": Order.Status.NEW,
        "company_name": company_name,
        "phone": phone,
        "email": email,
        "total_price": total_decimal,
        "snapshot": snapshot,
    }

    with transaction.atomic():
        order, created = Order.objects.get_or_create(configuration=cfg, defaults=defaults)

        if not created:
            # ничего не перетираем, только дозаполняем пустое
            changed = False
            update_fields = []

            if not order.order_number and cfg.order_number:
                order.order_number = cfg.order_number
                changed = True
                update_fields.append("order_number")

            if not order.snapshot:
                order.snapshot = snapshot
                changed = True
                update_fields.append("snapshot")

            if (order.total_price is None) or (order.total_price == Decimal("0.00")):
                order.total_price = total_decimal
                changed = True
                update_fields.append("total_price")

            if changed:
                update_fields.append("updated_at")
                order.save(update_fields=update_fields)

    return order, created
