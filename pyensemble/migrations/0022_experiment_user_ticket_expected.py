# Generated by Django 3.2.25 on 2024-12-03 01:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0021_auto_20241115_1748'),
    ]

    operations = [
        migrations.AddField(
            model_name='experiment',
            name='user_ticket_expected',
            field=models.BooleanField(default=False, help_text='User ticket expected for participation'),
        ),
    ]
