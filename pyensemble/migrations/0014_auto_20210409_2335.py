# Generated by Django 3.1.6 on 2021-04-09 23:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0013_auto_20210409_2207'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attributexattribute',
            name='unique_hash',
            field=models.CharField(max_length=32, unique=True),
        ),
        migrations.AlterField(
            model_name='stimulusxattribute',
            name='unique_hash',
            field=models.CharField(max_length=32, unique=True),
        ),
    ]