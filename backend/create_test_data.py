import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import EquipmentType, EquipmentModule, CompatibilityRule
from users.models import User

def create_test_data():
    print('Создание тестовых данных...')
    
    # Создаем типы оборудования
    types = [
        {'name': 'Процессоры', 'description': 'Центральные процессоры', 'order': 1},
        {'name': 'Видеокарты', 'description': 'Графические ускорители', 'order': 2},
        {'name': 'Оперативная память', 'description': 'Модули RAM', 'order': 3},
        {'name': 'Жесткие диски', 'description': 'Накопители', 'order': 4},
    ]
    
    created_types = []
    for type_data in types:
        obj, created = EquipmentType.objects.get_or_create(
            name=type_data['name'],
            defaults=type_data
        )
        created_types.append(obj)
        print(f'Тип оборудования: {obj.name}')
    
    # Создаем модули оборудования
    modules_data = [
        {
            'name': 'Intel Core i9-13900K',
            'description': '24-ядерный процессор',
            'equipment_type': created_types[0],
            'price_type': 'fixed',
            'price': 45000.00,
            'power_consumption': 125,
            'dimensions': '45x45mm',
            'weight': 0.05,
            'is_active': True,
            'is_default': True,
        },
        {
            'name': 'AMD Ryzen 9 7950X',
            'description': '16-ядерный процессор',
            'equipment_type': created_types[0],
            'price_type': 'fixed',
            'price': 42000.00,
            'power_consumption': 170,
            'dimensions': '45x45mm',
            'weight': 0.05,
            'is_active': True,
            'is_default': False,
        },
        {
            'name': 'NVIDIA RTX 4090',
            'description': 'Видеокарта 24GB',
            'equipment_type': created_types[1],
            'price_type': 'fixed',
            'price': 150000.00,
            'power_consumption': 450,
            'dimensions': '336x140mm',
            'weight': 2.1,
            'is_active': True,
            'is_default': True,
        },
        {
            'name': 'AMD RX 7900 XTX',
            'description': 'Видеокарта 24GB',
            'equipment_type': created_types[1],
            'price_type': 'fixed',
            'price': 95000.00,
            'power_consumption': 355,
            'dimensions': '287x125mm',
            'weight': 1.8,
            'is_active': True,
            'is_default': False,
        },
        {
            'name': 'DDR5 32GB',
            'description': 'Оперативная память 32GB',
            'equipment_type': created_types[2],
            'price_type': 'fixed',
            'price': 12000.00,
            'power_consumption': 5,
            'dimensions': '133x30mm',
            'weight': 0.03,
            'is_active': True,
            'is_default': True,
        },
        {
            'name': 'NVMe SSD 2TB',
            'description': 'Твердотельный накопитель',
            'equipment_type': created_types[3],
            'price_type': 'fixed',
            'price': 15000.00,
            'power_consumption': 7,
            'dimensions': '80x22mm',
            'weight': 0.01,
            'is_active': True,
            'is_default': True,
        },
    ]
    
    for module_data in modules_data:
        obj, created = EquipmentModule.objects.get_or_create(
            name=module_data['name'],
            equipment_type=module_data['equipment_type'],
            defaults=module_data
        )
        print(f'Модуль оборудования: {obj.name}')
    
    # Создаем правило совместимости
    rule, created = CompatibilityRule.objects.get_or_create(
        name='Максимум 1 процессор',
        defaults={
            'rule_type': 'max_quantity',
            'description': 'В системе может быть только один процессор',
            'max_quantity': 1,
            'is_active': True,
        }
    )
    
    if created:
        # Добавляем модули к правилу (только процессоры)
        processor_modules = EquipmentModule.objects.filter(equipment_type=created_types[0])
        rule.modules.set(processor_modules)
        print(f'Правило совместимости: {rule.name}')
    
    print('✅ Тестовые данные созданы успешно!')

if __name__ == '__main__':
    create_test_data()
