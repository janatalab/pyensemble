# Generated by Django 2.2.7 on 2020-04-24 02:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0002_auto_20200417_0211'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attributexattribute',
            name='child',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='children', to='pyensemble.Attribute'),
        ),
        migrations.AlterField(
            model_name='attributexattribute',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parents', to='pyensemble.Attribute'),
        ),
    ]
