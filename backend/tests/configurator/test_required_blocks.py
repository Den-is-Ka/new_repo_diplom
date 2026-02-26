import pytest
from rest_framework.exceptions import ValidationError

from configurator.services import validate_configuration_for_submit


@pytest.mark.django_db
def test_required_blocks_rejects_when_missing(settings, configuration_with_module):
    # Требуем несуществующий код — гарантированно отсутствует
    settings.CONFIG_REQUIRED_CATEGORY_CODES = ["__MUST_NOT_EXIST__"]
    settings.CONFIG_REQUIRED_MODULE_CODES = []

    with pytest.raises(ValidationError) as e:
        validate_configuration_for_submit(configuration_with_module)

    payload = e.value.detail
    assert str(payload["code"]) == "CONFIG_INVALID"
    assert any(str(d["code"]) == "MISSING_REQUIRED_BLOCKS" for d in payload["details"])


@pytest.mark.django_db
def test_required_blocks_passes_when_requirements_empty(
    settings, configuration_with_module
):
    # Когда списки пустые — правило выключено и валидация не падает
    settings.CONFIG_REQUIRED_CATEGORY_CODES = []
    settings.CONFIG_REQUIRED_MODULE_CODES = []

    validate_configuration_for_submit(
        configuration_with_module
    )  # не должно кидать исключение
