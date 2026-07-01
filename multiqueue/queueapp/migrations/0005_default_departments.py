from django.db import migrations


DEFAULT_DEPARTMENTS = [
    ('Guichet Aéroport', 'GUICHET_AEROPORT', 250),
    ('Guichet Soa Trans', 'GUICHET_SOA_TRANS', 180),
    ('Manitra Plus', 'MANITRA_PLUS', 160),
    ('BNI Madagascar', 'BNI_MADAGASCAR', 200),
    ('BFV', 'BFV', 200),
    ('Micro-finance', 'MICRO_FINANCE', 150),
    ('Institut Pasteur', 'INSTITUT_PASTEUR', 160),
    ('CHU', 'CHU', 220),
    ('Administratif', 'ADMINISTRATIF', 120),
]


def create_departments(apps, schema_editor):
    Queue = apps.get_model('queueapp', 'Queue')
    Agent = apps.get_model('queueapp', 'Agent')

    for name, service_type, capacity in DEFAULT_DEPARTMENTS:
        queue, _ = Queue.objects.get_or_create(
            name=name,
            defaults={
                'service_type': service_type,
                'max_capacity': capacity,
                'is_active': True,
            },
        )
        if not queue.service_type:
            queue.service_type = service_type
            queue.save(update_fields=['service_type'])

        for number in range(1, 4):
            Agent.objects.get_or_create(
                queue=queue,
                agent_number=number,
                defaults={
                    'name': f'Agent {name} {number}',
                    'status': 'available',
                    'is_active': True,
                },
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('queueapp', '0004_queueitem_agent_assignment'),
    ]

    operations = [
        migrations.RunPython(create_departments, noop_reverse),
    ]
