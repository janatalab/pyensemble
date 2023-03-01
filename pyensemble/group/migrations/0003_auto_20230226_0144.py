# Generated by Django 3.2.17 on 2023-02-26 01:44

import django.core.serializers.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0002_groupsession_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupsession',
            name='exclude',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='groupsession',
            name='executed_postsession_callback',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='groupsession',
            name='expired',
            field=models.BooleanField(blank=True, default=False),
        ),
        migrations.AddField(
            model_name='groupsession',
            name='origin_sessid',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='groupsession',
            name='reporting_data',
            field=models.JSONField(default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder),
        ),
        migrations.AddField(
            model_name='groupsession',
            name='timezone',
            field=models.CharField(blank=True, max_length=64),
        ),
    ]