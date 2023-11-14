# Generated by Django 3.2.20 on 2023-11-14 20:35

from django.db import migrations, models
import pyensemble.group.models
import pyensemble.storage_backends


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0007_alter_groupsessionfile_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupsessionfile',
            name='file',
            field=models.FileField(max_length=512, storage=pyensemble.storage_backends.S3DataStorage, upload_to=pyensemble.group.models.groupsession_filepath),
        ),
    ]
