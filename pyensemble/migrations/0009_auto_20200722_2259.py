# Generated by Django 2.2.7 on 2020-07-22 22:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0008_auto_20200620_0111'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experimentxform',
            name='form_handler',
            field=models.CharField(blank=True, choices=[('form_generic', 'form_generic'), ('form_stimulus_s', 'form_stimulus_s'), ('form_generic_s', 'form_generic_s'), ('form_image_s', 'form_image_s'), ('form_feedback', 'form_feedback'), ('form_end_session', 'form_end_session'), ('form_consent', 'form_consent'), ('form_subject_register', 'form_subject_register'), ('form_subject_email', 'form_subject_email')], default='form_generic', max_length=50),
        ),
    ]