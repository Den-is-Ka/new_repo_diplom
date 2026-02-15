from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_rename_equipmenttype_to_equipmentcategory"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE catalog_equipmentcategory
                ADD COLUMN IF NOT EXISTS equipment_type varchar(100);

            ALTER TABLE catalog_equipmentcategory
                ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true;

            ALTER TABLE catalog_equipmentcategory
                ADD COLUMN IF NOT EXISTS code varchar(50);

            -- старое поле могло остаться от старой модели
            ALTER TABLE catalog_equipmentcategory
                DROP COLUMN IF EXISTS image;
            """,
            reverse_sql="""
            ALTER TABLE catalog_equipmentcategory
                DROP COLUMN IF EXISTS equipment_type;

            ALTER TABLE catalog_equipmentcategory
                DROP COLUMN IF EXISTS is_active;

            ALTER TABLE catalog_equipmentcategory
                DROP COLUMN IF EXISTS code;

            -- image обратно не возвращаем (не нужно)
            """,
        )
    ]
