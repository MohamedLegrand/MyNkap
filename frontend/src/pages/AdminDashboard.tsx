import React, { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { AdminLayout } from '../layouts/AdminLayout';
import { api } from '../services/api';
import {
  CreateAdminModal,
  ResetClientPasswordModal,
  EditConfigModal,
  ViewAuditDetailModal,
} from '../components/AdminModals';

export const AdminDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('kpis');

  // Modals state
  const [isCreateAdminOpen, setIsCreateAdminOpen] = useState(false);
  const [isResetPasswordOpen, setIsResetPasswordOpen] = useState(false);
  const [targetClient, setTargetClient] = useState<{ id: number; name: string } | null>(null);
  const [resetPasswordResult, setResetPasswordResult] = useState<string | null>(null);

  const [isEditConfigOpen, setIsEditConfigOpen] = useState(false);
  const [targetConfig, setTargetConfig] = useState<{ key: string; val: string; type: string } | null>(null);

  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);
  const [selectedAuditLog, setSelectedAuditLog] = useState<any>(null);

  // States de données consommant l'API backend
  const [kpis, setKpis] = useState<any>({
    clients: { total_clients: 1250, clients_actifs: 1210, clients_suspendus: 40, nouveaux_clients_30j: 185 },
    finances: { chiffre_affaires_abonnements: '14,250,000 XAF', volume_total_transactions: '450,000,000 XAF', solde_cumule_comptes_principaux: '180,000,000 XAF' },
    abonnements: { abonnes_gratuit: 890, abonnes_essentiel: 260, abonnes_premium: 100, taux_conversion_payant_pourcent: 28.8 },
    securite: { transactions_suspectes_count: 7, montant_total_suspect: '3,850,000 XAF', total_audit_logs: 4890 },
  });

  const [clients, setClients] = useState<any[]>([
    { id_client: 1, email: 'patrick.mboma@mynkap.cm', first_name: 'Patrick', last_name: 'Mboma', phone: '+237699123456', est_actif: true, total_comptes: 3, plan_actif: 'PREMIUM' },
    { id_client: 2, email: 'samuel.eto@mynkap.cm', first_name: 'Samuel', last_name: 'Eto', phone: '+237677987654', est_actif: true, total_comptes: 2, plan_actif: 'ESSENTIEL' },
    { id_client: 3, email: 'rigobert.song@mynkap.cm', first_name: 'Rigobert', last_name: 'Song', phone: '+237699887766', est_actif: false, total_comptes: 1, plan_actif: 'GRATUIT' },
  ]);

  const [admins, setAdmins] = useState<any[]>([
    { id_administrateur: 1, username: 'superadmin_master', email: 'superadmin@mynkap.cm', niveau_acces: 3, est_actif: true, date_creation: '15/01/2026' },
    { id_administrateur: 2, username: 'moderateur_fraude', email: 'moderation@mynkap.cm', niveau_acces: 2, est_actif: true, date_creation: '01/03/2026' },
    { id_administrateur: 3, username: 'support_agent_1', email: 'support@mynkap.cm', niveau_acces: 1, est_actif: true, date_creation: '10/05/2026' },
  ]);

  const [auditLogs] = useState<any[]>([
    { id_log: 1045, utilisateur_email: 'superadmin@mynkap.cm', id_utilisateur: 1, action: 'ADMIN_MODIFIER_CONFIG', ressource: 'Configuration', id_ressource: 4, date_action: '27/07/2026 11:20', donnees_avant: { MAX_TRANSACTION_LIMIT: 5000000 }, donnees_apres: { MAX_TRANSACTION_LIMIT: 10000000 } },
    { id_log: 1044, utilisateur_email: 'moderation@mynkap.cm', id_utilisateur: 2, action: 'ADMIN_SUSPENDRE_CLIENT', ressource: 'Client', id_ressource: 3, date_action: '27/07/2026 10:15', donnees_avant: { est_actif: true }, donnees_apres: { est_actif: false } },
    { id_log: 1043, utilisateur_email: 'patrick.mboma@mynkap.cm', id_utilisateur: 101, action: 'CONNEXION', ressource: 'Utilisateur', id_ressource: 101, date_action: '27/07/2026 09:45', donnees_avant: null, donnees_apres: { ip: '197.234.221.15' } },
  ]);

  const [configs, setConfigs] = useState<any[]>([
    { cle: 'MAX_TRANSACTION_LIMIT', valeur: '10000000', type_donnee: 'INT', description: 'Plafond maximum par transaction unique (XAF)' },
    { cle: 'FRAUD_SUSPICION_THRESHOLD', valeur: '2000000', type_donnee: 'INT', description: 'Seuil de déclenchement d\'alerte de suspicion (XAF)' },
    { cle: 'MAX_LOGIN_ATTEMPTS', valeur: '5', type_donnee: 'INT', description: 'Nombre de tentatives de connexion avant blocage IP' },
    { cle: 'MAINTENANCE_MODE', valeur: 'false', type_donnee: 'BOOL', description: 'Bascule du site en mode maintenance technique' },
  ]);

  const [subscriptions] = useState<any[]>([
    { id_client: 1, client_email: 'patrick.mboma@mynkap.cm', plan: 'PREMIUM', statut: 'ACTIF', date_debut: '01/07/2026', date_fin: '01/08/2026', montant: '10,000 XAF' },
    { id_client: 2, client_email: 'samuel.eto@mynkap.cm', plan: 'ESSENTIEL', statut: 'ACTIF', date_debut: '15/07/2026', date_fin: '15/08/2026', montant: '3,500 XAF' },
  ]);

  const [fraudTransactions, setFraudTransactions] = useState<any[]>([
    { id_transaction: 894, client_email: 'rigobert.song@mynkap.cm', type: 'DEPENSE', montant: '3,500,000 XAF', description: 'Virement externe inhabituel', est_suspecte: true, date: '26/07/2026 22:40' },
    { id_transaction: 890, client_email: 'inconnu_user@mynkap.cm', type: 'DEPENSE', montant: '5,000,000 XAF', description: 'Retrait Orange Money nocturne', est_suspecte: true, date: '25/07/2026 03:15' },
  ]);

  // Consommation des endpoints lors du chargement
  useEffect(() => {
    fetchAdminKPIs();
  }, []);

  const fetchAdminKPIs = async () => {
    try {
      const res = await api.request<any>('/admin/kpis');
      if (res) setKpis(res);
    } catch {
      // conserver mock data si hors ligne
    }
  };

  // Actions Clients (Module 1)
  const handleToggleClientStatus = (id: number) => {
    setClients(prev =>
      prev.map(c => (c.id_client === id ? { ...c, est_actif: !c.est_actif } : c))
    );
  };

  const handleTriggerResetPassword = (id: number, name: string) => {
    setTargetClient({ id, name });
    setResetPasswordResult(null);
    setIsResetPasswordOpen(true);
  };

  const handleConfirmResetPassword = () => {
    // Génération d'un mot de passe temporaire
    const tempPass = `MyNkap@${Math.floor(100000 + Math.random() * 900000)}`;
    setResetPasswordResult(tempPass);
  };

  // Actions Admin (Module 2)
  const handleCreateAdminSubmit = (data: any) => {
    const newAdmin = {
      id_administrateur: admins.length + 1,
      username: data.username,
      email: data.email,
      niveau_acces: data.niveau_acces,
      est_actif: true,
      date_creation: new Date().toLocaleDateString(),
    };
    setAdmins(prev => [...prev, newAdmin]);
  };

  const handleUpdateAdminLevel = (id: number, currentLevel: number) => {
    const nextLevel = currentLevel >= 3 ? 1 : currentLevel + 1;
    setAdmins(prev =>
      prev.map(a => (a.id_administrateur === id ? { ...a, niveau_acces: nextLevel } : a))
    );
  };

  // Actions Config (Module 4)
  const handleSaveConfig = (newVal: string) => {
    if (!targetConfig) return;
    setConfigs(prev =>
      prev.map(cfg => (cfg.cle === targetConfig.key ? { ...cfg, valeur: newVal } : cfg))
    );
  };

  // Actions Anti-Fraude (Module 6)
  const handleToggleFraudStatus = (idTx: number) => {
    setFraudTransactions(prev =>
      prev.map(tx => (tx.id_transaction === idTx ? { ...tx, est_suspecte: !tx.est_suspecte } : tx))
    );
  };

  return (
    <AdminLayout activeTab={activeTab} onTabChange={setActiveTab}>
      {/* 📊 MODULE 7 : TABLEAU DE BORD KPIS GLOBAUX */}
      {activeTab === 'kpis' && (
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
            {/* KPI Clients */}
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">Base Clients</span>
                <Users className="h-5 w-5 text-primary" />
              </div>
              <p className="text-3xl font-black text-primary tabular-nums">{kpis.clients.total_clients}</p>
              <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                <span>Actifs : <strong className="text-emerald-600 dark:text-emerald-400">{kpis.clients.clients_actifs}</strong></span>
                <span>Nouveaux +30j : <strong className="text-secondary">+{kpis.clients.nouveaux_clients_30j}</strong></span>
              </div>
            </div>

            {/* KPI CA Abonnements */}
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">Chiffre d'Affaires</span>
                <TrendingUp className="h-5 w-5 text-secondary" />
              </div>
              <p className="text-2xl font-black text-secondary tabular-nums">{kpis.finances.chiffre_affaires_abonnements}</p>
              <p className="text-xs text-muted-foreground mt-2">Volume total : {kpis.finances.volume_total_transactions}</p>
            </div>

            {/* KPI Conversions */}
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">Conversion Payant</span>
                <Zap className="h-5 w-5 text-amber-500" />
              </div>
              <p className="text-3xl font-black text-amber-500 tabular-nums">{kpis.abonnements.taux_conversion_payant_pourcent}%</p>
              <p className="text-xs text-muted-foreground mt-2">Payants : {kpis.abonnements.abonnes_essentiel + kpis.abonnements.abonnes_premium} abonnés</p>
            </div>

            {/* KPI Risque Anti-Fraude */}
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">Alertes Fraude</span>
                <AlertOctagon className="h-5 w-5 text-destructive" />
              </div>
              <p className="text-3xl font-black text-destructive tabular-nums">{kpis.securite.transactions_suspectes_count}</p>
              <p className="text-xs font-semibold text-destructive mt-2">Montant à risque : {kpis.securite.montant_total_suspect}</p>
            </div>
          </div>
        </div>
      )}

      {/* 👥 MODULE 1 : GESTION DES CLIENTS */}
      {activeTab === 'clients' && (
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
                  className="w-full bg-background border border-border rounded-xl pl-9 pr-4 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-amber-500"
                />
              </div>
            </div>

            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase font-bold text-[10px]">
                <tr>
                  <th className="p-4">Client</th>
                  <th className="p-4">Téléphone</th>
                  <th className="p-4">Comptes</th>
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
                    <td className="p-4"><span className="font-bold">{c.total_comptes}</span> comptes</td>
                    <td className="p-4">
                      <span className="bg-primary/10 text-primary font-bold px-2 py-0.5 rounded text-[10px]">
                        {c.plan_actif}
                      </span>
                    </td>
                    <td className="p-4">
                      {c.est_actif ? (
                        <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 rounded-full font-bold text-[10px]">
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
                        onClick={() => handleToggleClientStatus(c.id_client)}
                        className={`p-1.5 rounded-lg border text-[11px] font-bold ${
                          c.est_actif ? 'bg-destructive/10 text-destructive border-destructive/20' : 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                        }`}
                      >
                        {c.est_actif ? 'Suspendre' : 'Réactiver'}
                      </button>
                      <button
                        onClick={() => handleTriggerResetPassword(c.id_client, `${c.first_name} ${c.last_name}`)}
                        className="p-1.5 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 text-[11px] font-bold"
                      >
                        Reset Password
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 🛡️ MODULE 2 : GESTION DES ADMINS */}
      {activeTab === 'admins' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="flex justify-between items-center pb-2 border-b border-border">
            <div>
              <h2 className="text-xl font-black tracking-tight">Équipe Administrateur (Module 2)</h2>
              <p className="text-xs text-muted-foreground">Gestion des accès d'administration et attribution des rôles</p>
            </div>
            <button
              onClick={() => setIsCreateAdminOpen(true)}
              className="bg-amber-500 text-slate-950 font-bold text-xs py-2.5 px-4 rounded-xl shadow-md hover:bg-amber-400 flex items-center gap-1.5"
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
                        a.niveau_acces === 3 ? 'bg-amber-500/20 text-amber-500 border border-amber-500/30' : 'bg-muted text-muted-foreground'
                      }`}>
                        Niveau {a.niveau_acces} ({a.niveau_acces === 3 ? 'Superadmin' : a.niveau_acces === 2 ? 'Modérateur' : 'Support'})
                      </span>
                    </td>
                    <td className="p-4">{a.date_creation}</td>
                    <td className="p-4">
                      <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 rounded-full font-bold text-[10px]">
                        Actif
                      </span>
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
          </div>
        </div>
      )}

      {/* 📜 MODULE 3 : AUDIT GLOBAL */}
      {activeTab === 'audit' && (
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
                  <tr key={log.id_log} className="hover:bg-muted/30">
                    <td className="p-4 font-mono font-bold text-muted-foreground">#{log.id_log}</td>
                    <td className="p-4 font-bold text-foreground">{log.utilisateur_email}</td>
                    <td className="p-4">
                      <span className="bg-primary/10 text-primary font-mono font-bold px-2 py-0.5 rounded text-[10px]">
                        {log.action}
                      </span>
                    </td>
                    <td className="p-4">{log.ressource} (#{log.id_ressource})</td>
                    <td className="p-4 text-muted-foreground">{log.date_action}</td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => { setSelectedAuditLog(log); setIsAuditModalOpen(true); }}
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
          </div>
        </div>
      )}

      {/* ⚙️ MODULE 4 : CONFIGURATION SYSTÈME */}
      {activeTab === 'config' && (
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
                    {cfg.type_donnee}
                  </span>
                </div>

                <div className="pt-2 flex items-center justify-between border-t border-border">
                  <span className="font-mono text-sm font-black text-amber-500">{cfg.valeur}</span>
                  <button
                    onClick={() => {
                      setTargetConfig({ key: cfg.cle, val: cfg.valeur, type: cfg.type_donnee });
                      setIsEditConfigOpen(true);
                    }}
                    className="px-3 py-1.5 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 text-xs font-bold flex items-center gap-1"
                  >
                    <Edit className="h-3.5 w-3.5" />
                    <span>Modifier à chaud</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 💳 MODULE 5 : ABONNEMENTS & PAIEMENTS */}
      {activeTab === 'subscriptions' && (
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
                  <th className="p-4">Période</th>
                  <th className="p-4">Montant</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-medium">
                {subscriptions.map((sub, idx) => (
                  <tr key={idx} className="hover:bg-muted/30">
                    <td className="p-4 font-bold text-foreground">{sub.client_email}</td>
                    <td className="p-4 font-bold text-primary">{sub.plan}</td>
                    <td className="p-4">
                      <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-600 font-bold px-2 py-0.5 rounded-full text-[10px]">
                        {sub.statut}
                      </span>
                    </td>
                    <td className="p-4 text-muted-foreground">{sub.date_debut} ➔ {sub.date_fin}</td>
                    <td className="p-4 font-black text-foreground">{sub.montant}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 🚨 MODULE 6 : SURVEILLANCE ANTI-FRAUDE */}
      {activeTab === 'fraud' && (
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
                    <td className="p-4 font-bold text-foreground">{tx.client_email}</td>
                    <td className="p-4">{tx.description}</td>
                    <td className="p-4 font-black text-destructive">{tx.montant}</td>
                    <td className="p-4 text-muted-foreground">{tx.date}</td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => handleToggleFraudStatus(tx.id_transaction)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-bold ${
                          tx.est_suspecte ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20' : 'bg-destructive/10 text-destructive border border-destructive/20'
                        }`}
                      >
                        {tx.est_suspecte ? 'Lever la suspicion' : 'Marquer Suspecte'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
        auditItem={selectedAuditLog}
        onClose={() => setIsAuditModalOpen(false)}
      />
    </AdminLayout>
  );
};
