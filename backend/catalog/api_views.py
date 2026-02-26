from rest_framework.views import APIView
from rest_framework.response import Response
from catalog.models import EquipmentCategory


class EquipmentTypesView(APIView):
    def get(self, request):
        # Берём уникальные equipment_type из БД
        types = (
            EquipmentCategory.objects
            .exclude(equipment_type__isnull=True)
            .exclude(equipment_type__exact="")
            .values_list("equipment_type", flat=True)
            .distinct()
        )
        data = [{"code": t, "label": str(t)} for t in types]
        return Response(data)


try:
    from catalog.models import EngineeringSystem
except Exception:
    EngineeringSystem = None


class EngineeringSystemsView(APIView):
    def get(self, request):
        if EngineeringSystem is None:
            return Response([])

        qs = EngineeringSystem.objects.all().order_by("id")

        data = []
        for obj in qs:
            item = {"id": obj.id, "name": getattr(obj, "name", str(obj))}
            if hasattr(obj, "price"):
                item["price"] = str(obj.price)
            if hasattr(obj, "price_type"):
                item["price_type"] = obj.price_type
            data.append(item)

        return Response(data)
