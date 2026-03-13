from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create demo superuser with required custom fields."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin", type=str)
        parser.add_argument("--email", default="admin@example.com", type=str)
        parser.add_argument("--password", default="Admin12345!", type=str)
        parser.add_argument("--company", default="ООО ДипломТест", type=str)

    def handle(self, *args, **opts):
        User = get_user_model()
        username = opts["username"]
        email = opts["email"]
        password = opts["password"]
        company = opts["company"]

        u, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "company_name": company,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        u.email = email
        u.company_name = company
        u.is_staff = True
        u.is_superuser = True
        u.set_password(password)
        u.save()

        self.stdout.write(
            self.style.SUCCESS(f"OK: username={username} created={created} id={u.id}")
        )
