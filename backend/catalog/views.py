from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import EngineeringSystemGroup, EngineeringSystemOption
from .serializers import EngineeringSystemGroupSerializer, EngineeringSystemOptionSerializer


class EngineeringSystemGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    /api/catalog/engineering-system-groups/
    - список групп (2.1–2.9)
    - сортировка по order
    - фильтр is_active через query param
    """
    serializer_class = EngineeringSystemGroupSerializer

    def get_queryset(self):
        qs = EngineeringSystemGroup.objects.all().order_by("order", "code")
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            val = is_active.lower()
            if val in ("1", "true", "yes"):
                qs = qs.filter(is_active=True)
            elif val in ("0", "false", "no"):
                qs = qs.filter(is_active=False)
        return qs

    @action(detail=True, methods=["get"], url_path="options")
    def options(self, request, pk=None):
        """
        /api/catalog/engineering-system-groups/<id>/options/
        - опции по группе
        - сортировка по order
        - фильтр is_active через query param
        """
        group = self.get_object()
        qs = EngineeringSystemOption.objects.filter(group=group).order_by("order", "code")

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            val = is_active.lower()
            if val in ("1", "true", "yes"):
                qs = qs.filter(is_active=True)
            elif val in ("0", "false", "no"):
                qs = qs.filter(is_active=False)

        serializer = EngineeringSystemOptionSerializer(qs, many=True)
        return Response(serializer.data)
