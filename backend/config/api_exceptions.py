from __future__ import annotations

from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def _normalize_django_validation_error(exc: DjangoValidationError) -> Dict[str, Any]:
    """
    Приводим django.core.exceptions.ValidationError к удобному JSON:
    - если exc.message_dict -> вернем словарь как есть
    - если exc.messages -> {"detail": [...]} или {"detail": "..."}
    - если exc имеет code -> можно добавить при желании
    """
    if hasattr(exc, "message_dict") and exc.message_dict:
        # пример: {"detail": ["..."], "fields": ["..."]}
        return exc.message_dict

    messages = getattr(exc, "messages", None)
    if messages:
        if len(messages) == 1:
            return {"detail": messages[0]}
        return {"detail": messages}

    # fallback
    return {"detail": str(exc)}


def custom_exception_handler(exc: Exception, context: Optional[dict] = None) -> Response:
    """
    1) Сначала даём DRF обработать стандартные исключения
    2) Если DRF не обработал и это DjangoValidationError — возвращаем 400 JSON
    """
    response = exception_handler(exc, context)

    if response is not None:
        return response

    if isinstance(exc, DjangoValidationError):
        data = _normalize_django_validation_error(exc)
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    # если не знаем что это — пусть будет 500
    return Response(
        {"detail": "Internal server error."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
