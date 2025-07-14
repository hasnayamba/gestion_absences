from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db.models import Sum

# -------------------------
# GESTIONNAIRE UTILISATEUR
# -------------------------
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _


# -------------------------
# GESTIONNAIRE UTILISATEUR
# -------------------------
class UtilisateurManager(BaseUserManager):
    def create_user(self,username, email, password='1234', role='collaborateur', **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire")
        if not username:
            raise ValueError("Le nom d'utilisateur est obligatoire")
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password='admin', **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username,email, password, role='admin', **extra_fields)

# -------------------------
# UTILISATEUR PERSONNALISÉ
# -------------------------
class Utilisateur(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('drh', 'DRH'),
        ('directeur', 'Directeur Pays'),
        ('collaborateur', 'Collaborateur'),
        ('ca', 'Chef Antenne'),
        ('cp', 'Chef Projet'),
    ]
    username = models.CharField(max_length=150, null=True, default='tempuser', unique=True, verbose_name=_("Nom d'utilisateur"))
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    matricule = models.CharField(max_length=20, unique=True, editable=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='collaborateur')
    mot_de_passe_change = models.BooleanField(default=False)

    superieur = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subordonnes',
        limit_choices_to={'role': 'chef de projet'}
    )

    solde_initial = models.IntegerField(default=0, help_text="Solde de congé initial (sera utilisé à la création uniquement)", blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UtilisateurManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    def save(self, *args, **kwargs):
        if not self.matricule:
            dernier_id = Utilisateur.objects.count() + 1
            self.matricule = f"NY25-{dernier_id:02d}"

        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Création du solde de congé une seule fois à la création
        if is_new:
            from .models import SoldeConge
            SoldeConge.objects.create(
                utilisateur=self,
                solde_total=self.solde_initial,
                solde_restant=self.solde_initial
            )

    def get_absences_par_type(self):
        """
        Retourne un dictionnaire du style :
        {
            "Congé annuel": {"utilisés": 12, "quota": 30, "restants": 18},
            ...
        }
        """
        absences = Absence.objects.filter(utilisateur=self, statut='valide') \
            .values('type_absence__id', 'type_absence__nom', 'type_absence__plafond_annuel') \
            .annotate(utilises=Sum('nombre_jours'))

        result = {}
        for a in absences:
            quota = a['type_absence__plafond_annuel']
            utilises = a['utilises'] or 0
            restants = max(0, quota - utilises)
            result[a['type_absence__nom']] = {
                'utilisés': utilises,
                'quota': quota,
                'restants': restants
            }

        # Types jamais utilisés
        from .models import TypeAbsence
        for type_abs in TypeAbsence.objects.all():
            if type_abs.nom not in result:
                result[type_abs.nom] = {
                    'utilisés': 0,
                    'quota': type_abs.plafond_annuel,
                    'restants': type_abs.plafond_annuel
                }

        return result

    def nom_complet(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"

    
# -------------------------
# TYPE D'ABSENCE
# -------------------------
class TypeAbsence(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=100, unique=True)
    couleur = models.CharField(max_length=7, help_text="Code hexadécimal ex: #FF5733")
    plafond_annuel = models.IntegerField(help_text="Nombre maximum de jours par an")

    def __str__(self):
        return self.code

# -------------------------
# JOURS FÉRIÉS
# -------------------------
class JourFerie(models.Model):
    date = models.DateField(unique=True)
    nom = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.date} - {self.description}"
    

class Annee(models.Model):
    annee = models.IntegerField(unique=True)

    def __str__(self):
        return str(self.annee)


class Mois(models.Model):
    MOIS_CHOICES = [
        ('01', 'Janvier'),
        ('02', 'Février'),
        ('03', 'Mars'),
        ('04', 'Avril'),
        ('05', 'Mai'),
        ('06', 'Juin'),
        ('07', 'Juillet'),
        ('08', 'Août'),
        ('09', 'Septembre'),
        ('10', 'Octobre'),
        ('11', 'Novembre'),
        ('12', 'Décembre'),
    ]

    mois = models.CharField(max_length=2, choices=MOIS_CHOICES)
    annee = models.ForeignKey(Annee, on_delete=models.CASCADE, related_name='mois')

    class Meta:
        unique_together = ['mois', 'annee']
        ordering = ['mois']

    def __str__(self):
        return f"{self.get_mois_display()} {self.annee.annee}"



# -------------------------
# SOLDE DES CONGÉS
# -------------------------
class SoldeConge(models.Model):
    utilisateur = models.OneToOneField(Utilisateur, on_delete=models.CASCADE)
    solde_total = models.IntegerField(default=0)
    solde_restant = models.IntegerField(default=0)

    def __str__(self):
        return f"Solde de {self.utilisateur.email}"

# -------------------------
# DEMANDES D'ABSENCES
# -------------------------
class Absence(models.Model):
    STATUT_CHOICES = [
    ('en_attente', 'En attente'),
    ('approuve_superieur', 'Approuvé par supérieur'),
    ('valide', 'Validée par DRH'),
    ('refuse', 'Refusée'),
    ]

    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    type_absence = models.ForeignKey(TypeAbsence, on_delete=models.CASCADE)
    date_debut = models.DateField()
    date_fin = models.DateField(blank=True, null=True)  # Calculée si congé
    nombre_jours = models.IntegerField()
    justificatif = models.FileField(upload_to='justificatifs/', blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    commentaire_refus = models.TextField(blank=True, null=True)
    date_soumission = models.DateTimeField(auto_now_add=True)
    date_decision = models.DateTimeField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if self.date_debut and self.nombre_jours:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.utilisateur.email} - {self.type_absence.nom} ({self.statut})"
