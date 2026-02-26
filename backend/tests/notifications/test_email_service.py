import pytest
from decimal import Decimal

from django.core import mail
from django.contrib.auth import get_user_model

from orders.models import Order
from configurator.models import Configuration
from catalog.models import EquipmentCategory

from notifications.email_service import send_order_created_emails

User = get_user_model()


@pytest.mark.django_db
def test_email_service_sends_two_emails(settings):
    # locmem backend чтобы письма попадали в mail.outbox
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "no-reply@diplom.local"
    settings.EMAIL_SUBJECT_PREFIX = "[Diplom] "
    settings.MANUFACTURER_NOTIFY_EMAIL = "manufacturer@diplom.local"

    # ВАЖНО: company_name обязателен по User.save()
    u = User.objects.create_user(
        username="email_user",
        password="pass123",
        email="customer@example.com",
        company_name="ООО Email Тест",
    )

    # минимальная конфигурация (Order требует FK на config)
    root = EquipmentCategory.objects.create(
        name="Оборудование",
        parent=None,
        equipment_type="root",
        description="root",
        order=0,
        is_active=True,
        code="ROOT-EMAIL",
    )
    main = EquipmentCategory.objects.create(
        name="ДГУ",
        parent=root,
        equipment_type="DGU",
        description="main",
        order=1,
        is_active=True,
        code="DGU-EMAIL",
    )
    sub = EquipmentCategory.objects.create(
        name="до 50 кВт",
        parent=main,
        equipment_type="DGU",
        description="sub",
        order=1,
        is_active=True,
        code="DGU-50-EMAIL",
    )

    cfg = Configuration.objects.create(
        user=u,
        name="cfg",
        status=Configuration.Status.SUBMITTED,
        main_category=main,
        sub_category=sub,
        total_price=Decimal("123.00"),
    )

    order = Order.objects.create(
        configuration=cfg,
        user=u,
        order_number="ORD-TEST-0001",
        status="NEW",
        total_price=Decimal("123.00"),
        snapshot={
            "customer": {"email": "customer@example.com"},
            "modules": [],
            "engineering_systems": [],
        },
    )

    mail.outbox.clear()
    send_order_created_emails(order)

    assert len(mail.outbox) == 2
    subjects = [m.subject for m in mail.outbox]
    assert any("ORD-TEST-0001" in s for s in subjects)

    tos = [tuple(m.to) for m in mail.outbox]
    assert ("customer@example.com",) in tos
    assert ("manufacturer@diplom.local",) in tos
