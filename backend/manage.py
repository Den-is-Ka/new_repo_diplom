"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def main():
    # Загружаем .env из корня проекта
    env_path = Path(__file__).resolve().parent / '.env'
    print(f"1. Путь к .env: {env_path}")
    print(f"2. Файл существует: {env_path.exists()}")
    
    # Загружаем переменные
    loaded = load_dotenv(env_path, override=True)
    print(f"3. load_dotenv вернул: {loaded}")
    
    # Проверяем переменные
    print("4. Проверка переменных:")
    print(f"   POSTGRES_DB: {os.environ.get('POSTGRES_DB')}")
    print(f"   POSTGRES_USER: {os.environ.get('POSTGRES_USER')}")
    print(f"   POSTGRES_PASSWORD: {os.environ.get('POSTGRES_PASSWORD')}")
    print(f"   POSTGRES_HOST: {os.environ.get('POSTGRES_HOST')}")
    print(f"   POSTGRES_PORT: {os.environ.get('POSTGRES_PORT')}")
    
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()