from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # чтобы не упереться в CSRF/SessionAuth

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        email = (request.data.get("email") or "").strip()

        if not username or not password:
            return Response({"detail": "username и password обязательны"}, status=400)

        if User.objects.filter(**{User.USERNAME_FIELD: username}).exists():
            return Response({"detail": "Пользователь уже существует"}, status=400)

        u = User(**{User.USERNAME_FIELD: username})
        # если у модели есть email
        if hasattr(u, "email") and email:
            u.email = email

        u.is_active = True
        u.set_password(password)

        # роль client — подстройка под твою реализацию
        if hasattr(u, "role"):
            u.role = "client"
        u.save()

        # если роли через группы — добавим в группу client
        try:
            g, _ = Group.objects.get_or_create(name="client")
            u.groups.add(g)
        except Exception:
            pass

        return Response(
            {"id": u.id, "username": getattr(u, User.USERNAME_FIELD)},
            status=status.HTTP_201_CREATED,
        )


from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

User = get_user_model()


class RegisterView(APIView):
    """
    Простая регистрация для демо:
    POST /api/users/register/
    body: { "username": "...", "password": "...", "email": "..."? }

    Создаёт активного пользователя и назначает роль client (если поле role есть),
    либо добавляет в группу client (если используете groups).
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # важно: чтобы не упереться в SessionAuth/CSRF

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        email = (request.data.get("email") or "").strip()

        if not username or not password:
            return Response(
                {"detail": "username и password обязательны"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Если username-field у кастомного пользователя другой — используем USERNAME_FIELD
        username_field = User.USERNAME_FIELD
        if User.objects.filter(**{username_field: username}).exists():
            return Response(
                {"detail": "Пользователь уже существует"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        u = User(**{username_field: username})

        # если у модели есть email — заполним
        if hasattr(u, "email") and email:
            u.email = email

        u.is_active = True
        u.set_password(password)

        # роль через поле role (если есть)
        if hasattr(u, "role"):
            try:
                u.role = "client"
            except Exception:
                pass

        u.save()

        # роль через группу client (если группы используются)
        try:
            g, _ = Group.objects.get_or_create(name="client")
            u.groups.add(g)
        except Exception:
            pass

        return Response(
            {"id": u.id, "username": getattr(u, username_field)},
            status=status.HTTP_201_CREATED,
        )
