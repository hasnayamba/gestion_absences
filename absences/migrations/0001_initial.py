# Generated by Django 5.2.3 on 2025-06-22 21:56

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='JourFerie',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('nom', models.CharField(max_length=100, unique=True)),
                ('description', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='TypeAbsence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100, unique=True)),
                ('code', models.CharField(max_length=100, unique=True)),
                ('couleur', models.CharField(help_text='Code hexadécimal ex: #FF5733', max_length=7)),
                ('plafond_annuel', models.IntegerField(help_text='Nombre maximum de jours par an')),
            ],
        ),
        migrations.CreateModel(
            name='Utilisateur',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('matricule', models.CharField(editable=False, max_length=20, unique=True)),
                ('role', models.CharField(choices=[('admin', 'Administrateur'), ('drh', 'DRH'), ('directeur', 'Directeur Pays'), ('collaborateur', 'Collaborateur')], default='collaborateur', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('superieur', models.ForeignKey(blank=True, limit_choices_to={'role': 'chef de projet'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subordonnes', to=settings.AUTH_USER_MODEL)),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SoldeConge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('solde_total', models.IntegerField(default=0)),
                ('solde_restant', models.IntegerField(default=0)),
                ('utilisateur', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Absence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_debut', models.DateField()),
                ('date_fin', models.DateField(blank=True, null=True)),
                ('nombre_jours', models.IntegerField()),
                ('justificatif', models.FileField(blank=True, null=True, upload_to='justificatifs/')),
                ('statut', models.CharField(choices=[('en_attente', 'En attente'), ('valide', 'Validée'), ('refuse', 'Refusée')], default='en_attente', max_length=20)),
                ('commentaire_refus', models.TextField(blank=True, null=True)),
                ('date_soumission', models.DateTimeField(auto_now_add=True)),
                ('date_decision', models.DateTimeField(blank=True, null=True)),
                ('utilisateur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('type_absence', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='absences.typeabsence')),
            ],
        ),
    ]
