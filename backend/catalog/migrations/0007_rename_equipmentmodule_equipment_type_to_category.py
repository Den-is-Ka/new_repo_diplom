from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_merge_20260214_2247"),
    ]

    operations = [
        migrations.RunSQL(
            sql=r"""
DO $$
BEGIN
    -- 1) Переименуем колонку equipment_type_id -> category_id
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name='catalog_equipmentmodule'
          AND column_name='equipment_type_id'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name='catalog_equipmentmodule'
          AND column_name='category_id'
    ) THEN
        ALTER TABLE public.catalog_equipmentmodule
            RENAME COLUMN equipment_type_id TO category_id;
    END IF;

    -- 2) Переименуем индекс (если существует)
    IF EXISTS (
        SELECT 1 FROM pg_class
        WHERE relkind='i' AND relname='catalog_equipmentmodule_equipment_type_id_fe4266e8'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relkind='i' AND relname='catalog_equipmentmodule_category_id_fe4266e8'
    ) THEN
        ALTER INDEX public.catalog_equipmentmodule_equipment_type_id_fe4266e8
            RENAME TO catalog_equipmentmodule_category_id_fe4266e8;
    END IF;

    -- 3) Переименуем constraint FK (если существует)
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname='catalog_equipmentmod_equipment_type_id_fe4266e8_fk_catalog_e'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname='catalog_equipmentmod_category_id_fe4266e8_fk_catalog_e'
    ) THEN
        ALTER TABLE public.catalog_equipmentmodule
            RENAME CONSTRAINT catalog_equipmentmod_equipment_type_id_fe4266e8_fk_catalog_e
            TO catalog_equipmentmod_category_id_fe4266e8_fk_catalog_e;
    END IF;

    -- 4) Переименуем составной индекс (если существует)
    IF EXISTS (
        SELECT 1 FROM pg_class
        WHERE relkind='i' AND relname='catalog_equ_is_acti_b4027e_idx'
    ) THEN
        -- его можно оставить как есть (имя не критично), но если хочешь красиво:
        -- ничего не делаем, чтобы не ловить конфликты по имени в будущем
        NULL;
    END IF;
END $$;
""",
            reverse_sql=r"""
DO $$
BEGIN
    -- reverse: category_id -> equipment_type_id (если нужно откатить)
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name='catalog_equipmentmodule'
          AND column_name='category_id'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name='catalog_equipmentmodule'
          AND column_name='equipment_type_id'
    ) THEN
        ALTER TABLE public.catalog_equipmentmodule
            RENAME COLUMN category_id TO equipment_type_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_class
        WHERE relkind='i' AND relname='catalog_equipmentmodule_category_id_fe4266e8'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relkind='i' AND relname='catalog_equipmentmodule_equipment_type_id_fe4266e8'
    ) THEN
        ALTER INDEX public.catalog_equipmentmodule_category_id_fe4266e8
            RENAME TO catalog_equipmentmodule_equipment_type_id_fe4266e8;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname='catalog_equipmentmod_category_id_fe4266e8_fk_catalog_e'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname='catalog_equipmentmod_equipment_type_id_fe4266e8_fk_catalog_e'
    ) THEN
        ALTER TABLE public.catalog_equipmentmodule
            RENAME CONSTRAINT catalog_equipmentmod_category_id_fe4266e8_fk_catalog_e
            TO catalog_equipmentmod_equipment_type_id_fe4266e8_fk_catalog_e;
    END IF;
END $$;
""",
        ),
    ]
