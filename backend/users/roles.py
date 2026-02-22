MANUFACTURER_GROUP = "manufacturer"

def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))

def is_manufacturer(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and user.groups.filter(name=MANUFACTURER_GROUP).exists()
    )

def is_client(user) -> bool:
    return bool(user and user.is_authenticated and not is_admin(user) and not is_manufacturer(user))
