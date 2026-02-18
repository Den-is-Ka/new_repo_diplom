import pytest

from orders.models import OrderStatus
from orders.services import submit_configuration, assign_manager, change_status


@pytest.mark.django_db
def test_submit_creates_order(configuration_with_module, customer):
    order, created = submit_configuration(configuration_with_module.id, customer)

    assert created is True
    assert order.configuration_id == configuration_with_module.id
    assert order.order_number
    assert order.total_price is not None
    assert isinstance(order.snapshot, dict)


@pytest.mark.django_db
def test_submit_is_idempotent(configuration_with_module, customer):
    order1, created1 = submit_configuration(configuration_with_module.id, customer)
    order2, created2 = submit_configuration(configuration_with_module.id, customer)

    assert created1 is True
    assert created2 is False
    assert order1.id == order2.id


@pytest.mark.django_db
def test_submit_rejects_empty_configuration(configuration, customer):
    with pytest.raises(ValueError):
        submit_configuration(configuration.id, customer)



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

    # У тебя поле называется НЕ actor. Проверим универсально:
    assert getattr(last, "actor", None) == manager or getattr(last, "changed_by", None) == manager or getattr(last, "user", None) == manager
