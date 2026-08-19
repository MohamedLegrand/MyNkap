import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
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
  UserCog,
  ShieldOff,
  ShieldCheck,
  CreditCard,
  Trash2,
  Crown,
  X,
} from 'lucide-react';
import { AdminLayout } from '../layouts/AdminLayout';
import { api } from '../services/api';
import {
  CreateAdminModal,
  ResetClientPasswordModal,
  EditConfigModal,
  ViewAuditDetailModal,
  ClientDetailModal,
  TransactionSuspecteDetailModal,
  PlanModal,
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
  AuditStatsResponse,
  AdminAbonnementOverview,
  AdminPaiementItem,
  AdminFraudeOverview,
  Plan,
} from '../types';

interface Paginated<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

const formatXAF = (valeur: number) => `${Number(valeur).toLocaleString('fr-FR')} XAF`;

export const AdminDashboard: React.FC = () => {
  const { t } = useTranslation();
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

  const [idClientDetail, setIdClientDetail] = useState<number | null>(null);
  const [idTransactionDetail, setIdTransactionDetail] = useState<number | null>(null);
  const [modeSubscriptions, setModeSubscriptions] = useState<'abonnements' | 'paiements' | 'plans'>('abonnements');

  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false);
  const [planEnEdition, setPlanEnEdition] = useState<Plan | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // États de données consommant l'API backend
  const [kpis, setKpis] = useState<AdminGlobalKPIs | null>(null);
  const [clients, setClients] = useState<AdminClientListItem[]>([]);
  const [admins, setAdmins] = useState<AdminListItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogListItem[]>([]);
  const [auditStats, setAuditStats] = useState<AuditStatsResponse | null>(null);
  const [configs, setConfigs] = useState<ConfigItem[]>([]);
  const [subscriptions, setSubscriptions] = useState<AdminAbonnementItem[]>([]);
  const [subscriptionsOverview, setSubscriptionsOverview] = useState<AdminAbonnementOverview | null>(null);
  const [paiements, setPaiements] = useState<AdminPaiementItem[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [fraudTransactions, setFraudTransactions] = useState<AdminTransactionSuspecteItem[]>([]);
  const [fraudOverview, setFraudOverview] = useState<AdminFraudeOverview | null>(null);

  const fetchAdminKPIs = useCallback(async () => {
    try {
      const res = await api.request<AdminGlobalKPIs>('/admin/kpis');
      setKpis(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.kpis'));
    }
  }, [t]);

  const fetchClients = useCallback(async () => {
    try {
      const res = await api.request<Paginated<AdminClientListItem>>('/admin/clients');
      setClients(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.clients'));
    }
  }, [t]);

  const fetchAdmins = useCallback(async () => {
    try {
      const res = await api.request<AdminListItem[]>('/admin/admins');
      setAdmins(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.admins'));
    }
  }, [t]);

  const fetchAuditLogs = useCallback(async () => {
    try {
      const [logs, stats] = await Promise.all([
        api.request<Paginated<AuditLogListItem>>('/admin/audit'),
        api.request<AuditStatsResponse>('/admin/audit/stats'),
      ]);
      setAuditLogs(logs.items);
      setAuditStats(stats);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.audit'));
    }
  }, [t]);

  const fetchConfigs = useCallback(async () => {
    try {
      const res = await api.request<ConfigItem[]>('/admin/config');
      setConfigs(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.config'));
    }
  }, [t]);

  const fetchSubscriptions = useCallback(async () => {
    try {
      const [res, overview, paiementsRes, plansRes] = await Promise.all([
        api.request<Paginated<AdminAbonnementItem>>('/admin/abonnements'),
        api.request<AdminAbonnementOverview>('/admin/abonnements/overview'),
        api.request<Paginated<AdminPaiementItem>>('/admin/paiements'),
        api.request<Plan[]>('/admin/plans'),
      ]);
      setSubscriptions(res.items);
      setSubscriptionsOverview(overview);
      setPaiements(paiementsRes.items);
      setPlans(plansRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.subscriptions'));
    }
  }, [t]);

  const handleOuvrirCreationPlan = () => {
    setPlanEnEdition(null);
    setIsPlanModalOpen(true);
  };

  const handleOuvrirEditionPlan = (plan: Plan) => {
    setPlanEnEdition(plan);
    setIsPlanModalOpen(true);
  };

  const handleSubmitPlan = async (data: {
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
    acces_tontine: boolean;
  }) => {
    if (planEnEdition) {
      const updated = await api.request<Plan>(`/admin/plans/${planEnEdition.id_plan}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
      setPlans((prev) => prev.map((p) => (p.id_plan === updated.id_plan ? updated : p)));
    } else {
      const created = await api.request<Plan>('/admin/plans', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      setPlans((prev) => [...prev, created]);
    }
  };

  const handleDeletePlan = async (plan: Plan) => {
    if (!window.confirm(t('admin.dashboard.errors.delete_plan_confirm', { nom: plan.nom }))) return;
    try {
      await api.request(`/admin/plans/${plan.id_plan}`, { method: 'DELETE' });
      setPlans((prev) => prev.filter((p) => p.id_plan !== plan.id_plan));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('common.error_delete'));
    }
  };

  const handleValiderPaiementManuel = async (idPaiement: number) => {
    if (!window.confirm(t('admin.dashboard.errors.validate_payment_confirm'))) return;
    try {
      const paiement = await api.request<AdminPaiementItem>(`/admin/paiements/${idPaiement}/valider-manuel`, {
        method: 'POST',
        body: JSON.stringify({ raison: 'Validation manuelle par un administrateur' }),
      });
      setPaiements((prev) => prev.map((p) => (p.id_paiement === idPaiement ? paiement : p)));
      fetchSubscriptions();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.validate_payment_failed'));
    }
  };

  const fetchFraudTransactions = useCallback(async () => {
    try {
      const [res, overview] = await Promise.all([
        api.request<Paginated<AdminTransactionSuspecteItem>>('/admin/fraude/transactions'),
        api.request<AdminFraudeOverview>('/admin/fraude/overview'),
      ]);
      setFraudTransactions(res.items);
      setFraudOverview(overview);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.fraud'));
    }
  }, [t]);

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
      setError(err instanceof Error ? err.message : t('common.error_action'));
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
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.reset_password_failed'));
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
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.create_admin_failed'));
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
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.role_change_failed'));
    }
  };

  const handleToggleAdminStatus = async (id: number, currentlyActive: boolean) => {
    const raison = currentlyActive ? window.prompt(t('admin.dashboard.errors.suspension_reason_prompt')) ?? undefined : undefined;
    try {
      const admin = await api.request<AdminListItem>(`/admin/admins/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ est_actif: !currentlyActive, raison }),
      });
      setAdmins((prev) => prev.map((a) => (a.id_administrateur === id ? admin : a)));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.status_change_failed'));
    }
  };

  // Actions Audit (Module 3)
  const handleInspectAuditLog = async (log: AuditLogListItem) => {
    try {
      const detail = await api.request<AuditLogDetail>(`/admin/audit/${log.id_audit}`);
      setSelectedAuditLog(detail);
      setIsAuditModalOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.audit_detail_failed'));
    }
  };

  // Actions Config (Module 4)
  const handleOuvrirEditionConfig = async (cle: string) => {
    // Relit la valeur fraîche depuis le serveur avant édition, plutôt que
    // de se fier à la liste locale (potentiellement périmée).
    try {
      const fraiche = await api.request<ConfigItem>(`/admin/config/${cle}`);
      setTargetConfig({ key: fraiche.cle, val: fraiche.valeur, type: fraiche.type, description: fraiche.description });
      setIsEditConfigOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.load_config_param_failed'));
    }
  };

  const handleSaveConfig = async (newVal: string) => {
    if (!targetConfig) return;
    try {
      const updated = await api.request<ConfigItem>(`/admin/config/${targetConfig.key}`, {
        method: 'PUT',
        body: JSON.stringify({ valeur: newVal, type: targetConfig.type, description: targetConfig.description }),
      });
      setConfigs((prev) => prev.map((cfg) => (cfg.cle === targetConfig.key ? updated : cfg)));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.dashboard.errors.modify_config_failed'));
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
      setError(err instanceof Error ? err.message : t('common.error_action'));
    }
  };

  return (
    <AdminLayout activeTab={activeTab} onTabChange={setActiveTab}>
      {error && (
        <div className="mb-4 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label={t('common.close')}><X className="h-4 w-4" /></button>
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
              <h2 className="text-xl font-black tracking-tight">{t('admin.dashboard.kpis.title')}</h2>
              <p className="text-xs text-muted-foreground">{t('admin.dashboard.kpis.subtitle')}</p>
            </div>
            <button onClick={fetchAdminKPIs} className="p-2 rounded-xl bg-muted hover:bg-accent text-xs font-semibold flex items-center gap-1.5 border border-border">
              <RefreshCw className="h-3.5 w-3.5" />
              <span>{t('admin.dashboard.kpis.refresh')}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">{t('admin.dashboard.kpis.client_base')}</span>
                <Users className="h-5 w-5 text-primary" />
              </div>
              <p className="text-3xl font-black text-primary tabular-nums">{kpis.clients.total_clients}</p>
              <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                <span>{t('admin.dashboard.kpis.active_label')} <strong className="text-forest-600 dark:text-forest-400">{kpis.clients.clients_actifs}</strong></span>
                <span>{t('admin.dashboard.kpis.new_30d_label')} <strong className="text-secondary">+{kpis.clients.nouveaux_clients_30j}</strong></span>
              </div>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">{t('admin.dashboard.kpis.revenue')}</span>
                <TrendingUp className="h-5 w-5 text-secondary" />
              </div>
              <p className="text-2xl font-black text-secondary tabular-nums">{formatXAF(kpis.finances.chiffre_affaires_abonnements)}</p>
              <p className="text-xs text-muted-foreground mt-2">{t('admin.dashboard.kpis.total_volume_label')} {formatXAF(kpis.finances.volume_total_transactions)}</p>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">{t('admin.dashboard.kpis.payer_conversion')}</span>
                <Zap className="h-5 w-5 text-forest-500 dark:text-forest-400" />
              </div>
              <p className="text-3xl font-black text-forest-500 dark:text-forest-400 tabular-nums">{kpis.abonnements.taux_conversion_payant_pourcent}%</p>
              <p className="text-xs text-muted-foreground mt-2">{t('admin.dashboard.kpis.payers_label')} {kpis.abonnements.abonnes_essentiel + kpis.abonnements.abonnes_premium} {t('admin.dashboard.kpis.subscribers_suffix')}</p>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">{t('admin.dashboard.kpis.fraud_alerts')}</span>
                <AlertOctagon className="h-5 w-5 text-destructive" />
              </div>
              <p className="text-3xl font-black text-destructive tabular-nums">{kpis.securite.transactions_suspectes_count}</p>
              <p className="text-xs font-semibold text-destructive mt-2">{t('admin.dashboard.kpis.amount_at_risk')} {formatXAF(kpis.securite.montant_total_suspect)}</p>
            </div>
          </div>
        </div>
      )}

      {/* 👥 MODULE 1 : GESTION DES CLIENTS */}
      {!isLoading && activeTab === 'clients' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">{t('admin.dashboard.clients.title')}</h2>
              <p className="text-xs text-muted-foreground">{t('admin.dashboard.clients.subtitle')}</p>
            </div>
          </div>

          <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
            <div className="p-4 border-b border-border flex items-center justify-between gap-4">
              <div className="relative flex-1 max-w-md">
                <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
                <input
                  type="text"
                  placeholder={t('admin.dashboard.clients.search_placeholder')}
                  className="w-full bg-background border border-border rounded-xl pl-9 pr-4 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase font-bold text-[10px]">
                <tr>
                  <th className="p-4">{t('admin.dashboard.common.th_client')}</th>
                  <th className="p-4">{t('auth.phone')}</th>
                  <th className="p-4">{t('admin.dashboard.clients.th_main_balance')}</th>
                  <th className="p-4">{t('admin.dashboard.common.th_plan')}</th>
                  <th className="p-4">{t('admin.dashboard.common.th_status')}</th>
                  <th className="p-4 text-right">{t('admin.dashboard.common.th_actions')}</th>
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
                          <CheckCircle2 className="h-3 w-3" /> {t('admin.dashboard.common.active')}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 bg-destructive/10 text-destructive px-2 py-0.5 rounded-full font-bold text-[10px]">
                          <XCircle className="h-3 w-3" /> {t('admin.dashboard.common.suspended')}
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        onClick={() => setIdClientDetail(c.id_client)}
                        className="p-1.5 rounded-lg bg-muted hover:bg-accent text-foreground border border-border text-[11px] font-bold inline-flex items-center gap-1"
                      >
                        <UserCog className="h-3 w-3" />
                        <span>{t('admin.dashboard.clients.details')}</span>
                      </button>
                      <button
                        onClick={() => handleToggleClientStatus(c.id_client, c.est_actif)}
                        className={`p-1.5 rounded-lg border text-[11px] font-bold ${
                          c.est_actif ? 'bg-destructive/10 text-destructive border-destructive/20' : 'bg-forest-500/10 text-forest-600 border-forest-500/20'
                        }`}
                      >
                        {c.est_actif ? t('admin.dashboard.common.suspend') : t('common.reactivate')}
                      </button>
                      <button
                        onClick={() => handleTriggerResetPassword(c.id_client, `${c.first_name} ${c.last_name}`)}
                        className="p-1.5 rounded-lg bg-primary/10 text-primary border border-primary/20 text-[11px] font-bold"
                      >
                        {t('admin.dashboard.clients.reset_password_btn')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {clients.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">{t('admin.dashboard.clients.none')}</p>}
          </div>
        </div>
      )}

      {/* 🛡️ MODULE 2 : GESTION DES ADMINS */}
      {!isLoading && activeTab === 'admins' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">{t('admin.dashboard.admins.title')}</h2>
              <p className="text-xs text-muted-foreground">{t('admin.dashboard.admins.subtitle')}</p>
            </div>
            <button
              onClick={() => setIsCreateAdminOpen(true)}
              className="bg-primary text-primary-foreground font-bold text-xs py-2.5 px-4 rounded-xl shadow-md hover:bg-primary/90 flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" />
              <span>{t('admin.dashboard.admins.create_btn')}</span>
            </button>
          </div>

          <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase font-bold text-[10px]">
                <tr>
                  <th className="p-4">{t('admin.dashboard.admins.th_admin')}</th>
                  <th className="p-4">{t('admin.dashboard.admins.th_access_level')}</th>
                  <th className="p-4">{t('admin.dashboard.admins.th_created_on')}</th>
                  <th className="p-4">{t('admin.dashboard.common.th_status')}</th>
                  <th className="p-4 text-right">{t('admin.dashboard.common.th_actions')}</th>
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
                        {t('admin.dashboard.admins.level_display', {
                          level: a.niveau_acces,
                          role: a.niveau_acces === 3 ? t('admin.dashboard.admins.role_superadmin') : a.niveau_acces === 2 ? t('admin.dashboard.admins.role_moderator') : t('admin.dashboard.admins.role_support'),
                        })}
                      </span>
                    </td>
                    <td className="p-4">{new Date(a.date_creation).toLocaleDateString('fr-FR')}</td>
                    <td className="p-4">
                      {a.est_actif ? (
                        <span className="inline-flex items-center gap-1 bg-forest-500/10 text-forest-600 dark:text-forest-400 px-2 py-0.5 rounded-full font-bold text-[10px]">
                          {t('admin.dashboard.common.active')}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 bg-destructive/10 text-destructive px-2 py-0.5 rounded-full font-bold text-[10px]">
                          {t('admin.dashboard.common.suspended')}
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        onClick={() => handleUpdateAdminLevel(a.id_administrateur, a.niveau_acces)}
                        className="px-2.5 py-1 rounded-lg bg-primary/10 text-primary text-[11px] font-bold border border-primary/20"
                      >
                        {t('admin.dashboard.admins.change_role')}
                      </button>
                      <button
                        onClick={() => handleToggleAdminStatus(a.id_administrateur, a.est_actif)}
                        className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border inline-flex items-center gap-1 ${
                          a.est_actif ? 'bg-destructive/10 text-destructive border-destructive/20' : 'bg-forest-500/10 text-forest-600 border-forest-500/20'
                        }`}
                      >
                        {a.est_actif ? <ShieldOff className="h-3 w-3" /> : <ShieldCheck className="h-3 w-3" />}
                        <span>{a.est_actif ? t('admin.dashboard.common.suspend') : t('common.reactivate')}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {admins.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">{t('admin.dashboard.admins.none')}</p>}
          </div>
        </div>
      )}

      {/* 📜 MODULE 3 : AUDIT GLOBAL */}
      {!isLoading && activeTab === 'audit' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">{t('admin.dashboard.audit.title')}</h2>
              <p className="text-xs text-muted-foreground">{t('admin.dashboard.audit.subtitle')}</p>
            </div>
          </div>

          {auditStats && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
                <span className="text-xs font-bold text-muted-foreground uppercase">{t('admin.dashboard.audit.total_events')}</span>
                <p className="text-3xl font-black text-primary tabular-nums mt-1">{auditStats.total_logs}</p>
              </div>
              <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
                <span className="text-xs font-bold text-muted-foreground uppercase mb-2 block">{t('admin.dashboard.audit.top_actions')}</span>
                <div className="flex flex-wrap gap-1.5">
                  {auditStats.repartition_actions.slice(0, 6).map((a) => (
                    <span key={a.action} className="text-[10px] font-bold px-2 py-1 rounded-lg bg-primary/10 text-primary">
                      {a.action} <span className="text-muted-foreground">×{a.count}</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase font-bold text-[10px]">
                <tr>
                  <th className="p-4">{t('admin.dashboard.audit.th_id')}</th>
                  <th className="p-4">{t('admin.dashboard.audit.th_user')}</th>
                  <th className="p-4">{t('admin.dashboard.audit.th_action')}</th>
                  <th className="p-4">{t('admin.dashboard.audit.th_resource')}</th>
                  <th className="p-4">{t('admin.dashboard.audit.th_timestamp')}</th>
                  <th className="p-4 text-right">{t('admin.dashboard.audit.th_inspect')}</th>
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
                        <span>{t('admin.dashboard.audit.inspect_json')}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {auditLogs.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">{t('admin.dashboard.audit.none')}</p>}
          </div>
        </div>
      )}

      {/* ⚙️ MODULE 4 : CONFIGURATION SYSTÈME */}
      {!isLoading && activeTab === 'config' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">{t('admin.dashboard.config.title')}</h2>
              <p className="text-xs text-muted-foreground">{t('admin.dashboard.config.subtitle')}</p>
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
                    onClick={() => handleOuvrirEditionConfig(cfg.cle)}
                    className="px-3 py-1.5 rounded-xl bg-primary/10 text-primary border border-primary/20 text-xs font-bold flex items-center gap-1"
                  >
                    <Edit className="h-3.5 w-3.5" />
                    <span>{t('admin.dashboard.config.edit_hot')}</span>
                  </button>
                </div>
              </div>
            ))}
            {configs.length === 0 && <p className="text-xs text-muted-foreground">{t('admin.dashboard.config.none')}</p>}
          </div>
        </div>
      )}

      {/* 💳 MODULE 5 : ABONNEMENTS & PAIEMENTS */}
      {!isLoading && activeTab === 'subscriptions' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">{t('admin.dashboard.subscriptions.title')}</h2>
              <p className="text-xs text-muted-foreground">{t('admin.dashboard.subscriptions.subtitle')}</p>
            </div>
          </div>

          {subscriptionsOverview && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
                <span className="text-xs font-bold text-muted-foreground uppercase">{t('admin.dashboard.subscriptions.total_subscribers')}</span>
                <p className="text-2xl font-black text-primary tabular-nums mt-1">{subscriptionsOverview.total_abonnes}</p>
              </div>
              <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
                <span className="text-xs font-bold text-muted-foreground uppercase">{t('admin.dashboard.subscriptions.revenue')}</span>
                <p className="text-2xl font-black text-secondary tabular-nums mt-1">{formatXAF(subscriptionsOverview.chiffre_affaires_total)}</p>
              </div>
              <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
                <span className="text-xs font-bold text-muted-foreground uppercase mb-1 block">{t('admin.dashboard.subscriptions.by_plan')}</span>
                <div className="flex flex-wrap gap-1.5">
                  {subscriptionsOverview.repartition_plans.map((p) => (
                    <span key={p.nom_plan} className="text-[10px] font-bold px-2 py-1 rounded-lg bg-primary/10 text-primary">
                      {p.nom_plan} ×{p.nombre_abonnes}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="inline-flex rounded-xl bg-muted p-1 gap-1">
              <button
                onClick={() => setModeSubscriptions('abonnements')}
                className={`text-xs font-bold px-4 py-2 rounded-lg transition-colors ${modeSubscriptions === 'abonnements' ? 'bg-card text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
              >
                {t('admin.dashboard.subscriptions.tab_subscriptions')}
              </button>
              <button
                onClick={() => setModeSubscriptions('paiements')}
                className={`text-xs font-bold px-4 py-2 rounded-lg transition-colors ${modeSubscriptions === 'paiements' ? 'bg-card text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
              >
                {t('admin.dashboard.subscriptions.tab_payments')}
              </button>
              <button
                onClick={() => setModeSubscriptions('plans')}
                className={`text-xs font-bold px-4 py-2 rounded-lg transition-colors ${modeSubscriptions === 'plans' ? 'bg-card text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
              >
                {t('admin.dashboard.subscriptions.tab_plans')}
              </button>
            </div>

            {modeSubscriptions === 'plans' && (
              <button
                onClick={handleOuvrirCreationPlan}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-bold shadow-sm hover:bg-primary/90"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>{t('admin.dashboard.subscriptions.new_plan')}</span>
              </button>
            )}
          </div>

          {modeSubscriptions === 'plans' ? (
            <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase font-bold text-[10px]">
                  <tr>
                    <th className="p-4">{t('admin.dashboard.common.th_plan')}</th>
                    <th className="p-4">{t('admin.dashboard.subscriptions.th_monthly_price')}</th>
                    <th className="p-4">{t('admin.dashboard.subscriptions.th_yearly_price')}</th>
                    <th className="p-4">{t('admin.dashboard.subscriptions.th_included_access')}</th>
                    <th className="p-4 text-right">{t('admin.dashboard.common.th_actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border font-medium">
                  {plans.map((p) => (
                    <tr key={p.id_plan} className="hover:bg-muted/30">
                      <td className="p-4 font-black text-primary flex items-center gap-1.5">
                        <Crown className="h-3.5 w-3.5" />
                        <span>{p.nom}</span>
                      </td>
                      <td className="p-4 font-bold text-foreground">{formatXAF(p.prix_mensuel)}</td>
                      <td className="p-4 font-bold text-foreground">{formatXAF(p.prix_annuel)}</td>
                      <td className="p-4">
                        <div className="flex flex-wrap gap-1">
                          {[
                            p.acces_dettes && t('admin.dashboard.subscriptions.access_badges.dettes'),
                            p.acces_epargne && t('admin.dashboard.subscriptions.access_badges.epargne'),
                            p.acces_recurrentes && t('admin.dashboard.subscriptions.access_badges.recurrentes'),
                            p.acces_templates && t('admin.dashboard.subscriptions.access_badges.modeles'),
                            p.acces_analyse && t('admin.dashboard.subscriptions.access_badges.analyse'),
                            p.acces_jarvis && t('admin.dashboard.subscriptions.access_badges.jarvis'),
                            p.acces_rapport && t('admin.dashboard.subscriptions.access_badges.rapports'),
                            p.acces_tontine && t('admin.dashboard.subscriptions.access_badges.tontines'),
                          ].filter(Boolean).map((label) => (
                            <span key={label as string} className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                              {label}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="p-4 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() => handleOuvrirEditionPlan(p)}
                            title={t('admin.dashboard.subscriptions.edit_plan_title')}
                            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-primary"
                          >
                            <Edit className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeletePlan(p)}
                            title={t('admin.dashboard.subscriptions.delete_plan_title')}
                            className="p-1.5 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {plans.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">{t('admin.dashboard.subscriptions.none_plans')}</p>}
            </div>
          ) : modeSubscriptions === 'abonnements' ? (
            <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase font-bold text-[10px]">
                  <tr>
                    <th className="p-4">{t('admin.dashboard.common.th_client')}</th>
                    <th className="p-4">{t('admin.dashboard.subscriptions.th_pricing_plan')}</th>
                    <th className="p-4">{t('admin.dashboard.common.th_status')}</th>
                    <th className="p-4">{t('admin.dashboard.subscriptions.th_cycle')}</th>
                    <th className="p-4">{t('admin.dashboard.subscriptions.th_period')}</th>
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
              {subscriptions.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">{t('admin.dashboard.subscriptions.none_subscriptions')}</p>}
            </div>
          ) : (
            <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase font-bold text-[10px]">
                  <tr>
                    <th className="p-4">{t('admin.dashboard.common.th_client')}</th>
                    <th className="p-4">{t('admin.dashboard.subscriptions.th_requested_plan')}</th>
                    <th className="p-4">{t('transfers.amount')}</th>
                    <th className="p-4">{t('modals.plan_upgrade.reference')}</th>
                    <th className="p-4">{t('admin.dashboard.common.th_status')}</th>
                    <th className="p-4 text-right">{t('admin.dashboard.subscriptions.th_action_single')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border font-medium">
                  {paiements.map((p) => (
                    <tr key={p.id_paiement} className="hover:bg-muted/30">
                      <td className="p-4 font-bold text-foreground">{p.email_client}</td>
                      <td className="p-4 text-primary font-bold">{p.nom_plan_demande} ({p.cycle_facturation})</td>
                      <td className="p-4 font-black">{formatXAF(p.montant)}</td>
                      <td className="p-4 font-mono text-[11px] text-muted-foreground">{p.reference_hrpay}</td>
                      <td className="p-4">
                        <span className={`inline-flex items-center gap-1 font-bold px-2 py-0.5 rounded-full text-[10px] ${
                          p.statut === 'SUCCESS' ? 'bg-forest-500/10 text-forest-600' : p.statut === 'FAILED' ? 'bg-destructive/10 text-destructive' : 'bg-amber-500/10 text-amber-600'
                        }`}>
                          {p.statut}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        {p.statut === 'PENDING' && (
                          <button
                            onClick={() => handleValiderPaiementManuel(p.id_paiement)}
                            className="px-2.5 py-1 rounded-lg bg-primary/10 text-primary text-[11px] font-bold border border-primary/20 inline-flex items-center gap-1"
                          >
                            <CreditCard className="h-3 w-3" />
                            <span>{t('admin.dashboard.subscriptions.validate_manually')}</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {paiements.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">{t('admin.dashboard.subscriptions.none_payments')}</p>}
            </div>
          )}
        </div>
      )}

      {/* 🚨 MODULE 6 : SURVEILLANCE ANTI-FRAUDE */}
      {!isLoading && activeTab === 'fraud' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight text-destructive flex items-center gap-2">
                <AlertOctagon className="h-6 w-6" />
                <span>{t('admin.dashboard.fraud.title')}</span>
              </h2>
              <p className="text-xs text-muted-foreground">{t('admin.dashboard.fraud.subtitle')}</p>
            </div>
          </div>

          {fraudOverview && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
                <span className="text-xs font-bold text-muted-foreground uppercase">{t('analyse.suspicious_transactions')}</span>
                <p className="text-2xl font-black text-destructive tabular-nums mt-1">{fraudOverview.total_transactions_suspectes}</p>
              </div>
              <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
                <span className="text-xs font-bold text-muted-foreground uppercase">{t('admin.dashboard.fraud.clients_concerned')}</span>
                <p className="text-2xl font-black text-primary tabular-nums mt-1">{fraudOverview.nombre_clients_concernes}</p>
              </div>
              <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
                <span className="text-xs font-bold text-muted-foreground uppercase">{t('admin.dashboard.fraud.amount_at_risk')}</span>
                <p className="text-2xl font-black text-destructive tabular-nums mt-1">{formatXAF(fraudOverview.montant_total_suspect)}</p>
              </div>
            </div>
          )}

          <div className="bg-card rounded-2xl border border-destructive/30 overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-destructive/10 border-b border-destructive/20 text-destructive uppercase font-bold text-[10px]">
                <tr>
                  <th className="p-4">{t('admin.dashboard.fraud.th_tx')}</th>
                  <th className="p-4">{t('admin.dashboard.fraud.th_impacted_client')}</th>
                  <th className="p-4">{t('admin.dashboard.fraud.th_description_alert')}</th>
                  <th className="p-4">{t('transfers.amount')}</th>
                  <th className="p-4">{t('common.date')}</th>
                  <th className="p-4 text-right">{t('admin.dashboard.fraud.th_suspicion_action')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-medium">
                {fraudTransactions.map((tx) => (
                  <tr key={tx.id_transaction} className="hover:bg-destructive/5 cursor-pointer" onClick={() => setIdTransactionDetail(tx.id_transaction)}>
                    <td className="p-4 font-mono font-bold">#{tx.id_transaction}</td>
                    <td className="p-4 font-bold text-foreground">{tx.email_client}</td>
                    <td className="p-4">{tx.description ?? tx.nom_categorie ?? '—'}</td>
                    <td className="p-4 font-black text-destructive">{formatXAF(tx.montant)}</td>
                    <td className="p-4 text-muted-foreground">{new Date(tx.date_creation).toLocaleString('fr-FR')}</td>
                    <td className="p-4 text-right">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleToggleFraudStatus(tx.id_transaction, tx.est_suspecte); }}
                        className={`px-3 py-1.5 rounded-xl text-xs font-bold ${
                          tx.est_suspecte ? 'bg-forest-500/10 text-forest-600 border border-forest-500/20' : 'bg-destructive/10 text-destructive border border-destructive/20'
                        }`}
                      >
                        {tx.est_suspecte ? t('admin.dashboard.fraud.lift_suspicion') : t('admin.dashboard.fraud.mark_suspicious')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {fraudTransactions.length === 0 && <p className="p-6 text-center text-xs text-muted-foreground">{t('admin.dashboard.fraud.none')}</p>}
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

      <PlanModal
        isOpen={isPlanModalOpen}
        plan={planEnEdition}
        onClose={() => setIsPlanModalOpen(false)}
        onSubmit={handleSubmitPlan}
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

      <ClientDetailModal
        isOpen={idClientDetail !== null}
        idClient={idClientDetail}
        onClose={() => setIdClientDetail(null)}
        onForced={fetchClients}
      />

      <TransactionSuspecteDetailModal
        isOpen={idTransactionDetail !== null}
        idTransaction={idTransactionDetail}
        onClose={() => setIdTransactionDetail(null)}
      />
    </AdminLayout>
  );
};
