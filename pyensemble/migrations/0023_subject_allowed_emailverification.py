# Generated by Django 4.2.17 on 2024-12-31 19:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0022_experiment_user_ticket_expected'),
    ]

    operations = [
        migrations.AddField(
            model_name='subject',
            name='allowed',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='EmailVerification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=100, unique=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('subject', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='pyensemble.subject')),
            ],
        ),
    ]
