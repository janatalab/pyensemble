# Generated by Django 3.2.20 on 2023-11-15 03:03

from django.db import migrations, models
from django.conf import settings
import pyensemble.models

def use_storage():
    if settings.USE_AWS_STORAGE:
        from pyensemble.storage_backends import S3DataStorage
        storage = S3DataStorage

    else:
        from django.core.files.storage import FileSystemStorage
        storage = FileSystemStorage

    return storage

class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0018_auto_20231114_2035'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experimentfile',
            name='file',
            field=models.FileField(max_length=512, storage=use_storage(), upload_to=pyensemble.models.experiment_filepath),
        ),
        migrations.AlterField(
            model_name='sessionfile',
            name='file',
            field=models.FileField(max_length=512, storage=use_storage(), upload_to=pyensemble.models.session_filepath),
        ),
    ]