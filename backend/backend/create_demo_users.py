import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Список тестовых пользователей по Т
demo_users = [
    {
        "username": "client_dgu",
        "email": "dgu_client@industrial.com",
        "password": "client123",
        "company_name": " \"ромышленные ешения\"",
        "phone": "+79161234567",
        "first_name": "лексей",
        "last_name": "ванов"
    },
    {
        "username": "client_compressor",
        "email": "compressor_client@factory.ru",
        "password": "client123",
        "company_name": "авод \"еталлург\"",
        "phone": "+79031234567",
        "first_name": "ария",
        "last_name": "етрова"
    },
    {
        "username": "manager1",
        "email": "manager@container-company.com",
        "password": "manager123",
        "company_name": "онтейнерСтрой",
        "phone": "+79501234567",
        "first_name": "Сергей",
        "last_name": "Сидоров",
        "is_manager": True,
        "is_customer": False
    }
]

created_count = 0

for user_data in demo_users:
    try:
        # роверяем, существует ли пользователь
        if not User.objects.filter(email=user_data["email"]).exists():
            user = User.objects.create_user(
                username=user_data["username"],
                email=user_data["email"],
                password=user_data["password"],
                company_name=user_data["company_name"],
                phone=user_data["phone"],
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name", "")
            )
            
            # ополнительные флаги
            user.email_confirmed = True  # одтверждаем email для теста
            user.is_manager = user_data.get("is_manager", False)
            user.is_customer = user_data.get("is_customer", True)
            user.save()
            
            created_count += 1
            print(f"✅ Создан: {user.username} ({user.company_name})")
        else:
            print(f"⚠️ же существует: {user_data['email']}")
            
    except Exception as e:
        print(f"❌ шибка при создании {user_data['username']}: {e}")

print(f"\nСоздано {created_count} новых пользователей")
print("\nанные для входа:")
print("-----------------")
print("лиент :")
print("  огин: client_dgu")
print("  ароль: client123")
print("  Email: dgu_client@industrial.com")
print("\nлиент омпрессор:")
print("  огин: client_compressor")
print("  ароль: client123")
print("  Email: compressor_client@factory.ru")
print("\nенеджер:")
print("  огин: manager1")
print("  ароль: manager123")
print("  Email: manager@container-company.com")
