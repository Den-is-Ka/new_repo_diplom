from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create test data"

    def handle(self, *args, **options):
        # TODO: перенеси сюда логику из create_test_data.py
        self.stdout.write(self.style.SUCCESS("Test data created"))
