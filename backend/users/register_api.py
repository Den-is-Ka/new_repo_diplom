from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()


def _pick_enterprise_field_name(user_obj) -> str | None:
    """
    Ищем поле пользователя, которое соответствует "Название предприятия".
    Сначала по имени, потом по verbose_name (русский текст).
    """
    # частые варианты имён поля
    candidates = [
        "company_name",
        "enterprise_name",
        "organization_name",
        "organisation_name",
        "company",
        "enterprise",
        "organization",
        "organisation",
    ]
    for name in candidates:
        if hasattr(user_obj, name):
            return name

    # поиск по verbose_name
    for f in user_obj._meta.fields:
        try:
            vn = str(getattr(f, "verbose_name", "")).lower()
        except Exception:
            vn = ""
        if "предприят" in vn:  # "предприятия", "предприятие"
            return f.name

    return None


def _default_value_for_required_field(field, username: str, email: str):
    """
    Подстраховка: если у кастомного User есть обязательные NOT NULL поля.
    """
    internal = field.get_internal_type()
    if internal in ("CharField", "TextField", "SlugField"):
        return username
    if internal == "EmailField":
        return email or f"{username}@example.com"
    if internal in (
        "IntegerField",
        "BigIntegerField",
        "SmallIntegerField",
        "PositiveIntegerField",
    ):
        return 0
    if internal == "BooleanField":
        return False
    if internal == "DateTimeField":
        return timezone.now()
    if internal == "DateField":
        return timezone.now().date()
    return None


class RegisterView(APIView):
    """
    POST /api/users/register/
    body: { "username": "...", "password": "...", "email": "..."?, "company_name": "..."? }

    Делает активного пользователя + пытается назначить роль client.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # без SessionAuth/CSRF

    def post(self, request):
        try:
            username_in = (request.data.get("username") or "").strip()
            password = request.data.get("password") or ""
            email_in = (request.data.get("email") or "").strip()

            company_name = (
                (request.data.get("company_name") or "")
                or (request.data.get("company") or "")
                or (request.data.get("enterprise_name") or "")
                or (request.data.get("organization_name") or "")
            ).strip()

            if not username_in or not password:
                return Response(
                    {"detail": "username и password обязательны"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # дефолт, чтобы никогда не падать на пустом предприятии
            if not company_name:
                company_name = f"Demo Company ({username_in})"

            username_field = User.USERNAME_FIELD

            # если логин-поле = email, то username считаем email
            if username_field == "email":
                username_value = username_in
                email = username_in
            else:
                username_value = username_in
                email = email_in or f"{username_in}@example.com"

            # дубль?
            if User.objects.filter(**{username_field: username_value}).exists():
                return Response(
                    {"detail": "Пользователь уже существует"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ✅ ВАЖНО: создаём вручную (НЕ через create_user), чтобы обойти валидации менеджера
            u = User(**{username_field: username_value})

            # email (если есть поле)
            if hasattr(u, "email") and not getattr(u, "email", ""):
                u.email = email

            # заполняем "Название предприятия" по имени/verbose_name
            enterprise_field = _pick_enterprise_field_name(u)
            if enterprise_field:
                setattr(u, enterprise_field, company_name)

            # подстраховка: обязательные NOT NULL поля без default
            skip = {
                "id",
                "password",
                "last_login",
                "is_superuser",
                "is_staff",
                "is_active",
                "date_joined",
                username_field,
            }
            for f in u._meta.fields:
                if f.name in skip:
                    continue
                if f.null or getattr(f, "blank", False) or f.has_default():
                    continue
                if getattr(u, f.name, None) not in (None, "", 0):
                    continue
                dv = _default_value_for_required_field(f, username_in, email)
                if dv is not None:
                    setattr(u, f.name, dv)

            u.is_active = True
            u.set_password(password)

            # role (если есть) — подбираем по choices
            if hasattr(u, "role"):
                try:
                    field = u._meta.get_field("role")
                    choices = [c[0] for c in (field.choices or [])]
                    for cand in ("client", "CLIENT", "customer", "CUSTOMER"):
                        if cand in choices:
                            u.role = cand
                            break
                    else:
                        if choices:
                            u.role = choices[0]
                except Exception:
                    pass

            u.save()

            # group client (если используете groups)
            try:
                g, _ = Group.objects.get_or_create(name="client")
                u.groups.add(g)
            except Exception:
                pass

            return Response(
                {"id": u.id, "username": username_value}, status=status.HTTP_201_CREATED
            )

        except IntegrityError as e:
            return Response(
                {"detail": f"IntegrityError: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"detail": f"{type(e).__name__}: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
