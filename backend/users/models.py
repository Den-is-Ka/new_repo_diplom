from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    '''астомная модель пользователя'''
    
    # обавляем related_name чтобы избежать конфликтов
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',  # никальный related_name
        related_query_name='user',
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',  # никальный related_name
        related_query_name='user',
    )
    
    # ожно добавить дополнительные поля
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Телефон')
    
    class Meta:
        verbose_name = 'ользователь'
        verbose_name_plural = 'ользователи'
        
    def __str__(self):
        return self.email or self.username
