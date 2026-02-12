from django.core.management.base import BaseCommand
from users.services.demo_seed import seed_demo_users

class Command(BaseCommand):
    help = "Create demo users and demo data"

    def handle(self, *args, **options):
        seed_demo_users(stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS("Demo users created"))
