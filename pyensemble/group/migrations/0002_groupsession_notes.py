# Generated by Django 3.1.14 on 2023-01-24 00:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupsession',
            name='notes',
            field=models.TextField(blank=True),
        ),
    ]
