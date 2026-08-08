from datetime import datetime
from decimal import Decimal
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field

# --- Paramètres de filtre et pagination ---
class AdminClientFilterParams(BaseModel):
    q: Optional[str] = None
    est_actif: Optional[bool] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

# --- Vues de sortie des clients ---
class AdminClientListItem(BaseModel):
    id_client: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    est_actif: bool
    date_creation: datetime
    solde_compte_principal: Decimal = Decimal("0.00")
    plan_abonnement: str = "GRATUIT"

    class Config:
        from_attributes = True

class AdminClientListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AdminClientListItem]

class AdminClientDetail(BaseModel):
    id_client: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    est_actif: bool
    date_creation: datetime
    date_modification: datetime
    
    # Résumé financier & statistiques
    solde_compte_principal: Decimal = Decimal("0.00")
    nombre_comptes_financiers: int = 0
    nombre_transactions: int = 0
    nombre_dettes_actives: int = 0
    plan_abonnement: str = "GRATUIT"

    class Config:
        from_attributes = True

# --- Demande de changement de statut d'un client ---
class AdminClientStatusUpdate(BaseModel):
    est_actif: bool
    raison: Optional[str] = Field(None, description="Raison du changement de statut (tracée dans l'AuditLog)")

# --- Réponse de réinitialisation de mot de passe client ---
class AdminResetPasswordResponse(BaseModel):
    id_client: int
    email: EmailStr
    mot_de_passe_temporaire: str
    message: str

# --- Schémas pour la Gestion des Administrateurs ---
class AdminCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    mot_de_passe: str = Field(..., min_length=6)
    niveau_acces: int = Field(1, ge=1, le=3, description="1: Support, 2: Modérateur, 3: Superadmin")

class AdminListItem(BaseModel):
    id_administrateur: int
    email: EmailStr
    username: str
    niveau_acces: int
    est_actif: bool
    date_creation: datetime

    class Config:
        from_attributes = True

class AdminLevelUpdate(BaseModel):
    niveau_acces: int = Field(..., ge=1, le=3, description="1: Support, 2: Modérateur, 3: Superadmin")

class AdminStatusUpdate(BaseModel):
    est_actif: bool
    raison: Optional[str] = Field(None, description="Raison du changement de statut")

# --- Schémas pour l'Audit Global ---
class AuditLogListItem(BaseModel):
    id_audit: int
    id_utilisateur: int
    email_utilisateur: Optional[str] = None
    type_utilisateur: Optional[str] = None
    action: str
    ressource: str
    id_ressource: Optional[int] = None
    adresse_ip: Optional[str] = None
    user_agent: Optional[str] = None
    date_creation: datetime

    class Config:
        from_attributes = True

class AuditLogDetail(AuditLogListItem):
    donnees_avant: Optional[dict] = None
    donnees_apres: Optional[dict] = None

class AuditLogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AuditLogListItem]

class ActionPopularItem(BaseModel):
    action: str
    count: int

class AuditStatsResponse(BaseModel):
    total_logs: int
    repartition_actions: List[ActionPopularItem]

# --- Schémas pour la Configuration Système ---
class ConfigItem(BaseModel):
    id_config: int
    cle: str
    valeur: str
    valeur_parsed: Any = None
    type: str
    description: Optional[str] = None
    date_modification: datetime

    class Config:
        from_attributes = True

class ConfigUpdate(BaseModel):
    valeur: Any = Field(..., description="Nouvelle valeur du paramètre (string, int, bool ou dict/list JSON)")
    type: Optional[str] = Field("STRING", description="Type de la donnée : STRING, INT, BOOL, JSON")
    description: Optional[str] = Field(None, description="Description facultative du paramètre")

# --- Schémas pour la Gestion des Plans Tarifaires ---
class AdminPlanCreate(BaseModel):
    nom: str = Field(..., min_length=2, max_length=50)
    prix_mensuel: Decimal = Decimal("0")
    prix_annuel: Decimal = Decimal("0")
    devise: str = "XAF"
    acces_dettes: bool = False
    acces_epargne: bool = False
    acces_recurrentes: bool = False
    acces_templates: bool = False
    acces_analyse: bool = False
    acces_jarvis: bool = False
    acces_rapport: bool = False

class AdminPlanUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=2, max_length=50)
    prix_mensuel: Optional[Decimal] = None
    prix_annuel: Optional[Decimal] = None
    devise: Optional[str] = None
    acces_dettes: Optional[bool] = None
    acces_epargne: Optional[bool] = None
    acces_recurrentes: Optional[bool] = None
    acces_templates: Optional[bool] = None
    acces_analyse: Optional[bool] = None
    acces_jarvis: Optional[bool] = None
    acces_rapport: Optional[bool] = None

# --- Schémas pour la Gestion des Abonnements & Paiements ---
class PlanCountItem(BaseModel):
    nom_plan: str
    nombre_abonnes: int

class StatutCountItem(BaseModel):
    statut: str
    count: int

class AdminAbonnementOverview(BaseModel):
    total_abonnes: int
    repartition_plans: List[PlanCountItem]
    repartition_statuts: List[StatutCountItem]
    chiffre_affaires_total: Decimal = Decimal("0.00")

class AdminAbonnementItem(BaseModel):
    id_abonnement: int
    id_client: int
    email_client: EmailStr
    nom_client: str
    nom_plan: str
    cycle_facturation: Optional[str] = None
    statut: str
    date_debut: datetime
    date_fin: Optional[datetime] = None
    renouvellement_auto: bool

    class Config:
        from_attributes = True

class AdminAbonnementListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AdminAbonnementItem]

class AdminPaiementItem(BaseModel):
    id_paiement: int
    id_client: int
    email_client: EmailStr
    nom_plan_demande: str
    cycle_facturation: str
    montant: Decimal
    devise: str
    reference_hrpay: str
    statut: str
    date_creation: datetime
    date_confirmation: Optional[datetime] = None

    class Config:
        from_attributes = True

class AdminPaiementListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AdminPaiementItem]

class AdminForceAbonnementPayload(BaseModel):
    id_plan: int
    cycle_facturation: Optional[Literal["MENSUEL", "ANNUEL"]] = Field("MENSUEL", description="MENSUEL ou ANNUEL")
    statut: Literal["ESSAI", "ACTIF", "EXPIRE", "ANNULE"] = Field("ACTIF", description="ESSAI, ACTIF, EXPIRE, ANNULE")
    duree_jours: Optional[int] = Field(30, ge=1, description="Nombre de jours de validité (ex: 30 pour 1 mois)")
    raison: Optional[str] = Field(None, description="Raison de l'attribution manuelle (AuditLog)")

class AdminValiderPaiementManuelPayload(BaseModel):
    raison: Optional[str] = Field(None, description="Raison de la confirmation manuelle (AuditLog)")

# --- Schémas pour la Surveillance Anti-Fraude ---
class TypeTransactionCountItem(BaseModel):
    type: str
    count: int

class AdminFraudeOverview(BaseModel):
    total_transactions_suspectes: int
    nombre_clients_concernes: int
    montant_total_suspect: Decimal = Decimal("0.00")
    repartition_par_type: List[TypeTransactionCountItem]

class AdminTransactionSuspecteItem(BaseModel):
    id_transaction: int
    id_client: int
    email_client: EmailStr
    nom_client: str
    nom_compte: str
    nom_categorie: Optional[str] = None
    montant: Decimal
    type: str
    description: Optional[str] = None
    date: str
    est_suspecte: bool
    date_creation: datetime

    class Config:
        from_attributes = True

class AdminTransactionSuspecteListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AdminTransactionSuspecteItem]

class AdminTransactionSuspecteDetail(AdminTransactionSuspecteItem):
    nombre_total_transactions_client: int
    nombre_transactions_suspectes_client: int
    solde_compte_principal: Decimal = Decimal("0.00")

class AdminUpdateSuspicionPayload(BaseModel):
    est_suspecte: bool = Field(..., description="Bascule du statut de suspicion (True pour marquer, False pour lever)")
    raison: Optional[str] = Field(None, description="Raison explicative du changement (AuditLog)")

# --- Schémas pour le Tableau de Bord KPI Globaux ---
class AdminClientsKPIs(BaseModel):
    total_clients: int
    clients_actifs: int
    clients_suspendus: int
    nouveaux_clients_30j: int

class AdminFinancesKPIs(BaseModel):
    chiffre_affaires_abonnements: Decimal = Decimal("0.00")
    volume_total_transactions: Decimal = Decimal("0.00")
    solde_cumule_comptes_principaux: Decimal = Decimal("0.00")

class AdminAbonnementsKPIs(BaseModel):
    total_abonnes: int
    abonnes_gratuit: int
    abonnes_essentiel: int
    abonnes_premium: int
    taux_conversion_payant_pourcent: float = 0.0

class AdminSecuriteKPIs(BaseModel):
    transactions_suspectes_count: int
    montant_total_suspect: Decimal = Decimal("0.00")
    total_audit_logs: int

class AdminGlobalKPIsResponse(BaseModel):
    clients: AdminClientsKPIs
    finances: AdminFinancesKPIs
    abonnements: AdminAbonnementsKPIs
    securite: AdminSecuriteKPIs
