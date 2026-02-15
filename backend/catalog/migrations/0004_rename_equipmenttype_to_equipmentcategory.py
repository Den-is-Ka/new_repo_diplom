from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_engineeringsystemgroup_engineeringsystemoption"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF to_regclass('public.catalog_equipmenttype') IS NOT NULL
                   AND to_regclass('public.catalog_equipmentcategory') IS NULL THEN
                    ALTER TABLE public.catalog_equipmenttype
                        RENAME TO catalog_equipmentcategory;
                END IF;
            END$$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                IF to_regclass('public.catalog_equipmentcategory') IS NOT NULL
                   AND to_regclass('public.catalog_equipmenttype') IS NULL THEN
                    ALTER TABLE public.catalog_equipmentcategory
                        RENAME TO catalog_equipmenttype;
                END IF;
            END$$;
            """,
        ),
    ]
