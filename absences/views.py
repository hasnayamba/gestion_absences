import contextlib
import openpyxl
import calendar
from openpyxl import Workbook
from django.shortcuts import render, redirect, get_object_or_404
from .models import Utilisateur, TypeAbsence, JourFerie, Annee, SoldeConge, Absence, Mois
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required 
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, F, Prefetch 
from collections import defaultdict
from django.utils.dateformat import DateFormat
from django.utils.timezone import localtime, now
from datetime import datetime, timedelta, date, time
from collections import defaultdict
from django.db.models.functions import ExtractMonth
from openpyxl.styles import Font
from django.http import HttpResponse
from django.core.mail import send_mail
def home(request):
    return render(request, 'authentification/login.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            if not user.mot_de_passe_change:
                return redirect('changer_mot_de_passe')
            return redirect('dashboard')
        else:
            messages.error(request, "Identifiants incorrects.")
    return render(request, 'authentification/login.html')
@login_required
def logout_view(request):
    logout(request)
    return redirect('login')



def dashboard(request):
    user = request.user
    if user.role == 'admin':
            # Récupérer mois et année GET ou valeur courante
        mois_filter = request.GET.get('mois')
        annee_filter = request.GET.get('annee')

        today = date.today()
        current_month = today.month
        current_year = today.year

        try:
            mois = int(mois_filter) if mois_filter else current_month
            annee = int(annee_filter) if annee_filter else current_year
        except ValueError:
            mois = current_month
            annee = current_year

        mois_choices = list(range(1, 13))
        annee_choices = list(range(2020, current_year + 1))

        # Récupérer tous les utilisateurs (avec filtres recherche, rôle, statut)
        utilisateurs = Utilisateur.objects.all()

        query = request.GET.get("q", "")
        role = request.GET.get("role", "")
        statut = request.GET.get("statut", "")
        sort = request.GET.get("sort", "matricule")
        direction = request.GET.get("dir", "asc")
        page_number = request.GET.get("page", 1)

        if query:
            utilisateurs = utilisateurs.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(matricule__icontains=query)
            )
        if role:
            utilisateurs = utilisateurs.filter(role=role)
        if statut == "actif":
            utilisateurs = utilisateurs.filter(is_active=True)
        elif statut == "inactif":
            utilisateurs = utilisateurs.filter(is_active=False)

        if direction == "desc":
            sort = f"-{sort}"
        utilisateurs = utilisateurs.order_by(sort)

        paginator = Paginator(utilisateurs, 10)
        utilisateurs_page = paginator.get_page(page_number)

        # Récupérer toutes les absences validées pour construire la map
        absences = Absence.objects.select_related('utilisateur', 'type_absence').filter(
        date_debut__year=annee,
        statut='valide'   # <-- ici on filtre uniquement les absences validées
    )
        absences_filtered_qs = Absence.objects.filter(
        date_debut__month=mois,
        date_debut__year=annee,
        statut='valide',  
    )

        usf = Utilisateur.objects.prefetch_related(
            Prefetch('absence_set', queryset=absences_filtered_qs, to_attr='absences_filtrees')
        )

        # Construire map clé=(utilisateur_id, mois_str) -> liste absences
        absences_map = defaultdict(list)
        for a in absences:
            mois_str = a.date_debut.strftime('%m')
            absences_map[(a.utilisateur.id, mois_str)].append(a)

        # Dictionnaire mois num -> label
        mois_liste = {
            '01': 'Janv', '02': 'Févr', '03': 'Mars', '04': 'Avril',
            '05': 'Mai', '06': 'Juin', '07': 'Juil', '08': 'Août',
            '09': 'Sept', '10': 'Oct', '11': 'Nov', '12': 'Déc'
        }

        type_absences = TypeAbsence.objects.all()

        # Fonction pour calculer jours d'absence
        def jours_absence(a):
            return (a.date_fin - a.date_debut).days + 1

        # Construire la liste à passer au template
        utilisateurs_data = []
        for emp in utilisateurs_page:
            absences_par_mois = []
            total_jours = 0
            for mois_num in mois_liste.keys():
                abs_list = absences_map.get((emp.id, mois_num), [])
                for a in abs_list:
                    a.badge_color = a.type_absence.couleur
                    if a.statut == 'refuse':
                        a.statut_style = 'text-decoration-line-through text-danger'
                    elif a.statut == 'en_attente':
                        a.statut_style = 'text-muted fst-italic'
                    else:
                        a.statut_style = ''
                    total_jours += jours_absence(a)
                absences_par_mois.append(abs_list)
            utilisateurs_data.append({
                'utilisateur': emp,
                'absences_par_mois': absences_par_mois,
                'total_jours_absence': total_jours,
            })

        # Statistiques globales pour le graphe
        absences_par_mois_qs = (
            Absence.objects
            .filter(date_debut__year=annee, statut='valide')
            .annotate(mois=ExtractMonth('date_debut'))
            .values('mois')
            .annotate(nombre=Count('id'))
            .order_by('mois')
        )
        absences_par_mois = {item['mois']: item['nombre'] for item in absences_par_mois_qs}
        mois_labels = ['Jan', 'Fév', 'Mars', 'Avril', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc']
        absences_data_graph = [absences_par_mois.get(i + 1, 0) for i in range(12)]

        # Autres stats
        nb_users = utilisateurs.count()
        nb_absences = absences.count()
        nb_en_attente = Absence.objects.filter(statut='en_attente').count()
        total_utilisateurs = Utilisateur.objects.count()
        absences_validees_annee = Absence.objects.filter(statut="valide", date_debut__year=current_year).count()
        recuperations = Absence.objects.filter(type_absence__nom__icontains="récup", statut="valide", date_debut__year=current_year).count()
        absences_en_cours = Absence.objects.filter(statut="en_attente").count()
        absences = Absence.objects.filter(statut='approuve_superieur')


        absences_en_attente = Absence.objects.filter(statut='approuve_superieur')
        compteur_alertes = absences_en_attente.count()

        context = {
            'absences_en_attente': absences_en_attente,
            'compteur_alertes': compteur_alertes,
            'mois_labels': mois_labels,
            'nb_users': nb_users,
            'nb_absences': nb_absences,
            'nb_en_attente': nb_en_attente,
            'mois_liste': mois_liste,
            'type_absences': type_absences,
            'utilisateurs': utilisateurs_page,
            'utilisateurs_data': utilisateurs_data,
            'total_utilisateurs': total_utilisateurs,
            'absences_validees_annee': absences_validees_annee,
            'recuperations': recuperations,
            'absences_en_cours': absences_en_cours,
            'current_sort': sort.strip('-'),
            'current_dir': direction,
            'request': request,
            'mois_filtre': mois,
            'annee_filtre': annee,
            'mois_choices': mois_choices,
            'annee_choices': annee_choices,
            'absences_data': absences_data_graph,
            'usf':usf,
        }

        return render(request, "dashboards/admin.html", context)
    elif user.role == 'drh':
            # Filtres GET
        date_debut = request.GET.get('date_debut')
        date_fin = request.GET.get('date_fin')
        type_absence_id = request.GET.get('type_absence')
        absences = Absence.objects.filter(statut='approuve_superieur')
        absences_validees = Absence.objects.filter(statut='valide').select_related('utilisateur', 'type_absence')
        demandes_en_attente = Absence.objects.filter(statut='en_attente').select_related('utilisateur', 'type_absence')

        if date_debut:
            absences_validees = absences_validees.filter(date_debut__gte=date_debut)
            demandes_en_attente = demandes_en_attente.filter(date_debut__gte=date_debut)
        if date_fin:
            absences_validees = absences_validees.filter(date_fin__lte=date_fin)
            demandes_en_attente = demandes_en_attente.filter(date_fin__lte=date_fin)
        if type_absence_id:
            absences_validees = absences_validees.filter(type_absence_id=type_absence_id)
            demandes_en_attente = demandes_en_attente.filter(type_absence_id=type_absence_id)

        collaborateurs = Utilisateur.objects.filter(role='collaborateur').order_by('matricule')
        types_absence = TypeAbsence.objects.all()

        # Gestion POST (validation/refus)
        if request.method == 'POST':
            absence_id = request.POST.get('absence_id')
            action = request.POST.get('action')
            absence = get_object_or_404(Absence, id=absence_id)

            if action == 'valider':
                # Vérifier le solde disponible
                solde = absence.utilisateur.soldeconge
                if solde.solde_restant < absence.nombre_jours:
                    messages.error(request, "Solde insuffisant pour valider cette demande.")
                else:
                    absence.statut = 'valide'
                    absence.date_decision = now()
                    absence.save()
                    solde.solde_restant -= absence.nombre_jours
                    solde.save()
                    messages.success(request, f"Demande de {absence.utilisateur.first_name} validée.")

            elif action == 'refuser':
                motif = request.POST.get('commentaire_refus')
                if not motif:
                    messages.error(request, "Merci d'indiquer un motif de refus.")
                else:
                    absence.statut = 'refuse'
                    absence.commentaire_refus = motif
                    absence.date_decision = now()
                    absence.save()
                    messages.success(request, f"Demande de {absence.utilisateur.first_name} refusée.")

            return redirect('drh')

        return render(request, 'dashboards/drh.html', {
            'absences_validees': absences_validees,
            'demandes_en_attente': demandes_en_attente,
            'collaborateurs': collaborateurs,
            'types_absence': types_absence,
        })
    elif user.role == 'ca' or user.role == 'cp':
        user = request.user
        collaborateurs = Utilisateur.objects.filter(superieur=user)
        absences = Absence.objects.filter(utilisateur__in=collaborateurs)

        # Filtres
        mois_filtre = request.GET.get('mois')
        annee_filtre = request.GET.get('annee')
        statut = request.GET.get('statut')
        collaborateur_id = request.GET.get('collaborateur')

        if collaborateur_id:
            absences = absences.filter(utilisateur__id=collaborateur_id)
        if mois_filtre:
            absences = absences.filter(date_debut__month=mois_filtre)
        if annee_filtre:
            absences = absences.filter(date_debut__year=annee_filtre)
        if statut:
            absences = absences.filter(statut=statut)

        context = {
            'collaborateurs': collaborateurs,
            'absences': absences.order_by('-date_debut'),
            'mois_choices': range(1, 13),
            'annee_choices': range(2023, 2026),
            'mois_filtre': mois_filtre,
            'annee_filtre': annee_filtre,
        }
        return render(request, 'dashboards/superieur.html', context)
    else:
        return redirect('dashboard_collaborateur')
    
    
@login_required
def approuver_par_superieur(request, absence_id):
    absence = get_object_or_404(Absence, id=absence_id)
    if request.user == absence.utilisateur.superieur:
        absence.statut = 'approuve_superieur'
        absence.save()
        messages.success(request, "Demande d'absence approuvée. En attente de validation DRH.")
    else:
        messages.error(request, "Action non autorisée.")
    return redirect('dashboards/superieur')
    
def valider_absence(request, absence_id):
    absence = get_object_or_404(Absence, id=absence_id)
    absence.statut = 'en_attente'
    absence.save()
    messages.success(request, f"L'absence de {absence.utilisateur.get_full_name()} a été validée.")
    return redirect('liste_absences')    

def refuser_absence(request, absence_id):
    absence = get_object_or_404(Absence, id=absence_id)
    absence.statut = 'refuse'
    absence.save()
    messages.warning(request, f"L'absence de {absence.utilisateur.get_full_name()} a été refusée.")
    return redirect('dashboards/superieur')  # ou un autre nom de vue

@login_required
def changer_mot_de_passe(request):
    if request.method == 'POST':
        nouveau = request.POST.get('nouveau')
        confirmation = request.POST.get('confirmation')

        if nouveau != confirmation:
            messages.error(request, "Les mots de passe ne correspondent pas.")
        elif len(nouveau) < 6:
            messages.error(request, "Le mot de passe doit contenir au moins 6 caractères.")
        else:
            user = request.user
            user.set_password(nouveau)
            user.mot_de_passe_change = True
            user.save()

            # Mise à jour de la session pour ne pas déconnecter l’utilisateur
            update_session_auth_hash(request, user)

            messages.success(request, "Mot de passe mis à jour avec succès.")
            return redirect('dashboard')

    return render(request, 'authentification/changer_mot_de_passe.html')

@login_required
def creer_utilisateur(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        role = request.POST.get('role')
        solde_initial = request.POST.get('solde_initial')
        superieur_id = request.POST.get('superieur')

        # Création de l'utilisateur avec mot de passe par défaut
        user = Utilisateur.objects.create_user(
            email=email,
            password='1234',
            first_name=first_name,
            last_name=last_name,
            role=role,
            solde_initial=solde_initial
        )

        # Rattachement au supérieur hiérarchique si défini
        if superieur_id:
            with contextlib.suppress(Utilisateur.DoesNotExist):
                superieur = Utilisateur.objects.get(id=superieur_id)
                user.superieur = superieur
                user.save()

        messages.success(request, "Utilisateur ajouté avec succès.")
        return redirect('dashboard')

    # Requête GET → afficher la page de création
    superieurs = Utilisateur.objects.exclude(role='collaborateur')
    utilisateurs = Utilisateur.objects.all().order_by('date_joined')
    return render(request, 'admins/utilisateurs.html', {
        'superieurs': superieurs,
        'utilisateurs': utilisateurs
    })

@login_required
def detail_utilisateur(request, user_id):
    user = get_object_or_404(Utilisateur, id=user_id)
    return render(request, 'absences/detail_utilisateur.html', {'user': user})
@login_required
def modifier_utilisateur(request, user_id):
    user = get_object_or_404(Utilisateur, id=user_id)
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.role = request.POST.get('role')
        superieur_id = request.POST.get('superieur')
        user.superieur = Utilisateur.objects.get(id=superieur_id) if superieur_id else None
        user.save()
        messages.success(request, "Utilisateur modifié.")
        return redirect('dashboard')
    superieurs = Utilisateur.objects.filter(role='directeur').exclude(id=user.id)
    return render(request, 'dashboards/admin.html', {'user': user, 'superieurs': superieurs})
@login_required
def desactiver_utilisateur(request, user_id):
    user = get_object_or_404(Utilisateur, id=user_id)
    user.is_active = False
    user.save()
    messages.warning(request, "Compte désactivé.")
    return redirect('dashboard')
@login_required
def activer_utilisateur(request, user_id):
    user = get_object_or_404(Utilisateur, id=user_id)
    user.is_active = True
    user.save()
    messages.success(request, "Compte réactivé.")
    return redirect('dashboard')
@login_required
def supprimer_utilisateur(request, user_id):
    user = get_object_or_404(Utilisateur, id=user_id)
    user.delete()
    messages.error(request, "Utilisateur supprimé.")
    return redirect('dashboard')

@login_required
def liste_superieurs(request):
    superieurs = Utilisateur.objects.exclude(role='collaborateur')
    return render(request, 'admins/superieurs.html', {'superieurs': superieurs})
@login_required
def type_absence(request):
    # 🔹 Ajout d’un type d’absence
    if request.method == 'POST' and 'ajouter' in request.POST:
        nom = request.POST.get('nom')
        code = request.POST.get('code')
        couleur = request.POST.get('couleur')
        plafond_annuel = request.POST.get('plafond_annuel')

        if nom and code and couleur and plafond_annuel:
            try:
                plafond = int(plafond_annuel)
                TypeAbsence.objects.create(
                    nom=nom,
                    code=code,
                    couleur=couleur,
                    plafond_annuel=plafond
                )
                messages.success(request, "Type d'absence ajouté avec succès.")
            except ValueError:
                messages.error(request, "Le plafond annuel doit être un nombre entier.")
        else:
            messages.error(request, "Tous les champs sont obligatoires pour l'ajout.")

        return redirect('type_absence')

    # 🔹 Modification d’un type d’absence
    if request.method == 'POST' and 'modifier' in request.POST:
        type_id = request.POST.get('type_id')
        nouveau_nom = request.POST.get('nouveau_nom')
        nouveau_code = request.POST.get('nouveau_code')
        nouvelle_couleur = request.POST.get('nouvelle_couleur')
        nouveau_plafond = request.POST.get('nouveau_plafond')

        type_instance = get_object_or_404(TypeAbsence, id=type_id)
        try:
            type_instance.nom = nouveau_nom
            type_instance.code = nouveau_code
            type_instance.couleur = nouvelle_couleur
            type_instance.plafond_annuel = int(nouveau_plafond)
            type_instance.save()
            messages.success(request, "Type d'absence modifié avec succès.")
        except ValueError:
            messages.error(request, "Le plafond annuel doit être un entier valide.")

        return redirect('type_absence')

    # 🔹 Suppression d’un type d’absence
    if request.method == 'POST' and 'supprimer' in request.POST:
        type_id = request.POST.get('type_id')
        type_instance = get_object_or_404(TypeAbsence, id=type_id)
        type_instance.delete()
        messages.success(request, "Type d'absence supprimé.")
        return redirect('type_absence')

    # 🔹 Affichage des types
    types = TypeAbsence.objects.all().order_by('nom')
    return render(request, 'admins/type_absence.html', {'types': types})
@login_required
def jour_ferie(request):
    # ➕ Ajout
    if request.method == 'POST' and 'ajouter' in request.POST:
        date = request.POST.get('date')
        nom = request.POST.get('nom')
        description = request.POST.get('description')

        if date and nom and description:
            JourFerie.objects.create(date=date, nom=nom, description=description)
            messages.success(request, "Jour férié ajouté avec succès.")
        else:
            messages.error(request, "Tous les champs sont obligatoires.")
        return redirect('jour_ferie')

    # ✏️ Modification
    if request.method == 'POST' and 'modifier' in request.POST:
        jour_id = request.POST.get('jour_id')
        date = request.POST.get('nouvelle_date')
        nom = request.POST.get('nouveau_nom')
        description = request.POST.get('nouvelle_description')

        jf = get_object_or_404(JourFerie, id=jour_id)
        jf.date = date
        jf.nom = nom
        jf.description = description
        jf.save()
        messages.success(request, "Jour férié modifié avec succès.")
        return redirect('jour_ferie')

    # 🗑️ Suppression
    if request.method == 'POST' and 'supprimer' in request.POST:
        jour_id = request.POST.get('jour_id')
        jf = get_object_or_404(JourFerie, id=jour_id)
        jf.delete()
        messages.success(request, "Jour férié supprimé.")
        return redirect('jour_ferie')

    # 📋 Affichage
    jours = JourFerie.objects.all().order_by('date')
    return render(request, 'admins/jour_ferie.html', {'jours': jours})

@login_required
def annee_mois(request):
    if request.method == 'POST':
        # Ajouter une année
        if 'ajouter_annee' in request.POST:
            annee_val = request.POST.get('annee')
            if annee_val:
                try:
                    Annee.objects.create(annee=int(annee_val))
                    messages.success(request, f"Année {annee_val} ajoutée avec succès.")
                except:
                    messages.error(request, "Cette année existe déjà.")
            return redirect('annee_mois')

        # Supprimer une année
        elif 'supprimer_annee' in request.POST:
            annee_id = request.POST.get('annee_id')
            Annee.objects.filter(id=annee_id).delete()
            messages.success(request, "Année supprimée.")
            return redirect('annee_mois')

        # Ajouter un mois
        elif 'ajouter_mois' in request.POST:
            annee_id = request.POST.get('annee_id')
            mois_code = request.POST.get('mois')
            if annee_id and mois_code:
                annee = Annee.objects.get(id=annee_id)
                if not Mois.objects.filter(annee=annee, mois=mois_code).exists():
                    Mois.objects.create(annee=annee, mois=mois_code)
                    messages.success(request, "Mois ajouté.")
                else:
                    messages.warning(request, "Ce mois existe déjà pour cette année.")
            return redirect('annee_mois')

        # Supprimer un mois
        elif 'supprimer_mois' in request.POST:
            mois_id = request.POST.get('mois_id')
            Mois.objects.filter(id=mois_id).delete()
            messages.success(request, "Mois supprimé.")
            return redirect('annee_mois')

    # Récupérer les années et les mois associés
    annees = Annee.objects.prefetch_related('mois').all()
    for an in annees:
        an.mois_existants = [m.mois for m in an.mois.all()]  # utile pour ne pas réafficher un mois déjà ajouté

    context = {
        'annees': annees,
        'mois_choices': Mois.MOIS_CHOICES,
    }
    return render(request, 'admins/annee_mois.html', context)


@login_required
def calendrier(request):
    return render(request, 'admins/calendrier.html')

@login_required
def api_absences(request):
    absences = Absence.objects.select_related('utilisateur', 'type_absence')
    events = []

    for absence in absences:
        events.append({
            "title": f"{absence.utilisateur.first_name} {absence.utilisateur.last_name} - {absence.type_absence.nom}",
            "start": absence.date_debut.isoformat(),
            "end": (absence.date_fin or absence.date_debut).isoformat(),
            "color": absence.type_absence.couleur,
        })

    return JsonResponse(events, safe=False)


@login_required
def absences_par_mois(request):
    absences = Absence.objects.select_related('utilisateur', 'type_absence').order_by('date_debut')
    
    # Regrouper par mois
    absences_par_mois = defaultdict(list)
    for abs in absences:
        mois = abs.date_debut.month
        annee = abs.date_debut.year
        cle = f"{calendar.month_name[mois]} {annee}"
        absences_par_mois[cle].append(abs)

    # Tri par mois (ordre chronologique)
    absences_par_mois = dict(sorted(absences_par_mois.items(), key=lambda x: (int(x[0].split()[-1]), list(calendar.month_name).index(x[0].split()[0]))))

    return render(request, 'admin/absences_par_mois.html', {
        'absences_par_mois': absences_par_mois
    })
    
    
def calculer_date_fin(date_debut, nombre_jours):
    jours_restants = nombre_jours
    date_courante = date_debut
    while jours_restants > 0:
        if date_courante.weekday() < 5:  # 0 à 4 = lundi à vendredi
            jours_restants -= 1
        date_courante += timedelta(days=1)
    return date_courante - timedelta(days=1)
    
    
@login_required
def dashboard_collaborateur(request):
    user = request.user

    # Vérifie que l'utilisateur est bien un collaborateur
    if user.role != 'collaborateur':  # ou 'employe', selon ton modèle
        return render(request, 'unauthorized.html', status=403)

    # Récupération des absences de l'utilisateur connecté
    absences = Absence.objects.filter(utilisateur=user).select_related('type_absence')

    # Nombre total d'absences
    total_absences = absences.count()

    # Nombre d’absences par type
    absences_par_type = absences.values('type_absence__nom').annotate(nombre=Count('id'))
    absences_par_type_dict = {item['type_absence__nom']: item['nombre'] for item in absences_par_type}

    def nombre_jours_ouvres(date_debut, date_fin):
        jours_ouvres = 0
        courant = date_debut
        while courant <= date_fin:
            if courant.weekday() < 5:
                jours_ouvres += 1
            courant += timedelta(days=1)
        return jours_ouvres

    # Appliquer à chaque absence
    for absence in absences:
        absence.duree = nombre_jours_ouvres(absence.date_debut, absence.date_fin) # +1 pour inclure le jour de début

    context = {
        'total_absences': total_absences,
        'absences_par_type': absences_par_type_dict,
        'absences': absences,
    }

    return render(request, 'dashboards/collaborateur.html', context)


# Fonction utilitaire pour exclure les week-ends
def calculer_date_fin(date_debut, nombre_jours):
    jour = 0
    date_courante = date_debut
    while jour < nombre_jours:
        if date_courante.weekday() < 5:  # Lundi à Vendredi
            jour += 1
        date_courante += timedelta(days=1)
    return date_courante - timedelta(days=1)

@login_required
def demande_absence(request): 
    user = request.user
    types_absence = TypeAbsence.objects.all()

    if request.method == 'POST':
        type_id = request.POST.get('type_absence')
        date_debut = request.POST.get('date_debut')
        nombre_jours = request.POST.get('nombre_jours')
        justificatif = request.FILES.get('justificatif')

        if not (type_id and date_debut and nombre_jours):
            messages.error(request, "Tous les champs obligatoires doivent être remplis.")
            return redirect('demande_absence')

        type_abs = TypeAbsence.objects.get(pk=type_id)
        date_debut = date.fromisoformat(date_debut)
        nombre_jours = int(nombre_jours)
        date_fin = calculer_date_fin(date_debut, nombre_jours)

        # 🔍 Vérification anti-chevauchement
        chevauchements = Absence.objects.filter(
            utilisateur=user,
            date_debut__lte=date_fin,
            date_fin__gte=date_debut
        )
        if chevauchements.exists():
            messages.error(request, "Une absence existe déjà sur cette période.")
            return redirect('demande_absence')

        # ✅ Création de l'absence
        absence = Absence.objects.create(
            utilisateur=user,
            type_absence=type_abs,
            date_debut=date_debut,
            date_fin=date_fin,
            nombre_jours=nombre_jours,
            justificatif=justificatif,
            statut='en_attente',
            date_soumission=now()
        )
        messages.success(request, "Votre demande d'absence a été envoyée avec succès.")
        

        # 📩 Notifications email (supérieur et DRH)
        destinataires = []

        if user.superieur and user.superieur.email:
            destinataires.append(user.superieur.email)

        drh = Utilisateur.objects.filter(role='drh').first()
        if drh and drh.email:
            destinataires.append(drh.email)

        if destinataires:
            sujet = f"Nouvelle demande d'absence de {user.get_full_name()}"
            message = (
                f"{user.get_full_name()} a soumis une demande d'absence :\n"
                f"• Type : {type_abs.nom}\n"
                f"• Du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')} "
                f"({nombre_jours} jours ouvrés).\n\n"
                "Veuillez la consulter sur la plateforme."
            )

            send_mail(
                sujet,
                message,
                'no-reply@absencesapp.com',
                destinataires,
                fail_silently=True
            )

        messages.success(request, f"Demande envoyée jusqu’au {date_fin.strftime('%d/%m/%Y')}.")
        return redirect('dashboard_collaborateur')

    return render(request, 'collaborateurs/demande_absence.html', {
        'types_absence': types_absence,
        'today': date.today().isoformat()
    })

def export_absences_excel(request):
    # Création du classeur Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Absences acceptées"

    # En-têtes
    headers = [
        "Matricule", "Nom", "Prénom", "Email", "Rôle", "Supérieur",
        "Type d'absence", "Date début", "Date fin", "Nombre de jours", "Date validation"
    ]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Données
    absences = Absence.objects.filter(statut='valide').select_related('utilisateur', 'type_absence')

    for absence in absences:
        user = absence.utilisateur
        superieur = user.superieur.get_full_name() if user.superieur else "-"
        nb_jours = (absence.date_fin - absence.date_debut).days + 1 if absence.date_fin else absence.nombre_jours

        ws.append([
            user.matricule,
            user.last_name,
            user.first_name,
            user.email,
            user.get_role_display(),
            superieur,
            absence.type_absence.nom,
            absence.date_debut.strftime('%d/%m/%Y'),
            absence.date_fin.strftime('%d/%m/%Y') if absence.date_fin else '',
            nb_jours,
            absence.date_soumission.strftime('%d/%m/%Y')
        ])

    # Préparer la réponse HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=absences_validees.xlsx'
    wb.save(response)
    return response

def liste_absences(request):
    # Filtres GET
    mois = request.GET.get('mois')
    annee = request.GET.get('annee')
    statut = request.GET.get('statut')
    type_absence = request.GET.get('type')
    
    today = date.today()
    current_month = today.month
    current_year = today.year
    # Base queryset
    absence_query = Absence.objects.select_related('type_absence').order_by('-date_debut')

    # Appliquer les filtres
    if mois:
        absence_query = absence_query.filter(date_debut__month=int(mois))
    if annee:
        absence_query = absence_query.filter(date_debut__year=int(annee))
    if statut:
        absence_query = absence_query.filter(statut=statut)
    if type_absence:
        absence_query = absence_query.filter(type_absence__id=type_absence)

    # Récupérer utilisateurs avec absences filtrées
    utilisateurs = Utilisateur.objects.prefetch_related(
        Prefetch('absence_set', queryset=absence_query, to_attr='absences')
    )

    # Statistiques générales
    today = date.today()
    nb_attente = Absence.objects.filter(statut='en_attente').count()
    nb_valide_mois = Absence.objects.filter(statut='valide', date_debut__month=today.month, date_debut__year=today.year).count()
    nb_valide_annee = Absence.objects.filter(statut='valide', date_debut__year=today.year).count()

    # Pour filtres dynamiques
    types_absence = TypeAbsence.objects.all()
    # Absences filtrées
    toutes_absences=Absence.objects.all()
    absences_attente = toutes_absences.filter(statut='approuve_superieur')
    absences_valide_mois = toutes_absences.filter(statut='valide', date_debut__month=current_month, date_debut__year=current_year)
    absences_valide_annee = toutes_absences.filter(statut='valide', date_debut__year=current_year)
    mois_liste = {
    "01": "Janvier",
    "02": "Février",
    "03": "Mars",
    "04": "Avril",
    "05": "Mai",
    "06": "Juin",
    "07": "Juillet",
    "08": "Août",
    "09": "Septembre",
    "10": "Octobre",
    "11": "Novembre",
    "12": "Décembre"
}

    if request.method == 'POST':
        absence_id = request.POST.get('absence_id')
        action = request.POST.get('action')
        motif_refus = request.POST.get('motif_refus', '')

        absence = get_object_or_404(Absence, id=absence_id)
        if action == 'valide':
            absence.statut = 'valide'
            absence.motif_refus = ''
            messages.success(request, f"L'absence de {absence.utilisateur.first_name} {absence.utilisateur.last_name} a été validée.")
        elif action == 'refuse':
            absence.statut = 'refuse'
            absence.motif_refus = motif_refus
            messages.warning(request, f"L'absence de {absence.utilisateur.first_name} {absence.utilisateur.last_name} a été refusée.")
        absence.save()
        return redirect('liste_absences')
    annees_disponibles = [2023, 2024, 2025]
    
    collaborateurs = Utilisateur.objects.filter(role='collaborateur')

    data = []
    for user in collaborateurs:
        lignes = []
        for type_abs in TypeAbsence.objects.all():
            total = Absence.objects.filter(utilisateur=user, type_absence=type_abs, statut='valide')\
                        .aggregate(total=Sum('nombre_jours'))['total'] or 0
            lignes.append({
                'type': type_abs.code,
                'utilisé': total,
                'plafond': type_abs.plafond_annuel,
                'restant': max(type_abs.plafond_annuel - total, 0),
                'couleur': type_abs.couleur
            })
        data.append({
            'utilisateur': user,
            'absences': lignes
        })

    return render(request, 'absences/liste_absences.html', {
        'data': data,
        'types': TypeAbsence.objects.all(),
        'utilisateurs': utilisateurs,
        'nb_attente': nb_attente,
        'nb_valide_mois': nb_valide_mois,
        'nb_valide_annee': nb_valide_annee,
        'types_absence': types_absence,
        'mois_selected': mois,
        'annee_selected': annee,
        'statut_selected': statut,
        'type_selected': type_absence,
        'mois_liste': mois_liste,
        'annees_disponibles': annees_disponibles,
        'absences': toutes_absences,
        'absences_attente': absences_attente,
        'nb_attente': nb_attente,
        'nb_valide_mois': nb_valide_mois,
        'nb_valide_annee': nb_valide_annee,
    })


@login_required
def quotas_absences(request):
    collaborateurs = Utilisateur.objects.filter(role='collaborateur')

    data = []
    for user in collaborateurs:
        lignes = []
        for type_abs in TypeAbsence.objects.all():
            total = Absence.objects.filter(utilisateur=user, type_absence=type_abs, statut='valide')\
                        .aggregate(total=Sum('nombre_jours'))['total'] or 0
            lignes.append({
                'type': type_abs.code,
                'utilisé': total,
                'plafond': type_abs.plafond_annuel,
                'restant': max(type_abs.plafond_annuel - total, 0),
                'couleur': type_abs.couleur
            })
        data.append({
            'utilisateur': user,
            'absences': lignes
        })

    return render(request, 'absences/liste_absences.html', {
        'data': data,
        'types': TypeAbsence.objects.all()
    })
    
@login_required
def infos_collaborateurs(request):
    collaborateurs = Utilisateur.objects.select_related('superieur').filter(role='collaborateur')
    return render(request, 'drh/infos_collaborateurs.html', {
        'collaborateurs': collaborateurs
    })
