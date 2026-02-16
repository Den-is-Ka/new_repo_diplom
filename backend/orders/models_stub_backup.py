from django.db import models

class Order(models.Model):
    class Meta:
        db_table = 'orders_order'
        managed = False
