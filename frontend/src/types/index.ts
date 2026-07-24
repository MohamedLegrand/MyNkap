// Types TypeScript globaux pour l'application MyNkap

export interface Client {
  id_client: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
}

export interface CompteFinancier {
  id_compte: number;
  id_client: number;
  nom: string;
  type: 'MOBILE_MONEY' | 'BANCAIRE' | 'ESPECES' | 'EPARGNE';
  solde: number;
  devise: string;
  est_actif: boolean;
}

export interface Transaction {
  id_transaction: number;
  id_client: number;
  id_compte: number;
  id_categorie: number;
  montant: number;
  description: string;
  type: 'DEPENSE' | 'REVENU' | 'DEPOT_INITIAL' | 'ANNULATION' | 'REMBOURSEMENT_DETTE' | 'ENCAISSEMENT_CREANCE';
  date: string;
  est_recurrente: boolean;
  est_suspecte: boolean;
}
