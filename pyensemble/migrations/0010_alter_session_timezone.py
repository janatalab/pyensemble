# Generated by Django 3.2.17 on 2023-03-08 20:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0009_notification_ticket'),
    ]

    operations = [
        migrations.AlterField(
            model_name='session',
            name='timezone',
            field=models.CharField(blank=True, default='UTC', max_length=64),
        ),
    ]