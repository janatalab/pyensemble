# Generated by Django 2.2.7 on 2020-06-20 01:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0007_experimentxform_continue_button_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='response',
            name='jspsych_data',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='experimentxform',
            name='continue_button_text',
            field=models.CharField(blank=True, default='Next', max_length=50),
        ),
    ]