import secrets
import string
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, Request, status
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.modules.admin.schemas import (
    ActionPopularItem,
    AdminAbonnementItem,
    AdminAbonnementListResponse,
    AdminAbonnementOverview,
    AdminAbonnementsKPIs,
    AdminClientDetail,
    AdminClientListItem,
    AdminClientListResponse,
    AdminClientsKPIs,
    AdminClientStatusUpdate,
    AdminCreate,
    AdminFinancesKPIs,
    AdminForceAbonnementPayload,
    AdminFraudeOverview,
    AdminGlobalKPIsResponse,
    AdminLevelUpdate,
    AdminListItem,
    AdminPaiementItem,
    AdminPaiementListResponse,
    AdminResetPasswordResponse,
    AdminSecuriteKPIs,
    AdminStatusUpdate,
    AdminTransactionSuspecteDetail,
    AdminTransactionSuspecteItem,
    AdminTransactionSuspecteListResponse,
    AdminUpdateSuspicionPayload,
    AdminValiderPaiementManuelPayload,
    AuditLogDetail,
    AuditLogListItem,
    AuditLogListResponse,
    AuditStatsResponse,
    ConfigItem,
    ConfigUpdate,
    PlanCountItem,
    StatutCountItem,
    TypeTransactionCountItem,
)
from app.modules.audit.models import AuditLog, Config
from app.modules.audit.service import _deserialiser, enregistrer_action, set_config
from app.modules.auth.models import Administrateur, Client, RefreshToken, Utilisateur
from app.modules.budgets.models import Categorie
from app.modules.comptes.models import CompteFinancier, ComptePrincipal
from app.modules.dettes.models import Dette
from app.modules.plans import service as plans_service
from app.modules.plans.models import Abonnement, PaiementAbonnement, Plan
from app.modules.transactions.models import Transaction

# --- Services de Gestion des Clients ---

def lister_clients_admin(
    db: Session,
    q: Optional[str] = None,
    est_actif: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> AdminClientListResponse:
    """
    Recherche et liste paginée des clients pour l'espace administrateur.
    """
    query = db.query(Client)

    # Filtre par recherche textuelle (email, prénom, nom, téléphone)
    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Client.email.ilike(search_pattern),
                Client.first_name.ilike(search_pattern),
                Client.last_name.ilike(search_pattern),
                Client.phone.ilike(search_pattern),
            )
        )

    # Filtre par statut d'activité
    if est_actif is not None:
        query = query.filter(Client.est_actif == est_actif)

    total = query.count()
    offset = (page - 1) * page_size
    clients = query.order_by(Client.date_creation.desc()).offset(offset).limit(page_size).all()

    items = []
    for client in clients:
        solde = Decimal("0.00")
        if client.compte_principal and client.compte_principal.solde_total is not None:
            solde = Decimal(str(client.compte_principal.solde_total))

        plan = "GRATUIT"
        if hasattr(client, "abonnement") and client.abonnement and hasattr(client.abonnement, "plan"):
            plan = client.abonnement.plan.nom

        items.append(
            AdminClientListItem(
                id_client=client.id_client,
                email=client.email,
                first_name=client.first_name,
                last_name=client.last_name,
                phone=client.phone,
                est_actif=client.est_actif,
                date_creation=client.date_creation,
                solde_compte_principal=solde,
                plan_abonnement=plan,
            )
        )

    return AdminClientListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )

def obtenir_detail_client_admin(db: Session, id_client: int) -> AdminClientDetail:
    """
    Récupère la fiche détaillée d'un client avec ses métriques et statistiques financières.
    """
    client = db.query(Client).filter(Client.id_client == id_client).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client introuvable."
        )

    solde = Decimal("0.00")
    if client.compte_principal and client.compte_principal.solde_total is not None:
        solde = Decimal(str(client.compte_principal.solde_total))

    nb_comptes = db.query(func.count(CompteFinancier.id_compte)).filter(
        CompteFinancier.id_client == id_client
    ).scalar() or 0

    nb_tx = db.query(func.count(Transaction.id_transaction)).filter(
        Transaction.id_client == id_client
    ).scalar() or 0

    nb_dettes = db.query(func.count(Dette.id_dette)).filter(
        Dette.id_client == id_client,
        Dette.statut != "SOLDE"
    ).scalar() or 0

    plan = "GRATUIT"
    if hasattr(client, "abonnement") and client.abonnement and hasattr(client.abonnement, "plan"):
        plan = client.abonnement.plan.nom

    return AdminClientDetail(
        id_client=client.id_client,
        email=client.email,
        first_name=client.first_name,
        last_name=client.last_name,
        phone=client.phone,
        est_actif=client.est_actif,
        date_creation=client.date_creation,
        date_modification=client.date_modification,
        solde_compte_principal=solde,
        nombre_comptes_financiers=nb_comptes,
        nombre_transactions=nb_tx,
        nombre_dettes_actives=nb_dettes,
        plan_abonnement=plan,
    )

def changer_statut_client(
    db: Session,
    admin: Administrateur,
    id_client: int,
    payload: AdminClientStatusUpdate,
    request: Optional[Request] = None,
) -> Client:
    """
    Active ou désactive le compte d'un client.
    Si le compte est désactivé, révoque immédiatement tous ses refresh tokens de session.
    Tracé dans l'AuditLog.
    """
    client = db.query(Client).filter(Client.id_client == id_client).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client introuvable."
        )

    donnees_avant = {"est_actif": client.est_actif}
    client.est_actif = payload.est_actif

    # Si désactivation : révocation immédiate de tous ses tokens de rafraîchissement
    if not payload.est_actif:
        db.query(RefreshToken).filter(
            RefreshToken.id_client == id_client,
            RefreshToken.est_revoque == False
        ).update({"est_revoque": True})

    db.commit()
    db.refresh(client)

    action_name = "ADMIN_DESACTIVER_CLIENT" if not payload.est_actif else "ADMIN_ACTIVER_CLIENT"
    enregistrer_action(
        db,
        id_utilisateur=admin.id_administrateur,
        action=action_name,
        ressource="CLIENT",
        id_ressource=client.id_client,
        donnees_avant=donnees_avant,
        donnees_apres={"est_actif": client.est_actif, "raison": payload.raison},
        request=request,
    )

    return client

def reinitialiser_mot_de_passe_client(
    db: Session,
    admin: Administrateur,
    id_client: int,
    request: Optional[Request] = None,
) -> AdminResetPasswordResponse:
    """
    Génère un mot de passe temporaire sécurisé pour un client et révoque ses sessions.
    Tracé dans l'AuditLog.
    """
    client = db.query(Client).filter(Client.id_client == id_client).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client introuvable."
        )

    # Génération d'un mot de passe temporaire lisible et sécurisé
    caracteres = string.ascii_letters + string.digits
    tmp_password = "MyNkap#" + "".join(secrets.choice(caracteres) for _ in range(8))

    client.mot_de_passe = get_password_hash(tmp_password)

    # Révocation des sessions actives
    db.query(RefreshToken).filter(
        RefreshToken.id_client == id_client,
        RefreshToken.est_revoque == False
    ).update({"est_revoque": True})

    db.commit()

    enregistrer_action(
        db,
        id_utilisateur=admin.id_administrateur,
        action="ADMIN_REINITIALISER_MDP_CLIENT",
        ressource="CLIENT",
        id_ressource=client.id_client,
        donnees_avant=None,
        donnees_apres={"email": client.email},
        request=request,
    )

    return AdminResetPasswordResponse(
        id_client=client.id_client,
        email=client.email,
        mot_de_passe_temporaire=tmp_password,
        message="Le mot de passe a été réinitialisé avec succès et toutes les sessions du client ont été révoquées."
    )

# --- Services de Gestion des Administrateurs ---

def lister_administrateurs_admin(db: Session) -> List[Administrateur]:
    """
    Lister l'ensemble des administrateurs de la plateforme.
    """
    return db.query(Administrateur).order_by(
        Administrateur.niveau_acces.desc(),
        Administrateur.date_creation.desc()
    ).all()

def creer_administrateur_admin(
    db: Session,
    admin_createur: Administrateur,
    schema: AdminCreate,
    request: Optional[Request] = None,
) -> Administrateur:
    """
    Crée un nouvel administrateur avec un niveau d'accès défini.
    Garde-fous : 
    - Seul un admin de niveau_acces >= 2 peut créer d'autres admins.
    - Un admin de niveau 2 ne peut pas créer un Superadmin (niveau 3).
    - Email et username uniques.
    Tracé dans l'AuditLog.
    """
    if admin_createur.niveau_acces < 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé : droits insuffisants (niveau 2 minimum requis pour créer un administrateur)."
        )

    if admin_createur.niveau_acces == 2 and schema.niveau_acces > 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un modérateur (niveau 2) ne peut pas créer un Superadmin (niveau 3)."
        )

    # Vérification d'unicité de l'email sur Utilisateur
    if db.query(Utilisateur).filter(Utilisateur.email == schema.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet adresse email existe déjà."
        )

    # Vérification d'unicité du username sur Administrateur
    if db.query(Administrateur).filter(Administrateur.username == schema.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur administrateur est déjà utilisé."
        )

    nouveau_admin = Administrateur(
        email=schema.email,
        username=schema.username,
        mot_de_passe=get_password_hash(schema.mot_de_passe),
        niveau_acces=schema.niveau_acces,
        est_actif=True,
    )
    db.add(nouveau_admin)
    db.commit()
    db.refresh(nouveau_admin)

    enregistrer_action(
        db,
        id_utilisateur=admin_createur.id_administrateur,
        action="ADMIN_CREER_ADMIN",
        ressource="ADMINISTRATEUR",
        id_ressource=nouveau_admin.id_administrateur,
        donnees_avant=None,
        donnees_apres={
            "email": nouveau_admin.email,
            "username": nouveau_admin.username,
            "niveau_acces": nouveau_admin.niveau_acces,
        },
        request=request,
    )

    return nouveau_admin

def modifier_niveau_acces_admin(
    db: Session,
    admin_modificateur: Administrateur,
    id_target_admin: int,
    schema: AdminLevelUpdate,
    request: Optional[Request] = None,
) -> Administrateur:
    """
    Modifie le niveau d'accès d'un administrateur.
    Garde-fous : 
    - Seul un Superadmin (niveau 3) peut modifier les niveaux d'accès.
    - Protection du dernier Superadmin actif de la plateforme.
    Tracé dans l'AuditLog.
    """
    if admin_modificateur.niveau_acces < 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un Superadmin (niveau 3) peut modifier le niveau d'accès d'un administrateur."
        )

    target_admin = db.query(Administrateur).filter(Administrateur.id_administrateur == id_target_admin).first()
    if not target_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrateur introuvable."
        )

    # Garde-fou : Protection du dernier Superadmin actif contre la rétrogradation
    if target_admin.niveau_acces == 3 and target_admin.est_actif and schema.niveau_acces < 3:
        superadmins_actifs = db.query(func.count(Administrateur.id_administrateur)).filter(
            Administrateur.niveau_acces == 3,
            Administrateur.est_actif == True
        ).scalar() or 0

        if superadmins_actifs <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de rétrograder le dernier Superadmin actif de la plateforme."
            )

    donnees_avant = {"niveau_acces": target_admin.niveau_acces}
    target_admin.niveau_acces = schema.niveau_acces

    db.commit()
    db.refresh(target_admin)

    enregistrer_action(
        db,
        id_utilisateur=admin_modificateur.id_administrateur,
        action="ADMIN_MODIFIER_NIVEAU_ACCES",
        ressource="ADMINISTRATEUR",
        id_ressource=target_admin.id_administrateur,
        donnees_avant=donnees_avant,
        donnees_apres={"niveau_acces": target_admin.niveau_acces},
        request=request,
    )

    return target_admin

def changer_statut_administrateur(
    db: Session,
    admin_modificateur: Administrateur,
    id_target_admin: int,
    schema: AdminStatusUpdate,
    request: Optional[Request] = None,
) -> Administrateur:
    """
    Activer ou désactiver le compte d'un administrateur.
    Garde-fous : 
    - Seul un Superadmin (niveau 3) peut désactiver un administrateur.
    - Interdiction pour un admin de désactiver son propre compte.
    - Protection du dernier Superadmin actif contre la désactivation.
    Tracé dans l'AuditLog.
    """
    if admin_modificateur.niveau_acces < 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un Superadmin (niveau 3) peut modifier le statut d'un administrateur."
        )

    target_admin = db.query(Administrateur).filter(Administrateur.id_administrateur == id_target_admin).first()
    if not target_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrateur introuvable."
        )

    # Garde-fou 1 : Interdiction d'auto-suspension
    if target_admin.id_administrateur == admin_modificateur.id_administrateur and not schema.est_actif:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas désactiver votre propre compte administrateur."
        )

    # Garde-fou 2 : Protection du dernier Superadmin actif
    if not schema.est_actif and target_admin.niveau_acces == 3 and target_admin.est_actif:
        superadmins_actifs = db.query(func.count(Administrateur.id_administrateur)).filter(
            Administrateur.niveau_acces == 3,
            Administrateur.est_actif == True
        ).scalar() or 0

        if superadmins_actifs <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de désactiver le dernier Superadmin actif de la plateforme."
            )

    donnees_avant = {"est_actif": target_admin.est_actif}
    target_admin.est_actif = schema.est_actif

    db.commit()
    db.refresh(target_admin)

    action_name = "ADMIN_DESACTIVER_ADMIN" if not schema.est_actif else "ADMIN_ACTIVER_ADMIN"
    enregistrer_action(
        db,
        id_utilisateur=admin_modificateur.id_administrateur,
        action=action_name,
        ressource="ADMINISTRATEUR",
        id_ressource=target_admin.id_administrateur,
        donnees_avant=donnees_avant,
        donnees_apres={"est_actif": target_admin.est_actif, "raison": schema.raison},
        request=request,
    )

    return target_admin

# --- Services d'Audit Global ---

def lister_audit_logs_admin(
    db: Session,
    id_utilisateur: Optional[int] = None,
    action: Optional[str] = None,
    ressource: Optional[str] = None,
    id_ressource: Optional[int] = None,
    date_debut: Optional[datetime] = None,
    date_fin: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> AuditLogListResponse:
    """
    Lister et filtrer les journaux d'audit de la plateforme avec pagination.
    """
    query = db.query(AuditLog, Utilisateur.email, Utilisateur.type).outerjoin(
        Utilisateur, AuditLog.id_utilisateur == Utilisateur.id_utilisateur
    )

    if id_utilisateur is not None:
        query = query.filter(AuditLog.id_utilisateur == id_utilisateur)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action.strip()}%"))
    if ressource:
        query = query.filter(AuditLog.ressource.ilike(f"%{ressource.strip()}%"))
    if id_ressource is not None:
        query = query.filter(AuditLog.id_ressource == id_ressource)
    if date_debut:
        query = query.filter(AuditLog.date_creation >= date_debut)
    if date_fin:
        query = query.filter(AuditLog.date_creation <= date_fin)

    total = query.count()
    offset = (page - 1) * page_size
    results = query.order_by(AuditLog.date_creation.desc()).offset(offset).limit(page_size).all()

    items = []
    for log, email, user_type in results:
        items.append(
            AuditLogListItem(
                id_audit=log.id_audit,
                id_utilisateur=log.id_utilisateur,
                email_utilisateur=email,
                type_utilisateur=user_type,
                action=log.action,
                ressource=log.ressource,
                id_ressource=log.id_ressource,
                adresse_ip=log.adresse_ip,
                user_agent=log.user_agent,
                date_creation=log.date_creation,
            )
        )

    return AuditLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )

def obtenir_detail_audit_log_admin(db: Session, id_audit: int) -> AuditLogDetail:
    """
    Récupère le détail d'une entrée d'audit avec ses structures JSON donnees_avant et donnees_apres.
    """
    result = db.query(AuditLog, Utilisateur.email, Utilisateur.type).outerjoin(
        Utilisateur, AuditLog.id_utilisateur == Utilisateur.id_utilisateur
    ).filter(AuditLog.id_audit == id_audit).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrée d'audit introuvable."
        )

    log, email, user_type = result
    return AuditLogDetail(
        id_audit=log.id_audit,
        id_utilisateur=log.id_utilisateur,
        email_utilisateur=email,
        type_utilisateur=user_type,
        action=log.action,
        ressource=log.ressource,
        id_ressource=log.id_ressource,
        donnees_avant=log.donnees_avant,
        donnees_apres=log.donnees_apres,
        adresse_ip=log.adresse_ip,
        user_agent=log.user_agent,
        date_creation=log.date_creation,
    )

def obtenir_statistiques_audit_admin(db: Session) -> AuditStatsResponse:
    """
    Retourne les métriques et la répartition des actions les plus fréquentes dans l'AuditLog.
    """
    total_logs = db.query(func.count(AuditLog.id_audit)).scalar() or 0

    action_counts = db.query(
        AuditLog.action, func.count(AuditLog.id_audit).label("count")
    ).group_by(AuditLog.action).order_by(func.count(AuditLog.id_audit).desc()).limit(10).all()

    repartition = [ActionPopularItem(action=row[0], count=row[1]) for row in action_counts]

    return AuditStatsResponse(
        total_logs=total_logs,
        repartition_actions=repartition
    )

# --- Services de Configuration Système ---

def _format_config_item(config: Config) -> ConfigItem:
    parsed = _deserialiser(config)
    return ConfigItem(
        id_config=config.id_config,
        cle=config.cle,
        valeur=config.valeur,
        valeur_parsed=parsed,
        type=config.type,
        description=config.description,
        date_modification=config.date_modification,
    )

def lister_configs_admin(db: Session) -> List[ConfigItem]:
    """
    Lister l'ensemble des paramètres de configuration applicative.
    """
    configs = db.query(Config).order_by(Config.cle.asc()).all()
    return [_format_config_item(cfg) for cfg in configs]

def obtenir_config_admin(db: Session, cle: str) -> ConfigItem:
    """
    Consulter la valeur d'une clé de configuration spécifique.
    """
    config = db.query(Config).filter(Config.cle == cle.strip()).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paramètre de configuration '{cle}' introuvable."
        )
    return _format_config_item(config)

def modifier_config_admin(
    db: Session,
    admin: Administrateur,
    cle: str,
    payload: ConfigUpdate,
    request: Optional[Request] = None,
) -> ConfigItem:
    """
    Crée ou met à jour un paramètre de configuration à chaud.
    Garde-fous : Réservé aux administrateurs de niveau_acces >= 2.
    Tracé dans l'AuditLog.
    """
    if admin.niveau_acces < 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé : droits insuffisants pour modifier la configuration système (niveau 2 minimum requis)."
        )

    config_existant = db.query(Config).filter(Config.cle == cle.strip()).first()
    donnees_avant = None
    if config_existant:
        donnees_avant = {
            "valeur": config_existant.valeur,
            "type": config_existant.type,
            "description": config_existant.description,
        }

    # Déterminer le type déclaratif
    type_declare = payload.type or (config_existant.type if config_existant else "STRING")

    config_maj = set_config(
        db,
        cle=cle.strip(),
        valeur=payload.valeur,
        type_=type_declare,
        description=payload.description,
    )

    donnees_apres = {
        "valeur": config_maj.valeur,
        "type": config_maj.type,
        "description": config_maj.description,
    }

    enregistrer_action(
        db,
        id_utilisateur=admin.id_administrateur,
        action="ADMIN_MODIFIER_CONFIG",
        ressource="CONFIG",
        id_ressource=config_maj.id_config,
        donnees_avant=donnees_avant,
        donnees_apres=donnees_apres,
        request=request,
    )

    return _format_config_item(config_maj)

# --- Services de Gestion des Abonnements & Paiements ---

def obtenir_overview_abonnements_admin(db: Session) -> AdminAbonnementOverview:
    """
    Calcule la vue d'ensemble des abonnements clients, la répartition par plan/statut et les revenus totaux.
    """
    total_abonnements = db.query(func.count(Abonnement.id_abonnement)).scalar() or 0

    # Répartition par plan
    plans_counts = db.query(
        Plan.nom, func.count(Abonnement.id_abonnement).label("count")
    ).outerjoin(Abonnement, Plan.id_plan == Abonnement.id_plan).group_by(Plan.nom).all()

    repartition_plans = [PlanCountItem(nom_plan=row[0], nombre_abonnes=row[1]) for row in plans_counts]

    # Répartition par statut
    statuts_counts = db.query(
        Abonnement.statut, func.count(Abonnement.id_abonnement).label("count")
    ).group_by(Abonnement.statut).all()

    repartition_statuts = [StatutCountItem(statut=row[0], count=row[1]) for row in statuts_counts]

    # Total chiffre d'affaires (somme des paiements SUCCESS)
    ca_total = db.query(func.sum(PaiementAbonnement.montant)).filter(
        PaiementAbonnement.statut == "SUCCESS"
    ).scalar() or Decimal("0.00")

    return AdminAbonnementOverview(
        total_abonnes=total_abonnements,
        repartition_plans=repartition_plans,
        repartition_statuts=repartition_statuts,
        chiffre_affaires_total=Decimal(str(ca_total)),
    )

def lister_abonnements_admin(
    db: Session,
    q: Optional[str] = None,
    id_plan: Optional[int] = None,
    statut: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> AdminAbonnementListResponse:
    """
    Lister et filtrer les abonnements clients de la plateforme avec pagination.
    """
    query = db.query(Abonnement, Client.email, Client.first_name, Client.last_name, Plan.nom).join(
        Client, Abonnement.id_client == Client.id_client
    ).join(Plan, Abonnement.id_plan == Plan.id_plan)

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Client.email.ilike(search_pattern),
                Client.first_name.ilike(search_pattern),
                Client.last_name.ilike(search_pattern),
            )
        )
    if id_plan is not None:
        query = query.filter(Abonnement.id_plan == id_plan)
    if statut:
        query = query.filter(Abonnement.statut.ilike(f"%{statut.strip()}%"))

    total = query.count()
    offset = (page - 1) * page_size
    results = query.order_by(Abonnement.date_creation.desc()).offset(offset).limit(page_size).all()

    items = []
    for ab, email, fn, ln, nom_plan in results:
        items.append(
            AdminAbonnementItem(
                id_abonnement=ab.id_abonnement,
                id_client=ab.id_client,
                email_client=email,
                nom_client=f"{fn} {ln}".strip(),
                nom_plan=nom_plan,
                cycle_facturation=ab.cycle_facturation,
                statut=ab.statut,
                date_debut=ab.date_debut,
                date_fin=ab.date_fin,
                renouvellement_auto=ab.renouvellement_auto,
            )
        )

    return AdminAbonnementListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )

def lister_paiements_admin(
    db: Session,
    q: Optional[str] = None,
    statut: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> AdminPaiementListResponse:
    """
    Lister et filtrer l'historique des paiements de souscription Mobile Money (HR-Skills Pay).
    """
    query = db.query(PaiementAbonnement, Client.email, Plan.nom).join(
        Client, PaiementAbonnement.id_client == Client.id_client
    ).join(Plan, PaiementAbonnement.id_plan_demande == Plan.id_plan)

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Client.email.ilike(search_pattern),
                PaiementAbonnement.reference_hrpay.ilike(search_pattern),
            )
        )
    if statut:
        query = query.filter(PaiementAbonnement.statut.ilike(f"%{statut.strip()}%"))

    total = query.count()
    offset = (page - 1) * page_size
    results = query.order_by(PaiementAbonnement.date_creation.desc()).offset(offset).limit(page_size).all()

    items = []
    for p, email, nom_plan in results:
        items.append(
            AdminPaiementItem(
                id_paiement=p.id_paiement,
                id_client=p.id_client,
                email_client=email,
                nom_plan_demande=nom_plan,
                cycle_facturation=p.cycle_facturation,
                montant=Decimal(str(p.montant)),
                devise=p.devise,
                reference_hrpay=p.reference_hrpay,
                statut=p.statut,
                date_creation=p.date_creation,
                date_confirmation=p.date_confirmation,
            )
        )

    return AdminPaiementListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )

def forcer_abonnement_client_admin(
    db: Session,
    admin: Administrateur,
    id_client: int,
    payload: AdminForceAbonnementPayload,
    request: Optional[Request] = None,
) -> AdminAbonnementItem:
    """
    Attribue ou force manuellement un plan d'abonnement pour un client (support, litige, offre commerciale).
    Garde-fous : Réservé aux administrateurs niveau 2+.
    Tracé dans l'AuditLog.
    """
    if admin.niveau_acces < 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé : droits insuffisants pour forcer un abonnement (niveau 2 minimum requis)."
        )

    client = db.query(Client).filter(Client.id_client == id_client).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable.")

    plan_cible = db.query(Plan).filter(Plan.id_plan == payload.id_plan).first()
    if not plan_cible:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan introuvable.")

    ab = db.query(Abonnement).filter(Abonnement.id_client == id_client).first()
    donnees_avant = None
    if ab:
        donnees_avant = {
            "id_plan": ab.id_plan,
            "statut": ab.statut,
            "cycle_facturation": ab.cycle_facturation,
            "date_fin": ab.date_fin.isoformat() if ab.date_fin else None,
        }
    else:
        ab = Abonnement(id_client=id_client, id_plan=plan_cible.id_plan)
        db.add(ab)

    # Ne réutilise pas plans_service.changer_plan() ici : ce point d'entrée
    # admin a besoin d'une flexibilité que la fonction standard n'offre
    # pas (statut et durée arbitraires pour un geste commercial ou un
    # litige) — mais on aligne le reste du comportement sur elle pour
    # éviter toute divergence silencieuse (renouvellement_auto, date_debut).
    ab.id_plan = plan_cible.id_plan
    ab.statut = payload.statut
    ab.cycle_facturation = payload.cycle_facturation
    ab.date_debut = datetime.utcnow()
    ab.renouvellement_auto = True

    # Calcul de date_fin selon la durée passée
    if plan_cible.nom == "GRATUIT":
        ab.date_fin = None
        ab.cycle_facturation = None
    else:
        duree = payload.duree_jours or 30
        ab.date_fin = datetime.utcnow() + timedelta(days=duree)

    db.commit()
    db.refresh(ab)

    enregistrer_action(
        db,
        id_utilisateur=admin.id_administrateur,
        action="ADMIN_FORCER_ABONNEMENT",
        ressource="ABONNEMENT",
        id_ressource=ab.id_abonnement,
        donnees_avant=donnees_avant,
        donnees_apres={
            "id_plan": ab.id_plan,
            "statut": ab.statut,
            "cycle_facturation": ab.cycle_facturation,
            "date_fin": ab.date_fin.isoformat() if ab.date_fin else None,
            "raison": payload.raison,
        },
        request=request,
    )

    return AdminAbonnementItem(
        id_abonnement=ab.id_abonnement,
        id_client=client.id_client,
        email_client=client.email,
        nom_client=f"{client.first_name} {client.last_name}".strip(),
        nom_plan=plan_cible.nom,
        cycle_facturation=ab.cycle_facturation,
        statut=ab.statut,
        date_debut=ab.date_debut,
        date_fin=ab.date_fin,
        renouvellement_auto=ab.renouvellement_auto,
    )

def valider_paiement_manuel_admin(
    db: Session,
    admin: Administrateur,
    id_paiement: int,
    payload: AdminValiderPaiementManuelPayload,
    request: Optional[Request] = None,
) -> AdminPaiementItem:
    """
    Valide manuellement un paiement bloqué en PENDING et applique le plan correspondant au client.
    Garde-fous : Réservé aux administrateurs niveau 2+.
    Tracé dans l'AuditLog.
    """
    if admin.niveau_acces < 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé : droits insuffisants pour valider un paiement (niveau 2 minimum requis)."
        )

    paiement = db.query(PaiementAbonnement).filter(PaiementAbonnement.id_paiement == id_paiement).first()
    if not paiement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paiement introuvable.")

    if paiement.statut == "SUCCESS":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce paiement a déjà été validé.")

    plan_demande = db.query(Plan).filter(Plan.id_plan == paiement.id_plan_demande).first()
    if not plan_demande:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan demandé introuvable.")

    donnees_avant = {"statut": paiement.statut}
    paiement.statut = "SUCCESS"
    paiement.date_confirmation = datetime.utcnow()

    # Réutilise la même logique que la confirmation automatique
    # (plans_service.verifier_paiements_en_attente) au lieu de réimplémenter
    # l'application du plan à la main : garantit que valider manuellement un
    # paiement produit exactement le même état d'abonnement que si
    # HR-Skills Pay avait confirmé le SUCCESS lui-même — aucune divergence
    # silencieuse possible entre les deux chemins.
    plans_service.changer_plan(db, paiement.id_client, plan_demande.nom, paiement.cycle_facturation)
    db.refresh(paiement)

    enregistrer_action(
        db,
        id_utilisateur=admin.id_administrateur,
        action="ADMIN_VALIDER_PAIEMENT_MANUEL",
        ressource="PAIEMENT_ABONNEMENT",
        id_ressource=paiement.id_paiement,
        donnees_avant=donnees_avant,
        donnees_apres={"statut": paiement.statut, "raison": payload.raison},
        request=request,
    )

    client = db.query(Client).filter(Client.id_client == paiement.id_client).first()

    return AdminPaiementItem(
        id_paiement=paiement.id_paiement,
        id_client=paiement.id_client,
        email_client=client.email if client else "inconnu@mynkap.cm",
        nom_plan_demande=plan_demande.nom if plan_demande else "INCONNU",
        cycle_facturation=paiement.cycle_facturation,
        montant=Decimal(str(paiement.montant)),
        devise=paiement.devise,
        reference_hrpay=paiement.reference_hrpay,
        statut=paiement.statut,
        date_creation=paiement.date_creation,
        date_confirmation=paiement.date_confirmation,
    )

# --- Services de Surveillance Anti-Fraude ---

def _format_transaction_suspecte_item(tx: Transaction, client: Client, compte: CompteFinancier, cat: Optional[Categorie] = None) -> AdminTransactionSuspecteItem:
    return AdminTransactionSuspecteItem(
        id_transaction=tx.id_transaction,
        id_client=tx.id_client,
        email_client=client.email,
        nom_client=f"{client.first_name} {client.last_name}".strip(),
        nom_compte=compte.nom if compte else "Inconnu",
        nom_categorie=cat.nom if cat else None,
        montant=Decimal(str(tx.montant)),
        type=tx.type,
        description=tx.description,
        date=tx.date.strftime("%Y-%m-%d") if tx.date else "",
        est_suspecte=tx.est_suspecte,
        date_creation=tx.date_creation,
    )

def obtenir_overview_fraude_admin(db: Session) -> AdminFraudeOverview:
    """
    Calcule le nombre de transactions suspectes, le nombre de clients concernés et le montant global à risque.
    """
    query = db.query(Transaction).filter(Transaction.est_suspecte == True)

    total_suspectes = query.count()
    clients_concernes = db.query(func.count(func.distinct(Transaction.id_client))).filter(
        Transaction.est_suspecte == True
    ).scalar() or 0

    montant_total = db.query(func.sum(Transaction.montant)).filter(
        Transaction.est_suspecte == True
    ).scalar() or Decimal("0.00")

    counts = db.query(
        Transaction.type, func.count(Transaction.id_transaction).label("count")
    ).filter(Transaction.est_suspecte == True).group_by(Transaction.type).all()

    repartition = [TypeTransactionCountItem(type=row[0], count=row[1]) for row in counts]

    return AdminFraudeOverview(
        total_transactions_suspectes=total_suspectes,
        nombre_clients_concernes=clients_concernes,
        montant_total_suspect=Decimal(str(montant_total)),
        repartition_par_type=repartition,
    )

def lister_transactions_suspectes_admin(
    db: Session,
    q: Optional[str] = None,
    est_suspecte: Optional[bool] = True,
    type: Optional[str] = None,
    montant_min: Optional[Decimal] = None,
    montant_max: Optional[Decimal] = None,
    page: int = 1,
    page_size: int = 20,
) -> AdminTransactionSuspecteListResponse:
    """
    Lister et filtrer les transactions suspectes ou examinées pour l'espace administrateur.
    """
    query = db.query(Transaction, Client, CompteFinancier, Categorie).join(
        Client, Transaction.id_client == Client.id_client
    ).join(
        CompteFinancier, Transaction.id_compte == CompteFinancier.id_compte
    ).outerjoin(
        Categorie, Transaction.id_categorie == Categorie.id_categorie
    )

    if est_suspecte is not None:
        query = query.filter(Transaction.est_suspecte == est_suspecte)
    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Client.email.ilike(search_pattern),
                Client.first_name.ilike(search_pattern),
                Client.last_name.ilike(search_pattern),
                Transaction.description.ilike(search_pattern),
            )
        )
    if type:
        query = query.filter(Transaction.type.ilike(f"%{type.strip()}%"))
    if montant_min is not None:
        query = query.filter(Transaction.montant >= montant_min)
    if montant_max is not None:
        query = query.filter(Transaction.montant <= montant_max)

    total = query.count()
    offset = (page - 1) * page_size
    results = query.order_by(Transaction.date_creation.desc()).offset(offset).limit(page_size).all()

    items = []
    for tx, client, compte, cat in results:
        items.append(_format_transaction_suspecte_item(tx, client, compte, cat))

    return AdminTransactionSuspecteListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )

def obtenir_detail_transaction_suspecte_admin(db: Session, id_transaction: int) -> AdminTransactionSuspecteDetail:
    """
    Récupère la fiche détaillée d'investigation d'une transaction suspecte.
    """
    result = db.query(Transaction, Client, CompteFinancier, Categorie).join(
        Client, Transaction.id_client == Client.id_client
    ).join(
        CompteFinancier, Transaction.id_compte == CompteFinancier.id_compte
    ).outerjoin(
        Categorie, Transaction.id_categorie == Categorie.id_categorie
    ).filter(Transaction.id_transaction == id_transaction).first()

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction introuvable.")

    tx, client, compte, cat = result

    total_tx_client = db.query(func.count(Transaction.id_transaction)).filter(
        Transaction.id_client == client.id_client
    ).scalar() or 0

    suspectes_client = db.query(func.count(Transaction.id_transaction)).filter(
        Transaction.id_client == client.id_client,
        Transaction.est_suspecte == True
    ).scalar() or 0

    solde = Decimal("0.00")
    if client.compte_principal and client.compte_principal.solde_total is not None:
        solde = Decimal(str(client.compte_principal.solde_total))

    base_item = _format_transaction_suspecte_item(tx, client, compte, cat)

    return AdminTransactionSuspecteDetail(
        **base_item.model_dump(),
        nombre_total_transactions_client=total_tx_client,
        nombre_transactions_suspectes_client=suspectes_client,
        solde_compte_principal=solde,
    )

def modifier_statut_suspicion_admin(
    db: Session,
    admin: Administrateur,
    id_transaction: int,
    payload: AdminUpdateSuspicionPayload,
    request: Optional[Request] = None,
) -> AdminTransactionSuspecteItem:
    """
    Marque ou lève manuellement la suspicion d'une transaction.
    Garde-fous : Réservé aux administrateurs de niveau_acces >= 2 (Modérateurs/Superadmins).
    Tracé dans l'AuditLog.
    """
    if admin.niveau_acces < 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé : droits insuffisants pour modifier le statut de suspicion (niveau 2 minimum requis)."
        )

    tx = db.query(Transaction).filter(Transaction.id_transaction == id_transaction).first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction introuvable.")

    donnees_avant = {"est_suspecte": tx.est_suspecte}
    tx.est_suspecte = payload.est_suspecte

    db.commit()
    db.refresh(tx)

    action_name = "ADMIN_MARQUER_SUSPECTE" if payload.est_suspecte else "ADMIN_LEVER_SUSPICION"
    enregistrer_action(
        db,
        id_utilisateur=admin.id_administrateur,
        action=action_name,
        ressource="TRANSACTION",
        id_ressource=tx.id_transaction,
        donnees_avant=donnees_avant,
        donnees_apres={"est_suspecte": tx.est_suspecte, "raison": payload.raison},
        request=request,
    )

    client = db.query(Client).filter(Client.id_client == tx.id_client).first()
    compte = db.query(CompteFinancier).filter(CompteFinancier.id_compte == tx.id_compte).first()
    cat = db.query(Categorie).filter(Categorie.id_categorie == tx.id_categorie).first() if tx.id_categorie else None

    return _format_transaction_suspecte_item(tx, client, compte, cat)

# --- Services Tableau de Bord KPI Globaux ---

def obtenir_kpis_globaux_admin(db: Session) -> AdminGlobalKPIsResponse:
    """
    Calcule et retourne la synthèse des indicateurs de performance clés (KPIs) de la plateforme.
    """
    # 1. KPIs Clients
    total_clients = db.query(func.count(Client.id_client)).scalar() or 0
    clients_actifs = db.query(func.count(Client.id_client)).filter(Client.est_actif == True).scalar() or 0
    clients_suspendus = db.query(func.count(Client.id_client)).filter(Client.est_actif == False).scalar() or 0
    
    il_y_a_30j = datetime.utcnow() - timedelta(days=30)
    nouveaux_30j = db.query(func.count(Client.id_client)).filter(Client.date_creation >= il_y_a_30j).scalar() or 0

    clients_kpis = AdminClientsKPIs(
        total_clients=total_clients,
        clients_actifs=clients_actifs,
        clients_suspendus=clients_suspendus,
        nouveaux_clients_30j=nouveaux_30j,
    )

    # 2. KPIs Finances
    ca_abonnements = db.query(func.sum(PaiementAbonnement.montant)).filter(
        PaiementAbonnement.statut == "SUCCESS"
    ).scalar() or Decimal("0.00")

    vol_tx = db.query(func.sum(Transaction.montant)).scalar() or Decimal("0.00")
    solde_comptes = db.query(func.sum(ComptePrincipal.solde_total)).scalar() or Decimal("0.00")

    finances_kpis = AdminFinancesKPIs(
        chiffre_affaires_abonnements=Decimal(str(ca_abonnements)),
        volume_total_transactions=Decimal(str(vol_tx)),
        solde_cumule_comptes_principaux=Decimal(str(solde_comptes)),
    )

    # 3. KPIs Abonnements
    total_ab = db.query(func.count(Abonnement.id_abonnement)).scalar() or 0
    
    ab_gratuit = db.query(func.count(Abonnement.id_abonnement)).join(
        Plan, Abonnement.id_plan == Plan.id_plan
    ).filter(Plan.nom == "GRATUIT").scalar() or 0

    ab_essentiel = db.query(func.count(Abonnement.id_abonnement)).join(
        Plan, Abonnement.id_plan == Plan.id_plan
    ).filter(Plan.nom == "ESSENTIEL").scalar() or 0

    ab_premium = db.query(func.count(Abonnement.id_abonnement)).join(
        Plan, Abonnement.id_plan == Plan.id_plan
    ).filter(Plan.nom == "PREMIUM").scalar() or 0

    taux_conv = 0.0
    if total_clients > 0:
        taux_conv = round(((ab_essentiel + ab_premium) / total_clients) * 100.0, 2)

    abonnements_kpis = AdminAbonnementsKPIs(
        total_abonnes=total_ab,
        abonnes_gratuit=ab_gratuit,
        abonnes_essentiel=ab_essentiel,
        abonnes_premium=ab_premium,
        taux_conversion_payant_pourcent=taux_conv,
    )

    # 4. KPIs Sécurité
    nb_suspectes = db.query(func.count(Transaction.id_transaction)).filter(
        Transaction.est_suspecte == True
    ).scalar() or 0

    m_suspect = db.query(func.sum(Transaction.montant)).filter(
        Transaction.est_suspecte == True
    ).scalar() or Decimal("0.00")

    total_logs = db.query(func.count(AuditLog.id_audit)).scalar() or 0

    securite_kpis = AdminSecuriteKPIs(
        transactions_suspectes_count=nb_suspectes,
        montant_total_suspect=Decimal(str(m_suspect)),
        total_audit_logs=total_logs,
    )

    return AdminGlobalKPIsResponse(
        clients=clients_kpis,
        finances=finances_kpis,
        abonnements=abonnements_kpis,
        securite=securite_kpis,
    )
