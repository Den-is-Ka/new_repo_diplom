from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = (
        "Seed demo environment in one command:\n"
        "- load fixtures/demo_catalog.json\n"
        "- run demo user commands: create_admin, create_demo_users, fill_company_names\n"
        "Optional: run create_test_data via --with-test-data\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="demo_catalog.json",
            help="Fixture file name inside BASE_DIR/fixtures (default: demo_catalog.json)",
        )
        parser.add_argument(
            "--skip-fixtures",
            action="store_true",
            help="Do not load fixture file",
        )
        parser.add_argument(
            "--skip-users",
            action="store_true",
            help="Do not run user/demo related commands",
        )
        parser.add_argument(
            "--with-test-data",
            action="store_true",
            help="Additionally run create_test_data command (if exists)",
        )

    def handle(self, *args, **opts):
        base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
        fixtures_dir = base_dir / "fixtures"
        fixture_path = fixtures_dir / opts["fixture"]

        self.stdout.write(self.style.MIGRATE_HEADING("=== seed_demo_catalog ==="))
        self.stdout.write(f"BASE_DIR: {base_dir}")
        self.stdout.write(f"Fixtures dir: {fixtures_dir}")

        # 1) Load fixtures
        if not opts["skip_fixtures"]:
            self.stdout.write(self.style.WARNING("[1/2] Loading fixture..."))
            if not fixture_path.exists():
                self.stderr.write(self.style.ERROR(f"Fixture not found: {fixture_path}"))
                self.stderr.write(self.style.WARNING("Expected: BASE_DIR/fixtures/<fixture>.json"))
                return

            self.stdout.write(self.style.WARNING(f"Loading fixture: {fixture_path.name}"))
            try:
                call_command("loaddata", str(fixture_path))
                self.stdout.write(self.style.SUCCESS("Fixture loaded ✅"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"loaddata failed: {e}"))
                self.stderr.write(self.style.WARNING("Tip: run migrations first: python manage.py migrate"))
                raise

        # 2) Seed users / demo helpers
        if not opts["skip_users"]:
            cmds = ["create_admin", "create_demo_users", "fill_company_names"]
            if opts["with_test_data"]:
                cmds.append("create_test_data")

            self.stdout.write(self.style.WARNING("[2/2] Running management commands..."))
            for cmd in cmds:
                try:
                    self.stdout.write(self.style.WARNING(f"Running: {cmd}"))
                    call_command(cmd)
                    self.stdout.write(self.style.SUCCESS(f"{cmd}: OK ✅"))
                except Exception as e:
                    # не валим весь seed из-за одной команды, но явно показываем
                    self.stderr.write(self.style.ERROR(f"{cmd} failed ❌: {e}"))

        self.stdout.write(self.style.SUCCESS("seed_demo_catalog done ✅"))
