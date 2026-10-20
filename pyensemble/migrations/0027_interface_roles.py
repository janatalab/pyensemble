from django.db import migrations


def create_roles(apps, schema_editor):
    group = apps.get_model('auth', 'Group')
    for name in ('Editor', 'Release manager', 'Account administrator'):
        group.objects.using(schema_editor.connection.alias).get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('pyensemble', '0026_response_form_served'),
    ]

    operations = [
        migrations.RunPython(create_roles, migrations.RunPython.noop),
    ]
