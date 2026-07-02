# Generated to align Queue.service_type choices with the current multi-department model.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('queueapp', '0005_default_departments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='queue',
            name='service_type',
            field=models.CharField(
                choices=[
                    ('GUICHET_AEROPORT', 'Guichet Aéroport'),
                    ('GUICHET_SOA_TRANS', 'Guichet Soa Trans'),
                    ('MANITRA_PLUS', 'Manitra Plus'),
                    ('BNI_MADAGASCAR', 'BNI Madagascar'),
                    ('BFV', 'BFV'),
                    ('MICRO_FINANCE', 'Micro-finance'),
                    ('INSTITUT_PASTEUR', 'Institut Pasteur'),
                    ('CHU', 'CHU'),
                    ('ADMINISTRATIF', 'Administratif'),
                    ('SERVICE_CLIENT_MULTICANAL', 'Service client multicanal'),
                    ('GUICHET_ADMINISTRATIF', 'Guichet administratif'),
                    ('SUPPORT_TECHNIQUE', 'Support technique (ticketing)'),
                    ('DRIVE_RESTAURANT', 'Drive de restaurant'),
                    ('HOPITAL_URGENCES', 'Hôpital – Urgences'),
                    ('CENTRE_VACCINATION', 'Centre de vaccination'),
                ],
                default='GUICHET_AEROPORT',
                max_length=50,
                verbose_name='Département / type de guichet',
            ),
        ),
    ]
