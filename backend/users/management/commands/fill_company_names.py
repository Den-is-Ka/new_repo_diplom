"""
Команда для заполнения поля company_name у существующих пользователей
Использование: python manage.py fill_company_names
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Command(BaseCommand):
    help = _("Заполняет поле company_name для существующих пользователей")

    def add_arguments(self, parser):
        """Добавление аргументов командной строки"""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=_("Показать какие изменения будут сделаны без сохранения"),
        )
        parser.add_argument(
            "--default-name",
            type=str,
            default="",
            help=_("Имя компании по умолчанию для пользователей без email"),
        )

    def generate_company_name(self, user, default_name):
        """
        Генерирует имя компании на основе данных пользователя
        """
        # Если у пользователя уже есть нормальное имя компании
        if user.company_name and user.company_name not in [
            "",
            "Не указано",
            "Без компании",
        ]:
            return None  # Не менять

        # Вариант 1: Использовать email домен
        if user.email and "@" in user.email:
            domain = user.email.split("@")[1]

            # Красивые имена для популярных доменов
            domain_names = {
                "gmail.com": "Частное лицо",
                "mail.ru": "Частное лицо",
                "yandex.ru": "Частное лицо",
                "outlook.com": "Частное лицо",
                "hotmail.com": "Частное лицо",
            }

            if domain in domain_names:
                return domain_names[domain]
            else:
                # Берем часть до точки
                company_part = domain.split(".")[0]
                return f"{company_part.capitalize()} Company"

        # Вариант 2: Использовать username
        elif user.username:
            return f"Пользователь {user.username}"

        # Вариант 3: Значение по умолчанию
        else:
            return default_name or "Частное лицо"

    def handle(self, *args, **options):
        """Основная логика команды"""
        dry_run = options["dry_run"]
        default_name = options["default_name"]

        self.stdout.write(self.style.SUCCESS("Начинаю обработку пользователей..."))

        # Получаем всех пользователей
        users = User.objects.all()
        total_users = users.count()
        updated_count = 0

        self.stdout.write(f"Всего пользователей: {total_users}")

        for i, user in enumerate(users, 1):
            # Генерируем новое имя компании
            new_company_name = self.generate_company_name(user, default_name)

            if new_company_name:
                # Показываем изменение
                self.stdout.write(
                    f"{i}/{total_users}: {user.username} "
                    f'({user.email}) -> "{new_company_name}"'
                )

                if not dry_run:
                    # Сохраняем изменение
                    user.company_name = new_company_name
                    user.save()
                    updated_count += 1
            else:
                # Пропускаем пользователей с уже заполненным полем
                self.stdout.write(
                    f'{i}/{total_users}: {user.username} - уже заполнено: "{user.company_name}"'
                )

        # Итоговая статистика
        self.stdout.write("\n" + "=" * 50)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"РЕЖИМ ПРОСМОТРА: Будет обновлено {updated_count} пользователей"
                )
            )
            self.stdout.write(
                self.style.WARNING("Для реального обновления запустите без --dry-run")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ ОБНОВЛЕНО {updated_count} из {total_users} пользователей"
                )
            )

        self.stdout.write("=" * 50)
