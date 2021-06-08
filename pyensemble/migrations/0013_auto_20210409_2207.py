# Generated by Django 3.1.6 on 2021-04-09 22:07

# For some reason the statements in populate_hash had to be run from a shell and did not run as part of the migration set.

from django.db import migrations

def populate_hash(apps, schema_editor):
    StimulusXAttribute = apps.get_model('pyensemble', 'StimulusXAttribute')
    for obj in StimulusXAttribute.objects.all():
        obj.save()

    AttributeXAttribute = apps.get_model('pyensemble', 'AttributeXAttribute')
    for obj in AttributeXAttribute.objects.all():
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0012_auto_20210409_2205'),
    ]

    operations = [
        migrations.RunPython(populate_hash),
    ]