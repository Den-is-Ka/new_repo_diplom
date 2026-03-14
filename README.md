# Конфигуратор контейнерных решений (Backend + Demo UI)

Веб-приложение “Конфигуратор контейнерных решений”:
клиент собирает конфигурацию (категория → подкатегория → оборудование → инженерные системы), видит стоимость, отправляет заявку (submit).
После submit создаётся заказ (Order) со snapshot, конфигурация “замораживается” (lock), отправляются письма (console email backend).

---

## 1) Стек и технологии

Backend:
- Python / Django 5.0.14
- Django REST Framework (DRF)
- JWT (SimpleJWT)
- PostgreSQL
- drf-spectacular (Swagger/Redoc)
- WhiteNoise (static)
- corsheaders
- pytest

Email:
- Django console email backend (письма печатаются в консоль `runserver`)

Demo UI:
- Django templates + JS
- JWT в localStorage:
  - `diplom.jwt.access`
  - `diplom.jwt.refresh`

---

## 2) Роли (по ТЗ)

- client — видит только свои конфигурации/заказы
- manufacturer/manager — видит все заказы
- admin/staff — полный доступ

---

## 3) Быстрый старт

Команды выполнять из папки `backend/` (там где `manage.py`).

### 3.1 Установка зависимостей
Python venv:

Windows:
1) `python -m venv .venv`
2) `.venv\Scripts\activate`
3) `pip install -r requirements.txt`

Linux/Mac:
1) `python -m venv .venv`
2) `source .venv/bin/activate`
3) `pip install -r requirements.txt`

### 3.2 Миграции
```bash
python manage.py migrate
```

### 3.3 Демо-наполнение (каталог + пользователи)
```bash
python manage.py seed_demo_catalog
```

### 3.4 Запуск
```bash
python manage.py runserver
```

Открыть в браузере:
- UI Login:        http://127.0.0.1:8000/ui/login/
- UI Configurator: http://127.0.0.1:8000/ui/customer/
- UI Orders:       http://127.0.0.1:8000/ui/orders/
- Admin:           http://127.0.0.1:8000/admin/
- API Docs:        http://127.0.0.1:8000/api/docs/
- API Redoc:       http://127.0.0.1:8000/api/redoc/
- API Schema:      http://127.0.0.1:8000/api/schema/

---

## 4) Демо-пользователи (после seed_demo_catalog)

Команда `seed_demo_catalog` создаёт демо-аккаунты (idempotent-ish).
Точные логины/пароли печатаются в консоли при выполнении команды.

Обычно:
- `client_dgu` / пароль: `client123`
- `client_compressor` / пароль: `client123`
- `manager1` / пароль: `manager123`
- `admin` — админка/полный доступ

Если пароль admin менялся или логин не проходит, можно восстановить через Django shell:

1) `python manage.py shell`
2) Вставить:

```python
from django.contrib.auth import get_user_model

User = get_user_model()
u = User.objects.get(username="admin")
u.is_active = True
u.is_staff = True
u.is_superuser = True
u.set_password("9841Dark")
u.save()
print("admin fixed")
```

После этого логин:
- username: `admin`
- password: `9841Dark`

---

## 5) Основной сценарий (кликами в UI)

### 5.1 Вход
1) Открыть `/ui/login/`
2) Войти под клиентом (например `client_dgu / client123`)
3) Перейти в “Конфигуратор”

### 5.2 Создание заявки (черновик → отправка)
На странице `/ui/customer/`:

1) Выбрать “Основная категория” и “Подкатегория”
2) Нажать “Создать черновик с выбранными категориями”
3) Оборудование (модули):
   - “Загрузить доступные модули”
   - отметить нужные модули чекбоксами
   - “Сохранить выбранные модули”
4) Инженерные системы:
   - “Загрузить инженерные системы”
   - выбрать несколько опций чекбоксами
   - “Сохранить инженерные системы”
5) “Проверить конфигурацию”
   - ожидается `is_valid: true` и корректная `total_price`
6) “Отправить заявку”
   - конфигурация фиксируется (lock)
   - создаётся заказ (Order)
   - письма печатаются в консоль `runserver`

### 5.3 Проверка заказов
1) Открыть `/ui/orders/`
2) Убедиться, что новый заказ появился
3) Открыть заказ → посмотреть таблицы оборудования и инженерных систем
4) При наличии прав (manager/admin) можно сменить статус заказа

---

## 6) Что проверено руками (сквозной сценарий)

✅ UI работает кликами (без PowerShell):
- draft → выбрать категории → загрузить/сохранить модули → загрузить/сохранить инженерку → validate → submit
- после submit конфигурация блокируется
- создаётся Order со snapshot
- письма отправляются в console backend

---

## 7) API (ключевые эндпоинты)

JWT:
- POST `/api/token/`
- POST `/api/token/refresh/`

Configurator:
- GET/POST `/api/configurator/configurations/`
- GET `/api/configurator/configurations/{id}/`
- PATCH `/api/configurator/configurations/{id}/` (только draft)
- GET `/api/configurator/configurations/{id}/validate/`
- POST `/api/configurator/configurations/{id}/submit/`
- POST `/api/configurator/configurations/{id}/set_engineering/`
- GET `/api/configurator/configurations/main_categories/`
- GET `/api/configurator/configurations/sub_categories/?main_category_id=...`
- GET `/api/configurator/configurations/available_modules/?category_id=...`

Orders:
- GET `/api/orders/orders/`
- GET `/api/orders/orders/{id}/`
- GET `/api/orders/orders/{id}/history/`
- POST `/api/orders/orders/{id}/change_status/`

Catalog (engineering):
- GET `/api/catalog/engineering-system-options/`
- GET `/api/catalog/engineering-system-groups/`
(плюс legacy пути)

---

## 8) Тесты

Быстро:
```bash
pytest -q
```

С покрытием:
```bash
pytest --cov=. --cov-report=term-missing --cov-report=html
```

---

## 9) Кодстиль и проверки (black + isort)

Проект форматируется:
- `isort` с профилем `black`
- `black` (по умолчанию)

Форматирование:
```bash
python -m isort . --profile black
python -m black .
```

Проверка без изменений:
```bash
python -m isort . --profile black --check-only
python -m black . --check
```

Дополнительно (если используется в окружении):
```bash
python -m flake8
python -m mypy .
```

> Если на новой машине нет утилит: установи `black isort flake8 mypy pytest-cov` (или проверь, что они уже в `requirements.txt`).

---

## 10) Экспорт схемы OpenAPI (опционально)

```bash
python manage.py spectacular --file schema.yml
```

---

## 11) Структура проекта (укрупнённо)

Команды выполнять из `backend/` (там где `manage.py`).

```text
backend/
├── manage.py
├── config/
├── catalog/
├── configurator/
├── orders/
├── notifications/
├── ui/
│   └── templates/ui/
│       ├── base.html
│       ├── login.html
│       ├── customer.html
│       ├── orders.html
│       └── order_detail.html
├── static/ui/
│   ├── app.css
│   └── app.js
├── tests/
└── fixtures/demo_catalog.json
```

Примечание:
- В проекте может встречаться папка `backend/backend/users/...` (legacy/дубль).
  Чтобы проверить, какой пакет реально импортируется как `users`, можно выполнить:
  ```bash
  python -c "import users; print(users.__file__)"
  ```

---

## 12) Примечания

- Email отправляется в консоль `runserver` (console backend).
- После submit конфигурация фиксируется, изменение модулей/инженерки запрещено.
- UI переведён на русский для понятности заказчику.
- Символические цены инженерных опций можно править в админке или через shell.

Опционально (Windows): чтобы уменьшить предупреждения LF/CRLF при `git add`:
```bash
git config --global core.autocrlf input
git config --global core.safecrlf warn
```
