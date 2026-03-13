from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_rename_equipmentmodule_equipment_type_to_category"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=r"""
DO $$
BEGIN
    -- =========================
    -- EquipmentCategory fixes
    -- =========================

    -- name varchar(100) -> varchar(200) (модель max_length=200)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='catalog_equipmentcategory' AND column_name='name'
    ) THEN
        -- безопасно расширяем
        ALTER TABLE public.catalog_equipmentcategory
            ALTER COLUMN name TYPE varchar(200);
    END IF;

    -- equipment_type под модель (max_length=20). Можно оставить varchar(100), но лучше привести.
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='catalog_equipmentcategory' AND column_name='equipment_type'
    ) THEN
        ALTER TABLE public.catalog_equipmentcategory
            ALTER COLUMN equipment_type TYPE varchar(20);
    END IF;

    -- description в модели blank=True, но null=False (TextField) => NOT NULL норм.
    -- order/is_active/code уже есть.

    -- =========================
    -- EquipmentModule fixes
    -- =========================

    -- applicable_to (choices, max_length=20)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='catalog_equipmentmodule' AND column_name='applicable_to'
    ) THEN
        ALTER TABLE public.catalog_equipmentmodule
            ADD COLUMN applicable_to varchar(20) NOT NULL DEFAULT 'BOTH';
    END IF;

    -- physical_type_id FK -> catalog_equipmentphysicaltype
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='catalog_equipmentmodule' AND column_name='physical_type_id'
    ) THEN
        ALTER TABLE public.catalog_equipmentmodule
            ADD COLUMN physical_type_id bigint NULL;
    END IF;

    -- specifications jsonb default {}
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='catalog_equipmentmodule' AND column_name='specifications'
    ) THEN
        ALTER TABLE public.catalog_equipmentmodule
            ADD COLUMN specifications jsonb NOT NULL DEFAULT '{}'::jsonb;
    END IF;

    -- is_active/is_default уже есть, но на всякий случай:
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='catalog_equipmentmodule' AND column_name='is_active'
    ) THEN
        ALTER TABLE public.catalog_equipmentmodule
            ALTER COLUMN is_active SET DEFAULT true;
        ALTER TABLE public.catalog_equipmentmodule
            ALTER COLUMN is_active SET NOT NULL;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='catalog_equipmentmodule' AND column_name='is_default'
    ) THEN
        ALTER TABLE public.catalog_equipmentmodule
            ALTER COLUMN is_default SET DEFAULT false;
        ALTER TABLE public.catalog_equipmentmodule
            ALTER COLUMN is_default SET NOT NULL;
    END IF;

    -- FK constraint на physical_type_id (создаём только если нет)
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'catalog_equipmentmodule_physical_type_id_fk'
    ) THEN
        -- создаём FK только если таблица physical types существует
        IF to_regclass('public.catalog_equipmentphysicaltype') IS NOT NULL THEN
            ALTER TABLE public.catalog_equipmentmodule
                ADD CONSTRAINT catalog_equipmentmodule_physical_type_id_fk
                FOREIGN KEY (physical_type_id)
                REFERENCES public.catalog_equipmentphysicaltype(id)
                DEFERRABLE INITIALLY DEFERRED;
        END IF;
    END IF;

    -- индекс под модель: (is_active, category_id, applicable_to)
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind='i' AND n.nspname='public' AND c.relname='catalog_equ_module_active_category_applicable_idx'
    ) THEN
        CREATE INDEX catalog_equ_module_active_category_applicable_idx
            ON public.catalog_equipmentmodule (is_active, category_id, applicable_to);
    END IF;
END $$;
""",
                    reverse_sql=r"""
-- обратный откат не делаем (это "починка" схемы)
""",
                )
            ],
            state_operations=[],
        )
    ]
