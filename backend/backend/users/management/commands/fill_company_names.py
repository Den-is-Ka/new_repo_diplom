from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Command(BaseCommand):
    help = _("аполняет поле company_name для существующих пользователей")

    def handle(self, *args, **options):
        users = User.objects.all()
        updated_count = 0

        for user in users:
            old_name = user.company_name

            # сли поле содержит дефолтное значение или пустое
            if not old_name or old_name in ["", "омпания не указана", "ез компании"]:
                # енерируем имя компании на основе email
                if user.email and "@" in user.email:
                    domain = user.email.split("@")[1]

                    # ля личных доменов
                    if domain in [
                        "gmail.com",
                        "mail.ru",
                        "yandex.ru",
                        "outlook.com",
                        "hotmail.com",
                    ]:
                        user.company_name = "астное лицо"
                    else:
                        # ерем первую часть домена до точки
                        company_part = domain.split(".")[0]
                        user.company_name = f"омпания {company_part.title()}"

                # ли на основе username
                elif user.username:
                    user.company_name = f"ользователь {user.username}"

                # ли оставляем как есть
                else:
                    user.company_name = "еизвестная компания"

                user.save()
                updated_count += 1
                self.stdout.write(
                    f'{user.username}: "{old_name}" → "{user.company_name}"'
                )

        self.stdout.write(self.style.SUCCESS(f"бновлено {updated_count} пользователей"))
