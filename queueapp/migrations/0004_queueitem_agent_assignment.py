from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('queueapp', '0003_agent'),
    ]

    operations = [
        migrations.AddField(
            model_name='queueitem',
            name='served_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='queueitem',
            name='assigned_agent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_tickets', to='queueapp.agent'),
        ),
    ]
