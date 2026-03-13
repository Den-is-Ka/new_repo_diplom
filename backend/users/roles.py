MANUFACTURER_GROUP = "manufacturer"


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def is_manager(user) -> bool:
    # manager по ТЗ — отдельный флаг, не обязан быть is_staff
    return bool(user and user.is_authenticated and getattr(user, "is_manager", False))


def is_manufacturer(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and user.groups.filter(name=MANUFACTURER_GROUP).exists()
    )


def can_manage_orders(user) -> bool:
    """
    По ТЗ:
    - manager видит все заказы и может менять статус
    - manufacturer видит все заказы и может менять статус
    - admin/staff — полный доступ
    """
    return bool(is_admin(user) or is_manager(user) or is_manufacturer(user))


def is_client(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and not is_admin(user)
        and not is_manager(user)
        and not is_manufacturer(user)
    )
