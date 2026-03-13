import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    # ВАЖНО: заставляем идти ПОСЛЕ 0005_fix (там уже создаётся parent_id в БД)
    dependencies = [
        ("catalog", "0005_fix_equipmentcategory_columns"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # На уровне БД: добавляем колонку ТОЛЬКО если её нет
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_name = 'catalog_equipmentcategory'
                              AND column_name = 'parent_id'
                        ) THEN
                            ALTER TABLE catalog_equipmentcategory
                            ADD COLUMN parent_id integer NULL;
                        END IF;
                    END$$;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            # На уровне состояния Django: добавляем поле parent (чтобы state совпал с model)
            state_operations=[
                migrations.AddField(
                    model_name="equipmentcategory",
                    name="parent",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="catalog.equipmentcategory",
                    ),
                )
            ],
        )
    ]
