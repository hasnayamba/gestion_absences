# Generated by Django 5.2.3 on 2025-06-22 22:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('absences', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilisateur',
            name='mot_de_passe_change',
            field=models.BooleanField(default=False),
        ),
    ]
