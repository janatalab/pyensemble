# Generated by Django 3.2.17 on 2023-07-14 16:33

from django.db import migrations, models
import pyensemble.models


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0016_sessionfile_sessionfileattribute'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sessionfile',
            name='file',
            field=models.FileField(max_length=512, upload_to=pyensemble.models.session_filepath),
        ),
    ]
