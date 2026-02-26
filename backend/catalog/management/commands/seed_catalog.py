from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import (
    CompatibilityRule,
    ContainerConfiguration,
    EngineeringSystemGroup,
    EngineeringSystemOption,
    EquipmentCategory,
    EquipmentModule,
    EquipmentPhysicalType,
)


def _dec(x: str) -> Decimal:
    return Decimal(x)


def _uoc(model, lookup: Dict[str, Any], defaults: Dict[str, Any]):
    obj, _created = model.objects.update_or_create(**lookup, defaults=defaults)
    return obj


class Command(BaseCommand):
    help = "Seed catalog with demo data for diploma (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding catalog (demo data)..."))

        # -------------------------
        # 1) Physical types
        # -------------------------
        pt_dgu = _uoc(EquipmentPhysicalType, {"name": "ДГУ (генератор)"}, {})
        pt_comp = _uoc(EquipmentPhysicalType, {"name": "Компрессор"}, {})
        pt_common = _uoc(
            EquipmentPhysicalType, {"name": "Общее (контейнер/системы)"}, {}
        )

        # если есть is_active — включим
        for pt in (pt_dgu, pt_comp, pt_common):
            if hasattr(pt, "is_active"):
                pt.is_active = True
                pt.save(update_fields=["is_active"])

        self.stdout.write(self.style.SUCCESS("✅ EquipmentPhysicalType seeded"))

        # -------------------------
        # 2) Categories
        # -------------------------
        root = _uoc(
            EquipmentCategory,
            {"code": "ROOT"},
            {
                "name": "Оборудование",
                "parent": None,
                "equipment_type": "root",
                "description": "Корневая категория оборудования",
                "order": 0,
                "is_active": True,
            },
        )

        dgu = _uoc(
            EquipmentCategory,
            {"code": "DGU"},
            {
                "name": "ДГУ",
                "parent": root,
                "equipment_type": "dgu",
                "description": "Дизель-генераторные установки",
                "order": 10,
                "is_active": True,
            },
        )
        comp = _uoc(
            EquipmentCategory,
            {"code": "COMP"},
            {
                "name": "Компрессорная установка",
                "parent": root,
                "equipment_type": "compressor",
                "description": "Компрессорные установки",
                "order": 20,
                "is_active": True,
            },
        )

        # subcategories (codes <=10)
        dgu_50 = _uoc(
            EquipmentCategory,
            {"code": "DGU50"},
            {
                "name": "ДГУ до 50 кВт",
                "parent": dgu,
                "equipment_type": "dgu",
                "description": "Малые мощности",
                "order": 11,
                "is_active": True,
            },
        )
        dgu_200 = _uoc(
            EquipmentCategory,
            {"code": "DGU200"},
            {
                "name": "ДГУ 50–200 кВт",
                "parent": dgu,
                "equipment_type": "dgu",
                "description": "Средние мощности",
                "order": 12,
                "is_active": True,
            },
        )
        dgu_500 = _uoc(
            EquipmentCategory,
            {"code": "DGU500"},
            {
                "name": "ДГУ 200–500 кВт",
                "parent": dgu,
                "equipment_type": "dgu",
                "description": "Высокие мощности",
                "order": 13,
                "is_active": True,
            },
        )

        comp_10 = _uoc(
            EquipmentCategory,
            {"code": "C10"},
            {
                "name": "Компрессор до 10 бар",
                "parent": comp,
                "equipment_type": "compressor",
                "description": "Низкое давление",
                "order": 21,
                "is_active": True,
            },
        )
        comp_30 = _uoc(
            EquipmentCategory,
            {"code": "C30"},
            {
                "name": "Компрессор 10–30 бар",
                "parent": comp,
                "equipment_type": "compressor",
                "description": "Среднее давление",
                "order": 22,
                "is_active": True,
            },
        )
        comp_60 = _uoc(
            EquipmentCategory,
            {"code": "C60"},
            {
                "name": "Компрессор 30–60 бар",
                "parent": comp,
                "equipment_type": "compressor",
                "description": "Высокое давление",
                "order": 23,
                "is_active": True,
            },
        )

        self.stdout.write(self.style.SUCCESS("✅ EquipmentCategory seeded"))

        # ---------------------------------
        # 3) Engineering groups + options
        # ---------------------------------
        # code max_length=10 => держим короткие
        g_electric = _uoc(
            EngineeringSystemGroup,
            {"code": "EL"},
            {"title": "Электрика", "key": "electric", "order": 10, "is_active": True},
        )
        g_climate = _uoc(
            EngineeringSystemGroup,
            {"code": "CL"},
            {"title": "Климат", "key": "climate", "order": 20, "is_active": True},
        )
        g_security = _uoc(
            EngineeringSystemGroup,
            {"code": "SEC"},
            {
                "title": "Безопасность",
                "key": "security",
                "order": 30,
                "is_active": True,
            },
        )

        # applicability: оставляем "all" (если choices другие — кинет ValidationError, тогда поправим под твои choices)
        def _opt(group, code, title, price, order):
            return _uoc(
                EngineeringSystemOption,
                {"code": code},
                {
                    "group": group,
                    "title": title,
                    "price_type": "fixed",
                    "price": _dec(price),
                    "order": order,
                    "is_active": True,
                    "applicability": "all",
                },
            )

        _opt(g_electric, "EL1", "Щит распределительный", "95000.00", 10)
        _opt(g_electric, "EL2", "ИБП (UPS) 5 кВА", "130000.00", 20)
        _opt(g_electric, "EL3", "Кабельные вводы/лотки", "40000.00", 30)

        _opt(g_climate, "CL1", "Кондиционер промышленный", "220000.00", 10)
        _opt(g_climate, "CL2", "Обогреватели 2×3кВт", "65000.00", 20)
        _opt(g_climate, "CL3", "Вентиляция усиленная", "120000.00", 30)

        _opt(g_security, "S1", "Датчики дыма/температуры", "35000.00", 10)
        _opt(g_security, "S2", "Система контроля доступа", "125000.00", 20)
        _opt(g_security, "S3", "Система пожаротушения", "180000.00", 30)

        self.stdout.write(self.style.SUCCESS("✅ EngineeringSystemGroup/Option seeded"))

        # -------------------------
        # 4) Equipment modules
        # -------------------------
        # applicable_to: ставим безопасные значения: "all", "dgu", "compressor"
        def _mod(name, category, physical_type, applicable_to, price, is_default=False):
            return _uoc(
                EquipmentModule,
                {"name": name},
                {
                    "category": category,
                    "physical_type": physical_type,
                    "applicable_to": applicable_to,
                    "description": f"Демо-модуль: {name}",
                    "price_type": "fixed",
                    "price": _dec(price),
                    "is_active": True,
                    "is_default": is_default,
                },
            )

        # общие
        _mod("Шумоизоляция контейнера", dgu_50, pt_common, "all", "250000.00")
        _mod(
            "Освещение промышленное",
            dgu_50,
            pt_common,
            "all",
            "45000.00",
            is_default=True,
        )
        _mod("Охранная сигнализация", dgu_50, pt_common, "all", "60000.00")
        _mod("Транспортные салазки", dgu_50, pt_common, "all", "90000.00")

        # ДГУ
        _mod("Глушитель повышенный", dgu_200, pt_dgu, "dgu", "110000.00")
        _mod("Шкаф автоматики", dgu_200, pt_dgu, "dgu", "160000.00", is_default=True)
        _mod("Антивибрационные опоры", dgu_50, pt_dgu, "dgu", "70000.00")
        _mod("Топливный бак увеличенный", dgu_500, pt_dgu, "dgu", "190000.00")

        # Компрессор
        _mod(
            "Система маслоотделения",
            comp_10,
            pt_comp,
            "compressor",
            "175000.00",
            is_default=True,
        )
        _mod("Осушитель воздуха", comp_30, pt_comp, "compressor", "145000.00")
        _mod("Фильтр тонкой очистки", comp_10, pt_comp, "compressor", "65000.00")
        _mod("Ресивер 500л", comp_30, pt_comp, "compressor", "98000.00")

        self.stdout.write(self.style.SUCCESS("✅ EquipmentModule seeded"))

        # -------------------------
        # 5) Compatibility rules (minimal)
        # -------------------------
        # Набор “для диплома” — просто наличие правил в каталоге.
        # Поля неизвестны? Но модель есть. Заполним по полям, которые обычно есть: code/title/description/is_active/payload
        fields = {f.name for f in CompatibilityRule._meta.fields}

        def _rule(code, title, payload):
            lookup = (
                {"code": code}
                if "code" in fields
                else {"title": title} if "title" in fields else {"name": title}
            )
            defaults = {}
            if "title" in fields:
                defaults["title"] = title
            if "name" in fields:
                defaults["name"] = title
            if "description" in fields:
                defaults["description"] = title
            if "is_active" in fields:
                defaults["is_active"] = True
            if "payload" in fields:
                defaults["payload"] = payload
            if "rule" in fields:
                defaults["rule"] = payload
            if "data" in fields:
                defaults["data"] = payload
            _uoc(CompatibilityRule, lookup, defaults)

        _rule(
            "REQBLK",
            "Обязательные блоки: электрика + климат",
            {"type": "required_groups", "groups": ["electric", "climate"]},
        )
        _rule(
            "DGUONLY",
            "DGU-модули только для ДГУ",
            {"type": "module_applicable_to", "allowed": ["dgu"]},
        )
        _rule(
            "COMPONLY",
            "Компрессор-модули только для компрессора",
            {"type": "module_applicable_to", "allowed": ["compressor"]},
        )

        self.stdout.write(self.style.SUCCESS("✅ CompatibilityRule seeded (minimal)"))

        # -------------------------
        # 6) ContainerConfiguration (minimal)
        # -------------------------
        cc_fields = {f.name for f in ContainerConfiguration._meta.fields}

        def _cc(name, data):
            if "name" in cc_fields:
                lookup = {"name": name}
            elif "code" in cc_fields:
                lookup = {"code": name[:10].upper()}
            else:
                return

            defaults = {}
            if "title" in cc_fields:
                defaults["title"] = name
            if "name" in cc_fields:
                defaults["name"] = name
            if "is_active" in cc_fields:
                defaults["is_active"] = True
            if "config" in cc_fields:
                defaults["config"] = data
            if "data" in cc_fields:
                defaults["data"] = data
            if "payload" in cc_fields:
                defaults["payload"] = data
            if "specifications" in cc_fields:
                defaults["specifications"] = data

            _uoc(ContainerConfiguration, lookup, defaults)

        _cc(
            "Контейнер 20ft (стандарт)",
            {"size": "20ft", "insulation": "standard", "doors": 1},
        )
        _cc(
            "Контейнер 40ft (усиленный)",
            {"size": "40ft", "insulation": "high", "doors": 2},
        )

        self.stdout.write(
            self.style.SUCCESS("✅ ContainerConfiguration seeded (minimal)")
        )
        self.stdout.write(self.style.SUCCESS("🎉 Seed done. You can re-run safely."))
