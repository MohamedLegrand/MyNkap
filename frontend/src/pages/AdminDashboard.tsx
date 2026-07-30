import React, { useCallback, useEffect, useState } from 'react';
import {
  Users,
  Search,
  Plus,
  Zap,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  RefreshCw,
  Eye,
  Edit,
  TrendingUp,
  Loader2,
} from 'lucide-react';
import { AdminLayout } from '../layouts/AdminLayout';
import { api } from '../services/api';
import {
  CreateAdminModal,
  ResetClientPasswordModal,
  EditConfigModal,
  ViewAuditDetailModal,
} from '../components/AdminModals';
import type {
  AdminClientListItem,
  AdminListItem,
  AuditLogListItem,
  AuditLogDetail,
  ConfigItem,
  AdminAbonnementItem,
  AdminTransactionSuspecteItem,
  AdminGlobalKPIs,
} from '../types';

interface Paginated<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

const formatXAF = (valeur: number) => `${Number(valeur).toLocaleString('fr-FR')} XAF`;

export const AdminDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('kpis');

  // Modals state
  const [isCreateAdminOpen, setIsCreateAdminOpen] = useState(false);
  const [isResetPasswordOpen, setIsResetPasswordOpen] = useState(false);
  const [targetClient, setTargetClient] = useState<{ id: number; name: string } | null>(null);
  const [resetPasswordResult, setResetPasswordResult] = useState<string | null>(null);

  const [isEditConfigOpen, setIsEditConfigOpen] = useState(false);
  const [targetConfig, setTargetConfig] = useState<{ key: string; val: string; type: string; description: string | null } | null>(null);

  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);
  const [selectedAuditLog, setSelectedAuditLog] = useState<AuditLogDetail | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // États de données consommant l'API backend
  const [kpis, setKpis] = useState<AdminGlobalKPIs | null>(null);
  const [clients, setClients] = useState<AdminClientListItem[]>([]);
  const [admins, setAdmins] = useState<AdminListItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogListItem[]>([]);
  const [configs, setConfigs] = useState<ConfigItem[]>([]);
  const [subscriptions, setSubscriptions] = useState<AdminAbonnementItem[]>([]);
  const [fraudTransactions, setFraudTransactions] = useState<AdminTransactionSuspecteItem[]>([]);

  const fetchAdminKPIs = useCallback(async () => {
    try {
      const res = await api.request<AdminGlobalKPIs>('/admin/kpis');
      setKpis(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger les KPIs.');
    }
  }, []);

  const fetchClients = useCallback(async () => {
    try {
      const res = await api.request<Paginated<AdminClientListItem>>('/admin/clients');
      setClients(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger les clients.');
    }
  }, []);

  const fetchAdmins = useCallback(async () => {
    try {
      const res = await api.request<AdminListItem[]>('/admin/admins');
      setAdmins(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger les administrateurs.');
    }
  }, []);

  const fetchAuditLogs = useCallback(async () => {
    try {
      const res = await api.request<Paginated<AuditLogListItem>>('/admin/audit');
      setAuditLogs(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Impossible de charger l'audit.");
    }
  }, []);

  const fetchConfigs = useCallback(async () => {
    try {
      const res = await api.request<ConfigItem[]>('/admin/config');
      setConfigs(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger la configuration.');
    }
  }, []);

  const fetchSubscriptions = useCallback(async () => {
    try {
      const res = await api.request<Paginated<AdminAbonnementItem>>('/admin/abonnements');
      setSubscriptions(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger les abonnements.');
    }
  }, []);

  const fetchFraudTransactions = useCallback(async () => {
    try {
      const res = await api.request<Paginated<AdminTransactionSuspecteItem>>('/admin/fraude/transactions');
      setFraudTransactions(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger la surveillance anti-fraude.');
    }
  }, []);

  useEffect(() => {
    const fetchersParOnglet: Record<string, () => Promise<void>> = {
      kpis: fetchAdminKPIs,
      clients: fetchClients,
      admins: fetchAdmins,
      audit: fetchAuditLogs,
      config: fetchConfigs,
      subscriptions: fetchSubscriptions,
      fraud: fetchFraudTransactions,
    };
    const fetcher = fetchersParOnglet[activeTab];
    if (!fetcher) return;

    // Chargement à chaque changement d'onglet, pas une synchronisation
    // d'état dérivé d'un rendu précédent.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setError(null);
    setIsLoading(true);
    fetcher().finally(() => setIsLoading(false));
  }, [activeTab, fetchAdminKPIs, fetchClients, fetchAdmins, fetchAuditLogs, fetchConfigs, fetchSubscriptions, fetchFraudTransactions]);

  // Actions Clients (Module 1)
  const handleToggleClientStatus = async (id: number, currentlyActive: boolean) => {
    try {
      await api.request(`/admin/clients/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ est_actif: !currentlyActive }),
      });
      setClients((prev) => prev.map((c) => (c.id_client === id ? { ...c, est_actif: !currentlyActive } : c)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action impossible.');
    }
  };

  const handleTriggerResetPassword = (id: number, name: string) => {
    setTargetClient({ id, name });
    setResetPasswordResult(null);
    setIsResetPasswordOpen(true);
  };

  const handleConfirmResetPassword = async () => {
    if (!targetClient) return;
    try {
      const res = await api.request<{ mot_de_passe_temporaire: string }>(`/admin/clients/${targetClient.id}/reset-password`, {
        method: 'POST',
      });
      setResetPasswordResult(res.mot_de_passe_temporaire);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Réinitialisation impossible.');
    }
  };

  // Actions Admin (Module 2)
  const handleCreateAdminSubmit = async (data: { username: string; email: string; mot_de_passe: string; niveau_acces: number }) => {
    try {
      const nouvelAdmin = await api.request<AdminListItem>('/admin/admins', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      setAdmins((prev) => [...prev, nouvelAdmin]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Création de l'administrateur impossible.");
    }
  };

  const handleUpdateAdminLevel = async (id: number, currentLevel: number) => {
    const nextLevel = currentLevel >= 3 ? 1 : currentLevel + 1;
    try {
      const admin = await api.request<AdminListItem>(`/admin/admins/${id}/level`, {
        method: 'PATCH',
        body: JSON.stringify({ niveau_acces: nextLevel }),
      });
      setAdmins((prev) => prev.map((a) => (a.id_administrateur === id ? admin : a)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Changement de rôle impossible.');
    }
  };

  // Actions Audit (Module 3)
  const handleInspectAuditLog = async (log: AuditLogListItem) => {
    try {
      const detail = await api.request<AuditLogDetail>(`/admin/audit/${log.id_audit}`);
      setSelectedAuditLog(detail);
      setIsAuditModalOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Détail d'audit indisponible.");
    }
  };

  // Actions Config (Module 4)
  const handleSaveConfig = async (newVal: string) => {
    if (!targetConfig) return;
    try {
      const updated = await api.request<ConfigItem>(`/admin/config/${targetConfig.key}`, {
        method: 'PUT',
        body: JSON.stringify({ valeur: newVal, type: targetConfig.type, description: targetConfig.description }),
      });
      setConfigs((prev) => prev.map((cfg) => (cfg.cle === targetConfig.key ? updated : cfg)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Modification impossible.');
    }
  };

  // Actions Anti-Fraude (Module 6)
  const handleToggleFraudStatus = async (idTx: number, currentlySuspicious: boolean) => {
    try {
      const updated = await api.request<AdminTransactionSuspecteItem>(`/admin/fraude/transactions/${idTx}/statut`, {
        method: 'PATCH',
        body: JSON.stringify({ est_suspecte: !currentlySuspicious }),
      });
      setFraudTransactions((prev) => prev.map((tx) => (tx.id_transaction === idTx ? updated : tx)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action impossible.');
    }
  };

  return (
    <AdminLayout activeTab={activeTab} onTabChange={setActiveTab}>
      {error && (
        <div className="mb-4 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="font-bold">✕</button>
        </div>
      )}

      {isLoading && (
        <div className="flex justify-center py-10">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* 📊 MODULE 7 : TABLEAU DE BORD KPIS GLOBAUX */}
      {!isLoading && activeTab === 'kpis' && kpis && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">Tableau de Bord KPI Globaux (Supervision 360°)</h2>
              <p className="text-xs text-muted-foreground">Vue synthétique consolidée de l'ensemble des modules MyNkap</p>
            </div>
            <button onClick={fetchAdminKPIs} className="p-2 rounded-xl bg-muted hover:bg-accent text-xs font-semibold flex items-center gap-1.5 border border-border">
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Actualiser les métriques</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">Base Clients</span>
                <Users className="h-5 w-5 text-primary" />
              </div>
              <p className="text-3xl font-black text-primary tabular-nums">{kpis.clients.total_clients}</p>
              <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                <span>Actifs : <strong className="text-forest-600 dark:text-forest-400">{kpis.clients.clients_actifs}</strong></span>
                <span>Nouveaux +30j : <strong className="text-secondary">+{kpis.clients.nouveaux_clients_30j}</strong></span>
              </div>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">Chiffre d'Affaires</span>
                <TrendingUp className="h-5 w-5 text-secondary" />
              </div>
              <p className="text-2xl font-black text-secondary tabular-nums">{formatXAF(kpis.finances.chiffre_affaires_abonnements)}</p>
              <p className="text-xs text-muted-foreground mt-2">Volume total : {formatXAF(kpis.finances.volume_total_transactions)}</p>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">Conversion Payant</span>
                <Zap className="h-5 w-5 text-forest-500 dark:text-forest-400" />
              </div>
              <p className="text-3xl font-black text-forest-500 dark:text-forest-400 tabular-nums">{kpis.abonnements.taux_conversion_payant_pourcent}%</p>
              <p className="text-xs text-muted-foreground mt-2">Payants : {kpis.abonnements.abonnes_essentiel + kpis.abonnements.abonnes_premium} abonnés</p>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">Alertes Fraude</span>
                <AlertOctagon className="h-5 w-5 text-destructive" />
              </div>
              <p className="text-3xl font-black text-destructive tabular-nums">{kpis.securite.transactions_suspectes_count}</p>
              <p className="text-xs font-semibold text-destructive mt-2">Montant à risque : {formatXAF(kpis.securite.montant_total_suspect)}</p>
            </div>
          </div>
        </div>
      )}

      {/* 👥 MODULE 1 : GESTION DES CLIENTS */}
      {!isLoading && activeTab === 'clients' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">Gestion des Clients (Module 1)</h2>
              <p className="text-xs text-muted-foreground">Consulter, suspendre et réinitialiser les comptes clients</p>
            </div>
          </div>

          <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
            <div className="p-4 border-b border-border flex items-center justify-between gap-4">
              <div className="relative flex-1 max-w-md">
                <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Rechercher par nom, email, téléphone..."
                  className="w-full bg-background border border-border rounded-xl pl-9 pr-4 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase font-bold text-[10px]">
                <tr>
                  <th className="p-4">Client</th>
                  <th className="p-4">Téléphone</th>
                  <th className="p-4">Solde principal</th>
                  <th className="p-4">Plan</th>
                  <th className="p-4">Statut</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-medium">
                {clients.map((c) => (
                  <tr key={c.id_client} className="hover:bg-muted/30">
                    <td className="p-4">
                      <strong className="block text-foreground">{c.first_name} {c.last_name}</strong>
                      <span className="text-[11px] text-muted-foreground">{c.email}</span>
                    </td>
                    <td className="p-4">{c.phone}</td>
                    <td className="p-4">{formatXAF(c.solde_compte_principal)}</td>
                    <td className="p-4">
                      <span className="bg-primary/10 text-primary font-bold px-2 py-0.5 rounded text-[10px]">
                        {c.plan_abonnement}
                      </span>
                    </td>
                    <td className="p-4">
                      {c.est_actif ? (
                        <span className="inline-flex items-center gap-1 bg-forest-500/10 text-forest-600 dark:text-forest-400 px-2 py-0.5 rounded-full font-bold text-[10px]">
                          <CheckCircle2 className="h-3 w-3" /> Actif
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 bg-destructive/10 text-destructive px-2 py-0.5 rounded-full font-bold text-[10px]">
                          <XCircle className="h-3 w-3" /> Suspendu
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        onClick={() => handleToggleClientStatus(c.id_client, c.est_actif)}
                        className={`p-1.5 rounded-lg border text-[11px] font-bold ${
                          c.est_actif ? 'bg-destructive/10 text-destructive border-destructive/20' : 'bg-forest-500/10 text-forest-600 border-forest-500/20'
                        }`}
                      >
                        {c.est_actif ? 'Suspendre' : 'Réactiver'}
                      </button>
                      <button
                        onClick={() => handleTriggerResetPassword(c.id_client, `${c.first_name} ${c.last_name}`)}
                        className="p-1.5 rounded-lg bg-primary/10 text-primary border border-primary/20 text-[11px] font-bold"
                      >
                        Reset Password
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {clients.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">Aucun client.</p>}
          </div>
        </div>
      )}

      {/* 🛡️ MODULE 2 : GESTION DES ADMINS */}
      {!isLoading && activeTab === 'admins' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">Équipe Administrateur (Module 2)</h2>
              <p className="text-xs text-muted-foreground">Gestion des accès d'administration et attribution des rôles</p>
            </div>
            <button
              onClick={() => setIsCreateAdminOpen(true)}
              className="bg-primary text-primary-foreground font-bold text-xs py-2.5 px-4 rounded-xl shadow-md hover:bg-primary/90 flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" />
              <span>Créer un Admin</span>
            </button>
          </div>

          <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase font-bold text-[10px]">
                <tr>
                  <th className="p-4">Admin</th>
                  <th className="p-4">Niveau d'Accès</th>
                  <th className="p-4">Créé le</th>
                  <th className="p-4">Statut</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-medium">
                {admins.map((a) => (
                  <tr key={a.id_administrateur} className="hover:bg-muted/30">
                    <td className="p-4">
                      <strong className="block text-foreground">{a.username}</strong>
                      <span className="text-[11px] text-muted-foreground">{a.email}</span>
                    </td>
                    <td className="p-4">
                      <span className={`font-black px-2 py-0.5 rounded text-[10px] ${
                        a.niveau_acces === 3 ? 'bg-primary/20 text-primary border border-primary/30' : 'bg-muted text-muted-foreground'
                      }`}>
                        Niveau {a.niveau_acces} ({a.niveau_acces === 3 ? 'Superadmin' : a.niveau_acces === 2 ? 'Modérateur' : 'Support'})
                      </span>
                    </td>
                    <td className="p-4">{new Date(a.date_creation).toLocaleDateString('fr-FR')}</td>
                    <td className="p-4">
                      {a.est_actif ? (
                        <span className="inline-flex items-center gap-1 bg-forest-500/10 text-forest-600 dark:text-forest-400 px-2 py-0.5 rounded-full font-bold text-[10px]">
                          Actif
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 bg-destructive/10 text-destructive px-2 py-0.5 rounded-full font-bold text-[10px]">
                          Suspendu
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => handleUpdateAdminLevel(a.id_administrateur, a.niveau_acces)}
                        className="px-2.5 py-1 rounded-lg bg-primary/10 text-primary text-[11px] font-bold border border-primary/20"
                      >
                        Changer Rôle
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {admins.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">Aucun administrateur.</p>}
          </div>
        </div>
      )}

      {/* 📜 MODULE 3 : AUDIT GLOBAL */}
      {!isLoading && activeTab === 'audit' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">Journaux d'Audit & Traçabilité (Module 3)</h2>
              <p className="text-xs text-muted-foreground">Historique inaltérable de toutes les actions sur la plateforme</p>
            </div>
          </div>

          <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase font-bold text-[10px]">
                <tr>
                  <th className="p-4"># ID</th>
                  <th className="p-4">Utilisateur</th>
                  <th className="p-4">Action</th>
                  <th className="p-4">Ressource</th>
                  <th className="p-4">Horodatage</th>
                  <th className="p-4 text-right">Inspection</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-medium">
                {auditLogs.map((log) => (
                  <tr key={log.id_audit} className="hover:bg-muted/30">
                    <td className="p-4 font-mono font-bold text-muted-foreground">#{log.id_audit}</td>
                    <td className="p-4 font-bold text-foreground">{log.email_utilisateur ?? `ID ${log.id_utilisateur}`}</td>
                    <td className="p-4">
                      <span className="bg-primary/10 text-primary font-mono font-bold px-2 py-0.5 rounded text-[10px]">
                        {log.action}
                      </span>
                    </td>
                    <td className="p-4">{log.ressource} {log.id_ressource != null ? `(#${log.id_ressource})` : ''}</td>
                    <td className="p-4 text-muted-foreground">{new Date(log.date_creation).toLocaleString('fr-FR')}</td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => handleInspectAuditLog(log)}
                        className="px-2.5 py-1 rounded-lg bg-muted hover:bg-accent text-xs font-bold border border-border inline-flex items-center gap-1"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>Inspecter JSON</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {auditLogs.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">Aucune entrée d'audit.</p>}
          </div>
        </div>
      )}

      {/* ⚙️ MODULE 4 : CONFIGURATION SYSTÈME */}
      {!isLoading && activeTab === 'config' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">Configuration Système à Chaud (Module 4)</h2>
              <p className="text-xs text-muted-foreground">Modifier la configuration applicative sans aucun redéploiement</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {configs.map((cfg) => (
              <div key={cfg.cle} className="bg-card p-5 rounded-2xl border border-border shadow-sm space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="text-sm font-mono font-bold text-foreground">{cfg.cle}</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">{cfg.description}</p>
                  </div>
                  <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded bg-muted text-muted-foreground">
                    {cfg.type}
                  </span>
                </div>

                <div className="pt-2 flex items-center justify-between border-t border-border">
                  <span className="font-mono text-sm font-black text-primary">{cfg.valeur}</span>
                  <button
                    onClick={() => {
                      setTargetConfig({ key: cfg.cle, val: cfg.valeur, type: cfg.type, description: cfg.description });
                      setIsEditConfigOpen(true);
                    }}
                    className="px-3 py-1.5 rounded-xl bg-primary/10 text-primary border border-primary/20 text-xs font-bold flex items-center gap-1"
                  >
                    <Edit className="h-3.5 w-3.5" />
                    <span>Modifier à chaud</span>
                  </button>
                </div>
              </div>
            ))}
            {configs.length === 0 && <p className="text-xs text-muted-foreground">Aucun paramètre de configuration.</p>}
          </div>
        </div>
      )}

      {/* 💳 MODULE 5 : ABONNEMENTS & PAIEMENTS */}
      {!isLoading && activeTab === 'subscriptions' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">Abonnements & Paiements Mobile Money (Module 5)</h2>
              <p className="text-xs text-muted-foreground">Gestion des abonnements payants et validation des litiges HR-Skills Pay</p>
            </div>
          </div>

          <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase font-bold text-[10px]">
                <tr>
                  <th className="p-4">Client</th>
                  <th className="p-4">Plan Tarifaire</th>
                  <th className="p-4">Statut</th>
                  <th className="p-4">Cycle</th>
                  <th className="p-4">Période</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-medium">
                {subscriptions.map((sub) => (
                  <tr key={sub.id_abonnement} className="hover:bg-muted/30">
                    <td className="p-4 font-bold text-foreground">{sub.email_client}</td>
                    <td className="p-4 font-bold text-primary">{sub.nom_plan}</td>
                    <td className="p-4">
                      <span className="inline-flex items-center gap-1 bg-forest-500/10 text-forest-600 font-bold px-2 py-0.5 rounded-full text-[10px]">
                        {sub.statut}
                      </span>
                    </td>
                    <td className="p-4 text-muted-foreground">{sub.cycle_facturation ?? '—'}</td>
                    <td className="p-4 text-muted-foreground">
                      {new Date(sub.date_debut).toLocaleDateString('fr-FR')} ➔ {sub.date_fin ? new Date(sub.date_fin).toLocaleDateString('fr-FR') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {subscriptions.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">Aucun abonnement.</p>}
          </div>
        </div>
      )}

      {/* 🚨 MODULE 6 : SURVEILLANCE ANTI-FRAUDE */}
      {!isLoading && activeTab === 'fraud' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight text-destructive flex items-center gap-2">
                <AlertOctagon className="h-6 w-6" />
                <span>Surveillance Anti-Fraude (Module 6)</span>
              </h2>
              <p className="text-xs text-muted-foreground">Transactions suspectes signalées et gestion du risque financier</p>
            </div>
          </div>

          <div className="bg-card rounded-2xl border border-destructive/30 overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-destructive/10 border-b border-destructive/20 text-destructive uppercase font-bold text-[10px]">
                <tr>
                  <th className="p-4"># Tx</th>
                  <th className="p-4">Client Impacté</th>
                  <th className="p-4">Description / Alerte</th>
                  <th className="p-4">Montant</th>
                  <th className="p-4">Date</th>
                  <th className="p-4 text-right">Action Suspicion</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-medium">
                {fraudTransactions.map((tx) => (
                  <tr key={tx.id_transaction} className="hover:bg-destructive/5">
                    <td className="p-4 font-mono font-bold">#{tx.id_transaction}</td>
                    <td className="p-4 font-bold text-foreground">{tx.email_client}</td>
                    <td className="p-4">{tx.description ?? tx.nom_categorie ?? '—'}</td>
                    <td className="p-4 font-black text-destructive">{formatXAF(tx.montant)}</td>
                    <td className="p-4 text-muted-foreground">{new Date(tx.date_creation).toLocaleString('fr-FR')}</td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => handleToggleFraudStatus(tx.id_transaction, tx.est_suspecte)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-bold ${
                          tx.est_suspecte ? 'bg-forest-500/10 text-forest-600 border border-forest-500/20' : 'bg-destructive/10 text-destructive border border-destructive/20'
                        }`}
                      >
                        {tx.est_suspecte ? 'Lever la suspicion' : 'Marquer Suspecte'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {fraudTransactions.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">Aucune transaction suspecte.</p>}
          </div>
        </div>
      )}

      {/* MODALS REUTILISABLES */}
      <CreateAdminModal
        isOpen={isCreateAdminOpen}
        onClose={() => setIsCreateAdminOpen(false)}
        onSubmit={handleCreateAdminSubmit}
      />

      <ResetClientPasswordModal
        isOpen={isResetPasswordOpen}
        clientName={targetClient?.name || ''}
        onClose={() => setIsResetPasswordOpen(false)}
        onConfirm={handleConfirmResetPassword}
        tempPasswordResult={resetPasswordResult}
      />

      <EditConfigModal
        isOpen={isEditConfigOpen}
        configKey={targetConfig?.key || ''}
        initialValue={targetConfig?.val || ''}
        typeDonnee={targetConfig?.type || ''}
        onClose={() => setIsEditConfigOpen(false)}
        onSubmit={handleSaveConfig}
      />

      <ViewAuditDetailModal
        isOpen={isAuditModalOpen}
        auditItem={selectedAuditLog ? {
          id_log: selectedAuditLog.id_audit,
          utilisateur_email: selectedAuditLog.email_utilisateur,
          id_utilisateur: selectedAuditLog.id_utilisateur,
          action: selectedAuditLog.action,
          ressource: selectedAuditLog.ressource,
          id_ressource: selectedAuditLog.id_ressource,
          date_action: new Date(selectedAuditLog.date_creation).toLocaleString('fr-FR'),
          donnees_avant: selectedAuditLog.donnees_avant,
          donnees_apres: selectedAuditLog.donnees_apres,
        } : null}
        onClose={() => setIsAuditModalOpen(false)}
      />
    </AdminLayout>
  );
};
