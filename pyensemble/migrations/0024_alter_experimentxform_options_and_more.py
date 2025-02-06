# Generated by Django 4.2.17 on 2025-02-06 05:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pyensemble', '0023_subject_allowed_emailverification'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='experimentxform',
            options={'ordering': ['form_order']},
        ),
        migrations.AlterField(
            model_name='experimentxform',
            name='form_handler',
            field=models.CharField(blank=True, choices=[('form_generic', 'form_generic'), ('form_stimulus_s', 'form_stimulus_s'), ('form_generic_s', 'form_generic_s'), ('form_image_s', 'form_image_s'), ('form_feedback', 'form_feedback'), ('form_end_session', 'form_end_session'), ('form_consent', 'form_consent'), ('form_subject_register', 'form_subject_register'), ('form_login_w_email', 'form_login_w_email'), ('form_subject_email', 'form_subject_email'), ('group_trial', 'group_trial')], default='form_generic', max_length=50),
        ),
    ]
