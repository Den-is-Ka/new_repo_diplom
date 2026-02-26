from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Configuration
from .serializers import (
    ConfigurationCreateSerializer,
    ConfigurationSerializer,
    ConfigurationValidateSerializer,
)


class ConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet для управления конфигурациями"""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Пользователь видит только свои конфигурации
        return Configuration.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ConfigurationCreateSerializer
        return ConfigurationSerializer

    def perform_create(self, serializer):
        # Автоматически назначаем пользователя
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get"])
    def validate(self, request, pk=None):
        """Валидация конкретной конфигурации"""
        configuration = self.get_object()

        # Проверяем совместимость
        errors = configuration.check_compatibility()
        total_price = configuration.calculate_total_price()

        serializer = ConfigurationValidateSerializer(
            {"is_valid": len(errors) == 0, "errors": errors, "total_price": total_price}
        )

        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def recalculate(self, request, pk=None):
        """Пересчет стоимости конфигурации"""
        configuration = self.get_object()
        configuration.save()  # Вызовет пересчет и проверку

        return Response(
            {
                "total_price": configuration.total_price,
                "status": configuration.status,
                "errors": configuration.compatibility_errors,
            }
        )

    @action(detail=False, methods=["get"])
    def my_configurations(self, request):
        """Получить все конфигурации текущего пользователя"""
        configurations = self.get_queryset()
        serializer = self.get_serializer(configurations, many=True)
        return Response(serializer.data)
