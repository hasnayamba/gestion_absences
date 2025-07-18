# Generated by Django 5.2.3 on 2025-07-01 16:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('absences', '0005_alter_mois_options_alter_mois_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='absence',
            name='statut',
            field=models.CharField(choices=[('en_attente', 'En attente'), ('approuve_superieur', 'Approuvé par supérieur'), ('valide', 'Validée par DRH'), ('refuse', 'Refusée')], default='en_attente', max_length=20),
        ),
    ]
