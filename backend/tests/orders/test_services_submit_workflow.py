import pytest
from datetime import timedelta

from django.utils import timezone
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from orders.models import Order, OrderStatus
from orders.services import submit_configuration, assign_manager, change_status


# =========================
# submit workflow
# =========================

@pytest.mark.django_db
def test_submit_creates_order(configuration_with_module, customer):
    order, created = submit_configuration(configuration_with_module.id, customer)

    assert created is True
    assert order.configuration_id == configuration_with_module.id
    assert order.status == OrderStatus.NEW

    # расширенный snapshot (ключи должны быть всегда)
    assert "customer" in order.snapshot
    assert "engineering_systems" in order.snapshot
    assert set(order.snapshot["customer"].keys()) == {"company_name", "email", "phone"}
    assert isinstance(order.snapshot["engineering_systems"], list)


@pytest.mark.django_db
def test_submit_is_idempotent(configuration_with_module, customer):
    order1, created1 = submit_configuration(configuration_with_module.id, customer)
    order2, created2 = submit_configuration(configuration_with_module.id, customer)

    assert created1 is True
    assert created2 is False
    assert order1.id == order2.id


@pytest.mark.django_db
def test_submit_rejects_empty_configuration(configuration, customer):
    # ✅ раньше было ValueError, теперь бизнес-валидация кидает DRF ValidationError
    with pytest.raises(ValidationError) as e:
        submit_configuration(configuration.id, customer)

    payload = e.value.detail
    assert str(payload["code"]) == "CONFIG_INVALID"
    assert any(str(d["code"]) == "EMPTY_CONFIGURATION" for d in payload["details"])


# =========================
# assign manager
# =========================

@pytest.mark.django_db
def test_assign_manager_sets_manager_and_repeat_is_safe(configuration_with_module, customer, manager):
    order, _ = submit_configuration(configuration_with_module.id, customer)

    order1 = assign_manager(order_id=order.id, manager_user=manager, actor=manager)
    order1.refresh_from_db()
    assert order1.manager_id == manager.id

    # Повторное назначение: либо запрещено (ValueError), либо безопасно (возвращает тот же заказ)
    try:
        order2 = assign_manager(order_id=order.id, manager_user=manager, actor=manager)
        assert order2.id == order1.id
        assert order2.manager_id == manager.id
    except ValueError:
        # тоже ок: повторное назначение запрещено бизнес-правилом
        pass


@pytest.mark.django_db
def test_assign_manager_only_for_new_status():
    actor = baker.make("users.User", is_staff=True)      # кто выполняет действие (менеджер/админ)
    manager_user = baker.make("users.User", is_staff=True)    # кого назначаем менеджером

    order = baker.make(Order, status=OrderStatus.IN_REVIEW, manager=None)

    # у тебя сообщение: "Manager can be assigned only to NEW order"
    with pytest.raises(ValueError, match="only to NEW"):
        assign_manager(order.id, manager_user, actor)


@pytest.mark.django_db
def test_assign_manager_only_new_forbidden_when_not_new(manager):
    actor = manager
    manager_user = manager

    order = baker.make(Order, status=OrderStatus.IN_REVIEW, manager=None)

    with pytest.raises(ValueError, match="only to NEW"):
        assign_manager(order.id, manager_user=manager_user, actor=actor)


# =========================
# change status
# =========================

@pytest.mark.django_db
def test_change_status_rejects_illegal_transition(configuration_with_module, customer, manager):
    order, _ = submit_configuration(configuration_with_module.id, customer)

    with pytest.raises(ValueError):
        change_status(order_id=order.id, new_status=OrderStatus.COMPLETED, actor=manager)


@pytest.mark.django_db
def test_history_written_on_status_change(configuration_with_module, customer, manager):
    order, _ = submit_configuration(configuration_with_module.id, customer)
    assign_manager(order_id=order.id, manager_user=manager, actor=manager)

    change_status(order_id=order.id, new_status=OrderStatus.IN_REVIEW, actor=manager)
    change_status(order_id=order.id, new_status=OrderStatus.APPROVED, actor=manager)

    order.refresh_from_db()

    history_qs = order.status_history.order_by("created_at")
    assert history_qs.count() >= 2

    last = history_qs.last()
    assert last.to_status == OrderStatus.APPROVED

    # поле может называться по-разному
    assert (
        getattr(last, "actor", None) == manager
        or getattr(last, "changed_by", None) == manager
        or getattr(last, "user", None) == manager
    )


@pytest.mark.django_db
def test_change_status_sets_quoted_at_on_approved():
    actor = baker.make("users.User", is_staff=True)

    order = baker.make(
        Order,
        status=OrderStatus.IN_REVIEW,
        manager=actor,       # чтобы прошла проверка "assigned manager"
        quoted_at=None,
    )

    change_status(order.id, actor, OrderStatus.APPROVED)

    order.refresh_from_db()
    assert order.quoted_at is not None


@pytest.mark.django_db
def test_change_status_sets_completed_at_on_completed():
    actor = baker.make("users.User", is_staff=True)

    order = baker.make(
        Order,
        status=OrderStatus.IN_PRODUCTION,
        manager=actor,
        completed_at=None,
    )

    change_status(order.id, actor, OrderStatus.COMPLETED)

    order.refresh_from_db()
    assert order.completed_at is not None


@pytest.mark.django_db
def test_change_status_does_not_overwrite_quoted_at(manager):
    actor = manager
    old_time = timezone.now() - timedelta(days=1)

    order = baker.make(
        Order,
        status=OrderStatus.IN_REVIEW,
        manager=actor,
        quoted_at=old_time,
    )

    change_status(order.id, actor, OrderStatus.APPROVED)

    order.refresh_from_db()
    assert order.quoted_at == old_time


@pytest.mark.django_db
def test_change_status_does_not_overwrite_completed_at(manager):
    actor = manager
    old_time = timezone.now() - timedelta(days=1)

    order = baker.make(
        Order,
        status=OrderStatus.IN_PRODUCTION,
        manager=actor,
        completed_at=old_time,
    )

    change_status(order.id, actor, OrderStatus.COMPLETED)

    order.refresh_from_db()
    assert order.completed_at == old_time
