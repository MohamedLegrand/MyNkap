from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.admin import service
from app.modules.admin.schemas import (
    AdminAbonnementItem,
    AdminAbonnementListResponse,
    AdminAbonnementOverview,
    AdminClientDetail,
    AdminClientListResponse,
    AdminClientStatusUpdate,
    AdminCreate,
    AdminForceAbonnementPayload,
    AdminFraudeOverview,
    AdminGlobalKPIsResponse,
    AdminLevelUpdate,
    AdminListItem,
    AdminPaiementItem,
    AdminPaiementListResponse,
    AdminPlanCreate,
    AdminPlanUpdate,
    AdminResetPasswordResponse,
    AdminStatusUpdate,
    AdminTransactionSuspecteDetail,
    AdminTransactionSuspecteItem,
    AdminTransactionSuspecteListResponse,
    AdminUpdateSuspicionPayload,
    AdminValiderPaiementManuelPayload,
    AuditLogDetail,
    AuditLogListResponse,
    AuditStatsResponse,
    ConfigItem,
    ConfigUpdate,
)
from app.modules.auth.dependencies import get_current_active_admin
from app.modules.auth.models import Administrateur, Client
from app.modules.auth.schemas import AdminOut, ClientOut
from app.modules.plans.schemas import PlanOut

router = APIRouter(prefix="/admin", tags=["Administration"])

# --- Endpoints Dashboard & KPIs Globaux ---

@router.get(
    "/kpis",
    response_model=AdminGlobalKPIsResponse,
    summary="Tableau de bord des KPIs globaux de la plateforme (Admin)"
)
def get_global_kpis(
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Retourne l'ensemble des indicateurs de performance clés (KPIs) de la plateforme (Clients, Finances, Abonnements, Sécurité).
    Réservé aux administrateurs.
    """
    return service.obtenir_kpis_globaux_admin(db)

# --- Endpoints Gestion des Clients ---

@router.get(
    "/clients",
    response_model=AdminClientListResponse,
    summary="Lister et rechercher les clients (Admin)"
)
def list_clients(
    q: Optional[str] = Query(None, description="Recherche par email, nom, prénom ou téléphone"),
    est_actif: Optional[bool] = Query(None, description="Filtre par statut actif/inactif"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Retourne la liste paginée des clients de la plateforme avec filtres de recherche.
    Réservé aux administrateurs.
    """
    return service.lister_clients_admin(db, q=q, est_actif=est_actif, page=page, page_size=page_size)

@router.get(
    "/clients/{id_client}",
    response_model=AdminClientDetail,
    summary="Consulter le détail et la synthèse d'un client (Admin)"
)
def get_client_detail(
    id_client: int,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Retourne la fiche complète d'un client avec ses statistiques d'activité.
    Réservé aux administrateurs.
    """
    return service.obtenir_detail_client_admin(db, id_client=id_client)

@router.patch(
    "/clients/{id_client}/status",
    response_model=ClientOut,
    summary="Activer ou désactiver un compte client (Admin)"
)
def update_client_status(
    id_client: int,
    payload: AdminClientStatusUpdate,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Bascule l'état d'activité d'un compte client (suspendre ou réactiver le compte).
    Si le compte est désactivé, révoque automatiquement toutes ses sessions actives.
    Tracé dans l'AuditLog. Réservé aux administrateurs.
    """
    return service.changer_statut_client(
        db, admin=current_admin, id_client=id_client, payload=payload, request=request
    )

@router.post(
    "/clients/{id_client}/reset-password",
    response_model=AdminResetPasswordResponse,
    summary="Réinitialiser le mot de passe d'un client (Admin)"
)
def reset_client_password(
    id_client: int,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Génère un mot de passe temporaire pour débloquer un client en cas de litige ou problème d'accès,
    et déconnecte ses sessions en cours.
    Tracé dans l'AuditLog. Réservé aux administrateurs.
    """
    return service.reinitialiser_mot_de_passe_client(
        db, admin=current_admin, id_client=id_client, request=request
    )

# --- Endpoints Gestion des Administrateurs ---

@router.get(
    "/admins",
    response_model=List[AdminListItem],
    summary="Lister les administrateurs de la plateforme (Admin)"
)
def list_admins(
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Retourne la liste complète de l'équipe administrateur.
    Réservé aux administrateurs.
    """
    return service.lister_administrateurs_admin(db)

@router.post(
    "/admins",
    response_model=AdminListItem,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouvel administrateur (Admin)"
)
def create_admin(
    payload: AdminCreate,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Crée un nouvel administrateur avec un niveau d'accès défini (1: Support, 2: Modérateur, 3: Superadmin).
    Exige au minimum un niveau d'accès 2 pour créer d'autres admins.
    Tracé dans l'AuditLog.
    """
    return service.creer_administrateur_admin(
        db, admin_createur=current_admin, schema=payload, request=request
    )

@router.patch(
    "/admins/{id_admin}/level",
    response_model=AdminListItem,
    summary="Modifier le niveau d'accès d'un administrateur (Superadmin)"
)
def update_admin_level(
    id_admin: int,
    payload: AdminLevelUpdate,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Modifie le niveau d'accès d'un membre de l'équipe admin (1, 2 ou 3).
    Réservé exclusivement aux Superadmins (niveau 3).
    Intègre un garde-fou contre la rétrogradation du dernier Superadmin actif.
    Tracé dans l'AuditLog.
    """
    return service.modifier_niveau_acces_admin(
        db, admin_modificateur=current_admin, id_target_admin=id_admin, schema=payload, request=request
    )

@router.patch(
    "/admins/{id_admin}/status",
    response_model=AdminListItem,
    summary="Activer ou désactiver un administrateur (Superadmin)"
)
def update_admin_status(
    id_admin: int,
    payload: AdminStatusUpdate,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Active ou suspend un compte administrateur.
    Réservé exclusivement aux Superadmins (niveau 3).
    Garde-fous : Interdiction d'auto-suspension et de désactivation du dernier Superadmin actif.
    Tracé dans l'AuditLog.
    """
    return service.changer_statut_administrateur(
        db, admin_modificateur=current_admin, id_target_admin=id_admin, schema=payload, request=request
    )

# --- Endpoints Audit Global ---

@router.get(
    "/audit/stats",
    response_model=AuditStatsResponse,
    summary="Consulter les statistiques d'audit globales (Admin)"
)
def get_audit_stats(
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Retourne les métriques d'activité et la répartition des actions les plus courantes dans l'AuditLog.
    Réservé aux administrateurs.
    """
    return service.obtenir_statistiques_audit_admin(db)

@router.get(
    "/audit",
    response_model=AuditLogListResponse,
    summary="Lister et filtrer les journaux d'audit (Admin)"
)
def list_audit_logs(
    id_utilisateur: Optional[int] = Query(None, description="Filtre par ID d'utilisateur"),
    action: Optional[str] = Query(None, description="Filtre par nom d'action (ex: CONNEXION, ADMIN)"),
    ressource: Optional[str] = Query(None, description="Filtre par ressource (ex: CLIENT, TRANSACTION)"),
    id_ressource: Optional[int] = Query(None, description="Filtre par ID de la ressource ciblée"),
    date_debut: Optional[datetime] = Query(None, description="Filtre date de début"),
    date_fin: Optional[datetime] = Query(None, description="Filtre date de fin"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Consulter, rechercher et filtrer les journaux d'audit de la plateforme.
    Réservé aux administrateurs.
    """
    return service.lister_audit_logs_admin(
        db,
        id_utilisateur=id_utilisateur,
        action=action,
        ressource=ressource,
        id_ressource=id_ressource,
        date_debut=date_debut,
        date_fin=date_fin,
        page=page,
        page_size=page_size,
    )

@router.get(
    "/audit/{id_audit}",
    response_model=AuditLogDetail,
    summary="Consulter le détail d'une entrée d'audit (Admin)"
)
def get_audit_log_detail(
    id_audit: int,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Retourne les détails complets d'un événement d'audit incluant les payloads JSON donnees_avant et donnees_apres.
    Réservé aux administrateurs.
    """
    return service.obtenir_detail_audit_log_admin(db, id_audit=id_audit)

# --- Endpoints Configuration Système ---

@router.get(
    "/config",
    response_model=List[ConfigItem],
    summary="Lister la configuration système applicative (Admin)"
)
def list_configs(
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Consulter l'ensemble des paramètres de configuration système (réservé aux admins niveau 1+).
    """
    return service.lister_configs_admin(db)

@router.get(
    "/config/{cle}",
    response_model=ConfigItem,
    summary="Consulter un paramètre de configuration spécifique (Admin)"
)
def get_config_by_key(
    cle: str,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Consulter un paramètre de configuration système par sa clé.
    """
    return service.obtenir_config_admin(db, cle=cle)

@router.put(
    "/config/{cle}",
    response_model=ConfigItem,
    summary="Créer ou modifier un paramètre de configuration système (Admin)"
)
def update_config(
    cle: str,
    payload: ConfigUpdate,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Crée ou met à jour la valeur d'une clé de configuration applicative à chaud sans redéploiement.
    Réservé aux administrateurs de niveau 2 minimum (Modérateurs / Superadmins).
    Tracé dans l'AuditLog.
    """
    return service.modifier_config_admin(
        db, admin=current_admin, cle=cle, payload=payload, request=request
    )

# --- Endpoints Gestion des Plans Tarifaires ---

@router.get(
    "/plans",
    response_model=List[PlanOut],
    summary="Lister le catalogue des plans tarifaires (Admin)"
)
def list_plans_admin(
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Retourne l'ensemble des plans tarifaires, y compris ceux non listés publiquement.
    Réservé aux administrateurs.
    """
    return service.lister_plans_admin(db)

@router.post(
    "/plans",
    response_model=PlanOut,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouveau plan tarifaire (Admin)"
)
def create_plan(
    payload: AdminPlanCreate,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Crée une nouvelle offre commerciale (nom, tarifs, accès fonctionnels).
    Réservé aux administrateurs de niveau 2 minimum.
    Tracé dans l'AuditLog.
    """
    return service.creer_plan_admin(db, admin=current_admin, payload=payload, request=request)

@router.put(
    "/plans/{id_plan}",
    response_model=PlanOut,
    summary="Modifier un plan tarifaire existant (Admin)"
)
def update_plan(
    id_plan: int,
    payload: AdminPlanUpdate,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Modifie la tarification ou les accès fonctionnels d'un plan (le nom des
    plans système GRATUIT/ESSENTIEL/PREMIUM ne peut pas être changé).
    Réservé aux administrateurs de niveau 2 minimum.
    Tracé dans l'AuditLog.
    """
    return service.modifier_plan_admin(db, admin=current_admin, id_plan=id_plan, payload=payload, request=request)

@router.delete(
    "/plans/{id_plan}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un plan tarifaire (Admin)"
)
def delete_plan(
    id_plan: int,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Supprime un plan n'ayant plus aucun abonné ni historique de paiement.
    Les plans système (GRATUIT, ESSENTIEL, PREMIUM) ne peuvent jamais être supprimés.
    Réservé aux administrateurs de niveau 2 minimum.
    Tracé dans l'AuditLog.
    """
    service.supprimer_plan_admin(db, admin=current_admin, id_plan=id_plan, request=request)

# --- Endpoints Gestion des Abonnements & Paiements ---

@router.get(
    "/abonnements/overview",
    response_model=AdminAbonnementOverview,
    summary="Vue d'ensemble et métriques financières des abonnements (Admin)"
)
def get_abonnements_overview(
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Retourne la synthèse des abonnés par plan, la répartition des statuts et le chiffre d'affaires total encaissé.
    Réservé aux administrateurs.
    """
    return service.obtenir_overview_abonnements_admin(db)

@router.get(
    "/abonnements",
    response_model=AdminAbonnementListResponse,
    summary="Lister et filtrer les abonnements clients (Admin)"
)
def list_abonnements(
    q: Optional[str] = Query(None, description="Recherche par email ou nom de client"),
    id_plan: Optional[int] = Query(None, description="Filtre par ID de plan tarifaire"),
    statut: Optional[str] = Query(None, description="Filtre par statut (ESSAI, ACTIF, EXPIRE, ANNULE)"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Consulter et filtrer la liste paginée de tous les abonnements clients.
    Réservé aux administrateurs.
    """
    return service.lister_abonnements_admin(
        db, q=q, id_plan=id_plan, statut=statut, page=page, page_size=page_size
    )

@router.get(
    "/paiements",
    response_model=AdminPaiementListResponse,
    summary="Lister et filtrer l'historique des paiements HR-Skills Pay (Admin)"
)
def list_paiements(
    q: Optional[str] = Query(None, description="Recherche par email client ou référence HR-Skills Pay"),
    statut: Optional[str] = Query(None, description="Filtre par statut de paiement (PENDING, SUCCESS, FAILED)"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Consulter l'historique des paiements Mobile Money de souscription d'abonnement.
    Réservé aux administrateurs.
    """
    return service.lister_paiements_admin(
        db, q=q, statut=statut, page=page, page_size=page_size
    )

@router.post(
    "/clients/{id_client}/abonnement/forcer",
    response_model=AdminAbonnementItem,
    summary="Forcer ou attribuer un plan d'abonnement à un client (Admin)"
)
def force_abonnement(
    id_client: int,
    payload: AdminForceAbonnementPayload,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Bascule manuellement le plan d'abonnement d'un client (support, litige, geste commercial).
    Réservé aux administrateurs de niveau 2 minimum.
    Tracé dans l'AuditLog.
    """
    return service.forcer_abonnement_client_admin(
        db, admin=current_admin, id_client=id_client, payload=payload, request=request
    )

@router.post(
    "/paiements/{id_paiement}/valider-manuel",
    response_model=AdminPaiementItem,
    summary="Valider manuellement un paiement Mobile Money en litige (Admin)"
)
def validate_paiement_manuel(
    id_paiement: int,
    payload: AdminValiderPaiementManuelPayload,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Valide manuellement un paiement bloqué en PENDING et applique le plan correspondant au client.
    Réservé aux administrateurs de niveau 2 minimum.
    Tracé dans l'AuditLog.
    """
    return service.valider_paiement_manuel_admin(
        db, admin=current_admin, id_paiement=id_paiement, payload=payload, request=request
    )

# --- Endpoints Surveillance Anti-Fraude ---

@router.get(
    "/fraude/overview",
    response_model=AdminFraudeOverview,
    summary="Vue d'ensemble et métriques de la surveillance anti-fraude (Admin)"
)
def get_fraude_overview(
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Retourne la synthèse des transactions suspectes, le nombre de clients concernés et le montant cumulé en risque.
    Réservé aux administrateurs.
    """
    return service.obtenir_overview_fraude_admin(db)

@router.get(
    "/fraude/transactions",
    response_model=AdminTransactionSuspecteListResponse,
    summary="Lister et filtrer les transactions suspectes (Admin)"
)
def list_transactions_suspectes(
    q: Optional[str] = Query(None, description="Recherche par email, nom de client ou description"),
    est_suspecte: Optional[bool] = Query(True, description="Filtre sur le statut de suspicion (par défaut True)"),
    type: Optional[str] = Query(None, description="Filtre par type (DEPENSE, REVENU, etc.)"),
    montant_min: Optional[Decimal] = Query(None, description="Montant minimum"),
    montant_max: Optional[Decimal] = Query(None, description="Montant maximum"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Consulter, filtrer et rechercher les transactions signalées comme atypiques ou suspectes.
    Réservé aux administrateurs.
    """
    return service.lister_transactions_suspectes_admin(
        db,
        q=q,
        est_suspecte=est_suspecte,
        type=type,
        montant_min=montant_min,
        montant_max=montant_max,
        page=page,
        page_size=page_size,
    )

@router.get(
    "/fraude/transactions/{id_transaction}",
    response_model=AdminTransactionSuspecteDetail,
    summary="Fiche d'investigation d'une transaction suspecte (Admin)"
)
def get_transaction_suspecte_detail(
    id_transaction: int,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Retourne le détail d'une transaction suspecte et l'historique du comportement financier du client.
    Réservé aux administrateurs.
    """
    return service.obtenir_detail_transaction_suspecte_admin(db, id_transaction=id_transaction)

@router.patch(
    "/fraude/transactions/{id_transaction}/statut",
    response_model=AdminTransactionSuspecteItem,
    summary="Marquer ou lever la suspicion d'une transaction (Admin)"
)
def update_transaction_suspicion_status(
    id_transaction: int,
    payload: AdminUpdateSuspicionPayload,
    request: Request,
    current_admin: Administrateur = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """
    Modifie le flag de suspicion d'une transaction (lever la suspicion ou la marquer comme suspecte).
    Réservé aux administrateurs de niveau 2 minimum (Modérateurs / Superadmins).
    Tracé dans l'AuditLog.
    """
    return service.modifier_statut_suspicion_admin(
        db, admin=current_admin, id_transaction=id_transaction, payload=payload, request=request
    )
