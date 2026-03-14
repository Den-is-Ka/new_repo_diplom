import os
from dotenv import load_dotenv
from pathlib import Path

print('='*50)
print('ПРОВЕРКА ЗАГРУЗКИ .env ФАЙЛА')
print('='*50)

# Текущая директория
print(f'\n1. Текущая директория: {Path.cwd()}')

# Проверяем наличие .env файла
env_path = Path('.env')
print(f'2. .env файл существует: {env_path.exists()}')

if env_path.exists():
    print(f'3. Размер .env файла: {env_path.stat().st_size} байт')

# Загружаем .env
load_dotenv()
print('4. load_dotenv() выполнен')

# Проверяем переменные
print('\n5. Значения переменных из os.getenv():')
print(f'   POSTGRES_DB: {os.getenv("POSTGRES_DB")}')
print(f'   POSTGRES_USER: {os.getenv("POSTGRES_USER")}')
print(f'   POSTGRES_HOST: {os.getenv("POSTGRES_HOST")}')
print(f'   POSTGRES_PORT: {os.getenv("POSTGRES_PORT")}')

print('\n6. Проверка через os.environ.get():')
print(f'   POSTGRES_DB: {os.environ.get("POSTGRES_DB")}')
print(f'   POSTGRES_USER: {os.environ.get("POSTGRES_USER")}')
print('='*50)
