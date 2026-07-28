// Types TypeScript globaux pour l'application MyNkap

export interface Client {
  id_client: number;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_type: string;
}

export interface CompteFinancier {
  id_compte: number;
  nom: string;
  type: 'MOBILE_MONEY' | 'BANCAIRE' | 'ESPECES' | 'EPARGNE';
  solde: number;
  devise: string;
  est_actif: boolean;
}

export interface Transaction {
  id_transaction: number;
  id_compte: number;
  id_categorie: number | null;
  montant: number;
  description: string | null;
  type: 'DEPENSE' | 'REVENU' | 'DEPOT_INITIAL' | 'ANNULATION' | 'REMBOURSEMENT_DETTE' | 'ENCAISSEMENT_CREANCE';
  date: string;
  est_recurrente: boolean;
  est_suspecte: boolean;
  date_creation: string;
}

export interface ComptePrincipal {
  id_compte_principal: number;
  solde_total: number;
  devise: string;
  patrimoine_net: number;
  date_mise_a_jour: string;
}

export interface Categorie {
  id_categorie: number;
  id_client: number;
  nom: string;
  type: 'DEPENSE' | 'REVENU';
  icone: string | null;
  couleur: string | null;
  est_actif: boolean;
}

export interface Budget {
  id_budget: number;
  id_categorie: number;
  montant_limite: number;
  mois: number;
  annee: number;
  est_actif: boolean;
  montant_depense: number;
  montant_restant: number;
  pourcentage_utilise: number;
  est_depasse: boolean;
}

export interface ObjectifEpargne {
  id_objectif: number;
  id_compte_epargne: number;
  nom: string;
  montant_cible: number;
  date_echeance: string | null;
  statut: string;
  montant_actuel: number;
  montant_restant: number;
  pourcentage_atteint: number;
}

export interface JarvisMessage {
  id_message: string;
  type: string;
  canal: string;
  contenu: string;
  necessite_clarification: boolean;
  options_suggerees: string[] | null;
  date_creation: string;
}

export interface JarvisConversation {
  id_conversation: string;
  titre: string | null;
  date_creation: string;
  date_dernier_message: string;
}

export interface AppNotification {
  id_notification: number;
  type: string;
  titre: string;
  message: string;
  lien: string | null;
  est_lue: boolean;
  date_creation: string;
}

export interface Plan {
  id_plan: number;
  nom: 'GRATUIT' | 'ESSENTIEL' | 'PREMIUM';
  prix_mensuel: number;
  prix_annuel: number;
  devise: string;
  acces_dettes: boolean;
  acces_epargne: boolean;
  acces_recurrentes: boolean;
  acces_templates: boolean;
  acces_analyse: boolean;
  acces_jarvis: boolean;
  acces_rapport: boolean;
}

export interface Abonnement {
  id_abonnement: number;
  plan: Plan;
  statut: string;
  date_debut: string;
  date_fin: string | null;
  cycle_facturation: 'MENSUEL' | 'ANNUEL' | null;
  renouvellement_auto: boolean;
}

export interface PaiementAbonnement {
  id_paiement: number;
  plan_demande: Plan;
  cycle_facturation: string;
  montant: number;
  devise: string;
  reference_hrpay: string;
  statut: 'PENDING' | 'SUCCESS' | 'FAILED';
  date_creation: string;
  date_confirmation: string | null;
}

// --- Types Admin ---
export interface AdminClientListItem {
  id_client: number;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  est_actif: boolean;
  date_creation: string;
  solde_compte_principal: number;
  plan_abonnement: string;
}

export interface AdminListItem {
  id_administrateur: number;
  email: string;
  username: string;
  niveau_acces: number;
  est_actif: boolean;
  date_creation: string;
}

export interface AuditLogListItem {
  id_audit: number;
  id_utilisateur: number;
  email_utilisateur: string | null;
  type_utilisateur: string | null;
  action: string;
  ressource: string;
  id_ressource: number | null;
  date_creation: string;
}

export interface AuditLogDetail extends AuditLogListItem {
  donnees_avant: Record<string, unknown> | null;
  donnees_apres: Record<string, unknown> | null;
}

export interface ConfigItem {
  id_config: number;
  cle: string;
  valeur: string;
  valeur_parsed: unknown;
  type: string;
  description: string | null;
  date_modification: string;
}

export interface AdminAbonnementItem {
  id_abonnement: number;
  id_client: number;
  email_client: string;
  nom_client: string;
  nom_plan: string;
  cycle_facturation: string | null;
  statut: string;
  date_debut: string;
  date_fin: string | null;
  renouvellement_auto: boolean;
}

export interface AdminTransactionSuspecteItem {
  id_transaction: number;
  id_client: number;
  email_client: string;
  nom_client: string;
  nom_compte: string;
  nom_categorie: string | null;
  montant: number;
  type: string;
  description: string | null;
  date: string;
  est_suspecte: boolean;
  date_creation: string;
}

export interface AdminGlobalKPIs {
  clients: {
    total_clients: number;
    clients_actifs: number;
    clients_suspendus: number;
    nouveaux_clients_30j: number;
  };
  finances: {
    chiffre_affaires_abonnements: number;
    volume_total_transactions: number;
    solde_cumule_comptes_principaux: number;
  };
  abonnements: {
    total_abonnes: number;
    abonnes_gratuit: number;
    abonnes_essentiel: number;
    abonnes_premium: number;
    taux_conversion_payant_pourcent: number;
  };
  securite: {
    transactions_suspectes_count: number;
    montant_total_suspect: number;
    total_audit_logs: number;
  };
}
