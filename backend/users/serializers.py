from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

# Используем get_user_model() для поддержки кастомных моделей пользователя
UserModel = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']
