from django.urls import path
from . import views
from .views import login_view, logout_view

urlpatterns = [
    path('', login_view, name='login'),
    path('deconnexion/', logout_view, name='logout'),
    path('changer-mot-de-passe/', views.changer_mot_de_passe, name='changer_mot_de_passe'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin/utilisateur/<int:user_id>/', views.detail_utilisateur, name='detail_utilisateur'),
    path('admin/utilisateur/<int:user_id>/modifier/', views.modifier_utilisateur, name='modifier_utilisateur'),
    path('admin/utilisateur/<int:user_id>/desactiver/', views.desactiver_utilisateur, name='desactiver_utilisateur'),
    path('admin/utilisateur/<int:user_id>/activer/', views.activer_utilisateur, name='activer_utilisateur'),
    path('admin/utilisateur/<int:user_id>/supprimer/', views.supprimer_utilisateur, name='supprimer_utilisateur'),
    path('admin/liste_superieurs/', views.liste_superieurs, name='liste_superieurs'),
    path('admin/utilisateurs/', views.creer_utilisateur, name='creer_utilisateurs'),
    path('admin/type-absence/', views.type_absence, name='type_absence'),
    path('admin/jour-ferie/', views.jour_ferie, name='jour_ferie'),
    path('admin/annee_mois/', views.annee_mois, name='annee_mois'),
    path('admin/calendrier/', views.calendrier, name='calendrier'),
    path('api/absences/', views.api_absences, name='api_absences'),
    path('admin/absences-mensuelles/', views.absences_par_mois, name='absences_par_mois'),
    path('dashboard/collaborateur/', views.dashboard_collaborateur, name='dashboard_collaborateur'),
    path('demande-absence/', views.demande_absence, name='demande_absence'),
    path('liste_absences/', views.liste_absences, name='liste_absences'),
    path('export-absences/', views.export_absences_excel, name='export_absences_excel'),
    path('quotas/', views.quotas_absences, name='quotas_absences'),
    path('infos/', views.infos_collaborateurs, name='infos_collaborateurs'),
    path('valider-absence/<int:absence_id>/', views.valider_absence, name='valider_absence'),
    path('absence/<int:absence_id>/refuser/', views.refuser_absence, name='refuser_absence'),
    path('absence/<int:absence_id>/approuver/', views.approuver_par_superieur, name='approuver_par_superieur'),


    # path('mes-absences/', views.mes_absences, name='mes_absences'),

]
