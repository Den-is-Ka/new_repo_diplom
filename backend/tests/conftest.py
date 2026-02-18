import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker

User = get_user_model()


@pytest.fixture
def customer(db):
    return User.objects.create_user(
        username="customer",
        password="pass12345",
        company_name="ООО Тест Клиент",
        email="customer@test.local",
        phone="+79990000001",
    )


@pytest.fixture
def manager(db):
    return User.objects.create_user(
        username="manager",
        password="pass12345",
        is_staff=True,
        company_name="ООО Тест Менеджер",
        email="manager@test.local",
        phone="+79990000002",
    )

@pytest.fixture
def equipment_module(db):
    # если у модели другое имя — поправим после проверки
    return baker.make("catalog.EquipmentModule", price=1000)


@pytest.fixture
def configuration(db, customer):
    return baker.make("configurator.Configuration", user=customer)


@pytest.fixture
def configuration_with_module(db, configuration, equipment_module):
    baker.make(
        "configurator.ConfigurationModule",
        configuration=configuration,
        module=equipment_module,
        quantity=1,
    )
    return configuration
