# Generated by Django 3.2.17 on 2023-04-13 03:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0010_alter_session_timezone'),
        ('group', '0004_alter_groupsession_timezone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupsessionsubjectsession',
            name='state',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Unknown'), (1, 'Ready Server'), (2, 'Ready Client'), (3, 'Busy'), (4, 'Response Pending'), (5, 'Exit Loop')], default=0),
        ),
        migrations.AlterField(
            model_name='groupsessionsubjectsession',
            name='user_session',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='pyensemble.session'),
        ),
    ]
