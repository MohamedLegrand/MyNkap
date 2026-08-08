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
  type: 'DEPENSE' | 'REVENU' | 'DEPOT_INITIAL' | 'ANNULATION' | 'REMBOURSEMENT_DETTE' | 'ENCAISSEMENT_CREANCE' | 'DETTE_RECUE' | 'CREANCE_ACCORDEE';
  date: string;
  est_recurrente: boolean;
  est_suspecte: boolean;
  id_transaction_annulee: number | null;
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
  montant_mensuel_requis: number | null;
}

export interface Transfert {
  id_transfert: number;
  id_compte_source: number;
  id_compte_destination: number;
  montant: number;
  description: string | null;
  date: string;
  date_creation: string;
}

export interface TransactionRecurrente {
  id_transaction_recurrente: number;
  id_compte: number;
  id_categorie: number;
  montant: number;
  type: 'DEPENSE' | 'REVENU';
  description: string | null;
  frequence: 'HEBDOMADAIRE' | 'MENSUELLE' | 'TRIMESTRIELLE' | 'ANNUELLE';
  prochaine_execution: string;
  date_fin: string | null;
  est_active: boolean;
  date_creation: string;
}

export interface TemplateTransaction {
  id_template: number;
  id_compte: number;
  id_categorie: number;
  nom: string;
  montant: number;
  type: 'DEPENSE' | 'REVENU';
  description: string | null;
  nombre_utilisations: number;
  est_actif: boolean;
  date_creation: string;
  date_modification: string;
}

export interface Dette {
  id_dette: number;
  id_compte: number;
  nom: string;
  type: 'DETTE' | 'CREANCE';
  montant_total: number;
  montant_rembourse: number;
  montant_restant: number;
  personne_impliquee: string | null;
  date_echeance: string | null;
  statut: string;
  jours_avant_echeance: number | null;
  impact_patrimoine_net: number;
}

export interface Rapport {
  id_rapport: number;
  type: 'RELEVE_TRANSACTIONS' | 'BILAN_BUDGETAIRE' | 'DETTES_EPARGNE' | 'BILAN_FINANCIER' | 'PREDICTIONS';
  periode_debut: string;
  periode_fin: string;
  statut: 'EN_COURS' | 'GENERE' | 'ECHEC';
  taille: number | null;
  date_generation: string;
}

export interface JarvisMessage {
  id_message: string;
  type: 'QUESTION' | 'REPONSE';
  canal: 'TEXTE' | 'VOCAL';
  contenu: string;
  necessite_clarification: boolean;
  options_suggerees: string[] | null;
  peut_se_permettre: boolean | null;
  montant_suggere: number | null;
  conseil_supplementaire: string | null;
  date_creation: string;
}

export interface JarvisMessageVocal extends JarvisMessage {
  // null si la synthèse vocale de la réponse a échoué (la réponse texte
  // reste utilisable quand même) — voir jarvis.service.poser_question_vocale.
  audio_base64: string | null;
}

export interface JarvisConversation {
  id_conversation: string;
  titre: string | null;
  date_creation: string;
  date_dernier_message: string;
}

export interface JarvisConversationDetail extends JarvisConversation {
  messages: JarvisMessage[];
}

export interface AnalyseFinanciere {
  id_analyse: number | null;
  type: 'HABITUDES' | 'TENDANCES' | 'COMPARAISON' | 'COMPORTEMENT';
  periode_debut: string;
  periode_fin: string;
  resultats: Record<string, unknown> | null;
  score_financier: number | null;
  date_generation: string;
}

export interface Prediction {
  id_prediction: number | null;
  type: 'DEPENSES_FUTURES' | 'RISQUE_BUDGETAIRE' | 'CAPACITE_EPARGNE';
  periode_debut: string;
  periode_fin: string;
  montant_predit: number | null;
  niveau_confiance: number | null;
  recommandations: string | null;
  date_generation: string;
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
  // Les 3 plans système (GRATUIT/ESSENTIEL/PREMIUM) sont figés côté backend,
  // mais un admin peut créer des plans additionnels avec un nom libre.
  nom: string;
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

export interface AdminClientDetail {
  id_client: number;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  est_actif: boolean;
  date_creation: string;
  date_modification: string;
  solde_compte_principal: number;
  nombre_comptes_financiers: number;
  nombre_transactions: number;
  nombre_dettes_actives: number;
  plan_abonnement: string;
}

export interface AuditStatsResponse {
  total_logs: number;
  repartition_actions: { action: string; count: number }[];
}

export interface AdminAbonnementOverview {
  total_abonnes: number;
  repartition_plans: { nom_plan: string; nombre_abonnes: number }[];
  repartition_statuts: { statut: string; count: number }[];
  chiffre_affaires_total: number;
}

export interface AdminPaiementItem {
  id_paiement: number;
  id_client: number;
  email_client: string;
  nom_plan_demande: string;
  cycle_facturation: string;
  montant: number;
  devise: string;
  reference_hrpay: string;
  statut: 'PENDING' | 'SUCCESS' | 'FAILED';
  date_creation: string;
  date_confirmation: string | null;
}

export interface AdminFraudeOverview {
  total_transactions_suspectes: number;
  nombre_clients_concernes: number;
  montant_total_suspect: number;
  repartition_par_type: { type: string; count: number }[];
}

export interface AdminTransactionSuspecteDetail extends AdminTransactionSuspecteItem {
  nombre_total_transactions_client: number;
  nombre_transactions_suspectes_client: number;
  solde_compte_principal: number;
}
