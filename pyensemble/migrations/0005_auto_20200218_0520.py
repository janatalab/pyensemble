# Generated by Django 2.2.7 on 2020-02-18 05:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0004_auto_20200218_0519'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stimulus',
            name='height',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='stimulus',
            name='width',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
