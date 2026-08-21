import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Bot,
  PieChart,
  PiggyBank,
  AlertTriangle,
  CheckCircle2,
  Phone,
  Building2,
  Coins,
  Loader2,
  Tag,
  HandCoins,
  Filter,
  Ban,
  Download,
  FileText,
  Clock,
  Crown,
  ArrowRightLeft,
  MoreVertical,
  Pencil,
  RefreshCw,
  Power,
  PowerOff,
  X,
  Trash2,
  Users,
  MessageSquareHeart,
} from 'lucide-react';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { TransactionModal } from '../components/TransactionModal';
import { PlanUpgradeModal } from '../components/PlanUpgradeModal';
import { CompteModal } from '../components/CompteModal';
import { TransfertModal } from '../components/TransfertModal';
import { CategorieModal } from '../components/CategorieModal';
import { BudgetModal } from '../components/BudgetModal';
import { DetteModal } from '../components/DetteModal';
import { DetteOperationModal } from '../components/DetteOperationModal';
import { ObjectifModal } from '../components/ObjectifModal';
import { ObjectifOperationModal } from '../components/ObjectifOperationModal';
import { JarvisWidget } from '../components/JarvisWidget';
import { TransactionDetailModal } from '../components/TransactionDetailModal';
import { AutomatisationsSection } from '../components/AutomatisationsSection';
import { AnalyseSection } from '../components/AnalyseSection';
import { CategorieBadge } from '../components/CategorieBadge';
import { TontineModal } from '../components/TontineModal';
import { TontineDetailModal } from '../components/TontineDetailModal';
import { AvisModal } from '../components/AvisModal';
import { SettingsSection } from '../components/SettingsSection';
import { api } from '../services/api';
import { useAuthStore } from '../store';
import { LockedFeatureBanner } from '../components/LockedFeatureBanner';
import type {
  Abonnement,
  CompteFinancier,
  ComptePrincipal,
  Transaction,
  Categorie,
  Budget,
  ObjectifEpargne,
  Dette,
  Rapport,
  Transfert,
  Tontine,
  DonneesVerrouillees,
  Avis,
} from '../types';

const ICONS_PAR_TYPE_COMPTE: Record<string, React.ReactNode> = {
  MOBILE_MONEY: <Phone className="h-4 w-4" />,
  BANCAIRE: <Building2 className="h-4 w-4" />,
  ESPECES: <Coins className="h-4 w-4" />,
  EPARGNE: <PiggyBank className="h-4 w-4" />,
};

const formatMontant = (valeur: number) => `${valeur.toLocaleString('fr-FR')} XAF`;

// Nombre de jours restants avant la fin de l'essai — même principe que
// DashboardLayout.joursRestants (arrondi au jour supérieur).
const joursRestantsEssai = (dateFin: string): number =>
  Math.max(0, Math.ceil((new Date(dateFin).getTime() - Date.now()) / 86_400_000));

export const ClientDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('overview');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isUpgradeModalOpen, setIsUpgradeModalOpen] = useState(false);
  const [essaiConfirme, setEssaiConfirme] = useState(false);
  const [isCompteModalOpen, setIsCompteModalOpen] = useState(false);
  const [compteEnEdition, setCompteEnEdition] = useState<CompteFinancier | null>(null);
  const [compteActionError, setCompteActionError] = useState<string | null>(null);
  const [isTransfertModalOpen, setIsTransfertModalOpen] = useState(false);
  const [isCategorieModalOpen, setIsCategorieModalOpen] = useState(false);
  const [isBudgetModalOpen, setIsBudgetModalOpen] = useState(false);
  const [categorieEnEdition, setCategorieEnEdition] = useState<Categorie | null>(null);
  const [budgetEnEdition, setBudgetEnEdition] = useState<Budget | null>(null);
  const [transactionDetailId, setTransactionDetailId] = useState<number | null>(null);
  const [isDetteModalOpen, setIsDetteModalOpen] = useState(false);
  const [isObjectifModalOpen, setIsObjectifModalOpen] = useState(false);
  const [isTontineModalOpen, setIsTontineModalOpen] = useState(false);
  const [idTontineDetail, setIdTontineDetail] = useState<number | null>(null);
  const [detteOperation, setDetteOperation] = useState<Dette | null>(null);
  const [objectifOperation, setObjectifOperation] = useState<{ objectif: ObjectifEpargne; operation: 'alimenter' | 'retirer' | 'abandonner' } | null>(null);
  const client = useAuthStore((state) => state.client);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [abonnement, setAbonnement] = useState<Abonnement | null>(null);
  const [donneesVerrouillees, setDonneesVerrouillees] = useState<DonneesVerrouillees | null>(null);
  const [comptePrincipal, setComptePrincipal] = useState<ComptePrincipal | null>(null);
  const [comptes, setComptes] = useState<CompteFinancier[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Categorie[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [objectifsEpargne, setObjectifsEpargne] = useState<ObjectifEpargne[]>([]);
  const [dettes, setDettes] = useState<Dette[]>([]);
  const [tontines, setTontines] = useState<Tontine[]>([]);
  const [rapports, setRapports] = useState<Rapport[]>([]);
  const [transferts, setTransferts] = useState<Transfert[]>([]);
  const [transfertDetailId, setTransfertDetailId] = useState<number | null>(null);
  const [transfertDetail, setTransfertDetail] = useState<Transfert | null>(null);
  const [isLoadingTransfertDetail, setIsLoadingTransfertDetail] = useState(false);
  const [monAvis, setMonAvis] = useState<Avis | null>(null);
  const [isAvisModalOpen, setIsAvisModalOpen] = useState(false);

  const chargerAbonnement = useCallback(async () => {
    try {
      setAbonnement(await api.request<Abonnement>('/abonnement'));
    } catch {
      setAbonnement(null);
    }
  }, []);

  const chargerMonAvis = useCallback(async () => {
    // Sert uniquement à savoir si la bannière d'invitation à laisser un
    // avis doit s'afficher (masquée dès qu'un avis existe, quel que soit
    // son statut de modération) — voir la section juste après le bandeau
    // d'essai Premium ci-dessous.
    try {
      setMonAvis(await api.request<Avis | null>('/avis/moi'));
    } catch {
      setMonAvis(null);
    }
  }, []);

  const verifierInvitationAvis = useCallback(async () => {
    // Ouvre activement la modale (pas seulement la bannière passive)
    // quand le backend juge le moment opportun — ancienneté suffisante,
    // pas d'avis déjà soumis, pas de report en cours (voir
    // avis.service.doit_demander_avis). Un échec réseau ici ne doit
    // jamais bloquer le chargement du reste du tableau de bord.
    try {
      const { demander } = await api.request<{ demander: boolean }>('/avis/invitation');
      if (demander) setIsAvisModalOpen(true);
    } catch {
      // Silencieux : au pire on ne propose pas activement cette fois-ci,
      // la bannière reste de toute façon disponible.
    }
  }, []);

  const chargerDonneesVerrouillees = useCallback(async () => {
    // Toujours accessible quel que soit le forfait (voir GET
    // /abonnement/donnees-verrouillees, non gaté) : sert uniquement à
    // afficher « vous avez N éléments enregistrés » sur les modules dont
    // l'accès a été restreint, jamais les données elles-mêmes.
    try {
      setDonneesVerrouillees(await api.request<DonneesVerrouillees>('/abonnement/donnees-verrouillees'));
    } catch {
      setDonneesVerrouillees(null);
    }
  }, []);

  const chargerDonnees = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [cp, listeComptes, listeTransactions, listeCategories, listeBudgets] = await Promise.all([
        api.request<ComptePrincipal>('/comptes/principal'),
        // include_inactifs=true : les comptes désactivés restent visibles
        // dans "Mes Comptes" (badge + bouton Réactiver) plutôt que de
        // disparaître silencieusement après une désactivation.
        api.request<CompteFinancier[]>('/comptes?include_inactifs=true'),
        api.request<Transaction[]>('/transactions'),
        // Idem catégories/budgets : les éléments désactivés restent visibles
        // (badge + Réactiver) dans l'onglet Budgets & Alertes.
        api.request<Categorie[]>('/categories?include_inactifs=true'),
        api.request<Budget[]>('/budgets?include_inactifs=true'),
      ]);
      setComptePrincipal(cp);
      setComptes(listeComptes);
      setTransactions(listeTransactions);
      setCategories(listeCategories);
      setBudgets(listeBudgets);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : t('common.error_load_dashboard'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const chargerRapports = useCallback(async () => {
    try {
      setRapports(await api.request<Rapport[]>('/rapports'));
    } catch {
      setRapports([]);
    }
  }, []);

  useEffect(() => {
    // Chargement au montage, pas une synchronisation d'état dérivé.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    chargerDonnees();
    chargerAbonnement();
    chargerDonneesVerrouillees();
    chargerRapports();
    chargerMonAvis();
    verifierInvitationAvis();
  }, [chargerDonnees, chargerAbonnement, chargerDonneesVerrouillees, chargerRapports, chargerMonAvis, verifierInvitationAvis]);

  useEffect(() => {
    // Ne tente /epargne que si le forfait y donne accès — évite un 403
    // systématique (et inutile, déjà géré comme "aucun objectif") pour un
    // client GRATUIT ou STANDARD à chaque chargement du dashboard. Pas une
    // synchronisation d'état dérivé : dépend d'un appel réseau.
    if (!abonnement?.plan.acces_epargne) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setObjectifsEpargne([]);
      return;
    }
    api
      .request<ObjectifEpargne[]>('/epargne')
      .then(setObjectifsEpargne)
      .catch(() => setObjectifsEpargne([]));
  }, [abonnement]);

  useEffect(() => {
    // Même principe que pour l'épargne juste au-dessus — évite un 403
    // systématique pour un client sans accès au palier Dettes.
    if (!abonnement?.plan.acces_dettes) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDettes([]);
      return;
    }
    api
      .request<Dette[]>('/dettes')
      .then(setDettes)
      .catch(() => setDettes([]));
  }, [abonnement]);

  const fetchTontines = useCallback(() => {
    api
      .request<Tontine[]>('/tontines')
      .then(setTontines)
      .catch(() => setTontines([]));
  }, []);

  useEffect(() => {
    // Chargé seulement en visitant l'onglet Tontines (pas nécessaire ailleurs
    // dans le dashboard, contrairement aux dettes) — même garde-fou de plan
    // que les effets ci-dessus.
    if (activeTab !== 'tontines' || !abonnement?.plan.acces_tontine) return;
    fetchTontines();
  }, [activeTab, abonnement, fetchTontines]);

  useEffect(() => {
    // Chargé seulement en visitant "Mes Comptes" — pas de gating de plan
    // ici (les transferts sont gratuits), donc pas besoin de dépendre de
    // l'abonnement comme épargne/dettes ci-dessus.
    if (activeTab !== 'accounts') return;
    api
      .request<Transfert[]>('/transferts')
      .then(setTransferts)
      .catch(() => setTransferts([]));
  }, [activeTab]);

  useEffect(() => {
    // Relit le transfert depuis le serveur à l'ouverture de son détail —
    // pas une synchronisation d'état dérivé.
    if (transfertDetailId === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setTransfertDetail(null);
      return;
    }
    setIsLoadingTransfertDetail(true);
    api
      .request<Transfert>(`/transferts/${transfertDetailId}`)
      .then(setTransfertDetail)
      .catch(() => setTransfertDetail(null))
      .finally(() => setIsLoadingTransfertDetail(false));
  }, [transfertDetailId]);

  const nomCategorie = (idCategorie: number | null) =>
    categories.find((c) => c.id_categorie === idCategorie)?.nom ?? t('common.uncategorized');
  const categorieParId = (idCategorie: number | null) =>
    categories.find((c) => c.id_categorie === idCategorie);
  const nomCompte = (idCompte: number) => comptes.find((c) => c.id_compte === idCompte)?.nom ?? '—';
  const peutAnnulerTransaction = (id: number) => {
    const tx = transactions.find((t) => t.id_transaction === id);
    if (!tx || tx.type === 'ANNULATION') return false;
    return !transactions.some((t) => t.id_transaction_annulee === id);
  };

  const toggleActifCategorie = async (categorie: Categorie) => {
    setLoadError(null);
    try {
      if (categorie.est_actif) {
        await api.request(`/categories/${categorie.id_categorie}`, { method: 'DELETE' });
      } else {
        await api.request(`/categories/${categorie.id_categorie}/reactiver`, { method: 'POST' });
      }
      chargerDonnees();
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : t('common.error_action'));
    }
  };

  const toggleActifBudget = async (budget: Budget) => {
    setLoadError(null);
    try {
      if (budget.est_actif) {
        await api.request(`/budgets/${budget.id_budget}`, { method: 'DELETE' });
      } else {
        await api.request(`/budgets/${budget.id_budget}/reactiver`, { method: 'POST' });
      }
      chargerDonnees();
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : t('common.error_action'));
    }
  };

  const marquerDettePerte = async (dette: Dette) => {
    if (!window.confirm(t('debts.confirm_write_off', { nom: dette.nom }))) return;
    try {
      await api.request(`/dettes/${dette.id_dette}/marquer-perte`, { method: 'POST' });
      api.request<Dette[]>('/dettes').then(setDettes).catch(() => {});
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : t('common.error_action'));
    }
  };

  const supprimerDette = async (dette: Dette) => {
    if (!window.confirm(t('debts.confirm_delete', { nom: dette.nom }))) return;
    try {
      await api.request(`/dettes/${dette.id_dette}`, { method: 'DELETE' });
      setDettes((prev) => prev.filter((d) => d.id_dette !== dette.id_dette));
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : t('common.error_delete'));
    }
  };

  const reconcilierCompte = async (compte: CompteFinancier) => {
    setCompteActionError(null);
    try {
      await api.request(`/comptes/${compte.id_compte}/reconcilier`, { method: 'POST' });
      chargerDonnees();
    } catch (err) {
      setCompteActionError(err instanceof Error ? err.message : t('accounts.error_reconcile'));
    }
  };

  const toggleActifCompte = async (compte: CompteFinancier) => {
    setCompteActionError(null);
    try {
      if (compte.est_actif) {
        await api.request(`/comptes/${compte.id_compte}`, { method: 'DELETE' });
      } else {
        await api.request(`/comptes/${compte.id_compte}/reactiver`, { method: 'POST' });
      }
      chargerDonnees();
    } catch (err) {
      setCompteActionError(err instanceof Error ? err.message : t('common.error_action'));
    }
  };

  const transactionsRecentes = [...transactions]
    .sort((a, b) => new Date(b.date_creation).getTime() - new Date(a.date_creation).getTime())
    .slice(0, 5);

  const revenusDuMois = transactions
    .filter((t) => t.type === 'REVENU')
    .reduce((total, t) => total + Number(t.montant), 0);
  const depensesDuMois = transactions
    .filter((t) => t.type === 'DEPENSE')
    .reduce((total, t) => total + Number(t.montant), 0);
  const totalEpargne = objectifsEpargne.reduce((total, o) => total + Number(o.montant_actuel), 0);
  const dettesActives = dettes.filter((d) => d.type === 'DETTE' && d.statut !== 'SOLDE' && d.statut !== 'PERTE');
  const totalDettesDues = dettesActives.reduce((total, d) => total + Number(d.montant_restant), 0);
  // Cartes "Réserves Épargne" et "Dettes en Cours" : invisibles tant que le
  // client n'a encore rien créé dans ces modules, plutôt que d'afficher un
  // 0 en permanence dès l'inscription — apparaissent dynamiquement à la
  // première création (objectif d'épargne / dette).
  const afficherCarteEpargne = !!abonnement?.plan.acces_epargne && objectifsEpargne.length > 0;
  const afficherCarteDettes = !!abonnement?.plan.acces_dettes && dettesActives.length > 0;
  const nombreCartesHero = 3 + (afficherCarteEpargne ? 1 : 0) + (afficherCarteDettes ? 1 : 0);
  // "Mes Comptes" affiche aussi les comptes désactivés (badge + Réactiver) ;
  // partout ailleurs (totaux, sélecteurs de transfert/dette/épargne), seuls
  // les comptes actifs ont un sens. Même principe pour les budgets dans
  // l'aperçu "Vue d'ensemble".
  const comptesActifs = comptes.filter((c) => c.est_actif);
  const budgetsActifs = budgets.filter((b) => b.est_actif);

  return (
    <DashboardLayout
      activeTab={activeTab}
      onTabChange={setActiveTab}
      onOpenUpgradeModal={() => setIsUpgradeModalOpen(true)}
      plan={abonnement?.plan}
      abonnement={abonnement}
      nombreComptes={comptesActifs.length}
    >
      {/* Bannière de bienvenue, bandeaux et cartes de synthèse : réservés à
          la Vue d'ensemble — les autres sections (Comptes, Paramètres...)
          affichent directement leur propre contenu, sans ce récapitulatif. */}
      {activeTab === 'overview' && (
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-primary via-forest-600 to-secondary p-6 sm:p-8 text-white shadow-xl">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight">
              {t('overview.greeting', { nom: client?.first_name ?? '' })}
            </h2>
            <p className="text-sm text-white/80 max-w-xl leading-relaxed">
              {t('overview.summary_prefix')}{' '}
              <strong className="text-violet-300 font-black text-base">
                {comptePrincipal ? formatMontant(Number(comptePrincipal.solde_total)) : '—'}
              </strong>{' '}
              {t('overview.summary_suffix', { count: comptesActifs.length })}
            </p>
          </div>

          {/* La transaction (barre du haut) et l'upgrade (barre latérale) ont
              chacun un emplacement unique ailleurs dans le dashboard — seule
              l'action propre à cette bannière (JARVIS) reste ici, pour
              éviter les boutons redondants à plusieurs endroits de l'écran. */}
          {abonnement?.plan.acces_jarvis && (
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => document.getElementById('jarvis-widget')?.scrollIntoView({ behavior: 'smooth' })}
                className="bg-white/15 hover:bg-white/25 text-white font-bold text-xs py-3 px-5 rounded-xl border border-white/25 backdrop-blur-md transition-all flex items-center gap-2"
              >
                <Bot className="h-4 w-4" />
                <span>{t('overview.ask_jarvis')}</span>
              </button>
            </div>
          )}
        </div>
      </div>
      )}

      {/* Bandeau d'annonce de l'essai Premium 30 jours — l'accès est déjà
          actif automatiquement dès l'inscription (voir creer_abonnement_essai
          côté backend) ; ce bandeau ne fait que le mettre clairement en
          avant, en plus du badge discret de la barre latérale. */}
      {activeTab === 'overview' && abonnement?.statut === 'ESSAI' && abonnement.date_fin && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-5 rounded-2xl border border-primary/20 bg-primary/5">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary shrink-0">
              <Crown className="h-5 w-5" />
            </div>
            <p className="text-sm text-foreground">
              <strong className="font-bold">{t('overview.trial_banner_bold')}</strong> {t('overview.trial_banner_part1')}{' '}
              <strong className="text-primary">
                {t('dashboard.days_count', { count: joursRestantsEssai(abonnement.date_fin) })}
              </strong>
              . {t('overview.trial_banner_part2')}
            </p>
          </div>
          <div className="flex flex-col items-center sm:items-end gap-1.5 shrink-0">
            <button
              onClick={async () => {
                try {
                  await api.request('/abonnement/notifier-essai', { method: 'POST' });
                  setEssaiConfirme(true);
                } catch {
                  // La confirmation est secondaire : un échec réseau ne doit
                  // pas empêcher d'ouvrir la fenêtre de forfait ci-dessous.
                }
                setIsUpgradeModalOpen(true);
              }}
              className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2.5 px-5 rounded-xl shadow-md transition-all whitespace-nowrap"
            >
              {t('overview.enjoy_premium')}
            </button>
            {essaiConfirme && (
              <span className="text-[11px] font-semibold text-forest-600 dark:text-forest-400 flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" />
                {t('overview.access_confirmed')}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Invitation à laisser un avis — disparaît définitivement dès qu'un
          avis existe (peu importe son statut de modération), voir
          chargerMonAvis ci-dessus. */}
      {activeTab === 'overview' && monAvis === null && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-5 rounded-2xl border border-border bg-muted/40">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-secondary/10 text-secondary shrink-0">
              <MessageSquareHeart className="h-5 w-5" />
            </div>
            <p className="text-sm text-foreground">{t('overview.avis_prompt')}</p>
          </div>
          <button
            onClick={() => setIsAvisModalOpen(true)}
            className="bg-card hover:bg-accent border border-border text-foreground font-bold text-xs py-2.5 px-5 rounded-xl shadow-sm transition-all whitespace-nowrap shrink-0"
          >
            {t('overview.avis_cta')}
          </button>
        </div>
      )}

      {loadError && (
        <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center justify-between">
          <span>{loadError}</span>
          <button onClick={chargerDonnees} className="font-bold underline">{t('common.retry')}</button>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          {/* 2. Cartes Métriques "Hero" — réservées à la Vue d'ensemble,
              voir la bannière de bienvenue ci-dessus pour la même règle. */}
          {activeTab === 'overview' && (
          <div className={`grid grid-cols-1 sm:grid-cols-2 gap-5 ${
            nombreCartesHero === 5 ? 'lg:grid-cols-5' : nombreCartesHero === 4 ? 'lg:grid-cols-4' : 'lg:grid-cols-3'
          }`}>
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
              <div className="flex justify-between items-start mb-3">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{t('overview.total_balance')}</span>
                <div className="p-2 rounded-xl bg-violet-500/10 text-violet-600 dark:text-violet-400">
                  <Wallet className="h-5 w-5" />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-black tracking-tight text-violet-600 dark:text-violet-400 tabular-nums">
                {comptePrincipal ? Number(comptePrincipal.solde_total).toLocaleString('fr-FR') : '—'}{' '}
                <span className="text-xs font-bold text-muted-foreground">XAF</span>
              </p>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-3">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{t('overview.income_history')}</span>
                <div className="p-2 rounded-xl bg-forest-500/10 text-forest-600 dark:text-forest-400">
                  <TrendingUp className="h-5 w-5" />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-black tracking-tight text-forest-600 dark:text-forest-400 tabular-nums">
                {revenusDuMois.toLocaleString('fr-FR')} <span className="text-xs font-bold text-muted-foreground">XAF</span>
              </p>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-3">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{t('overview.expenses_history')}</span>
                <div className="p-2 rounded-xl bg-destructive/10 text-destructive">
                  <TrendingDown className="h-5 w-5" />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-black tracking-tight text-destructive tabular-nums">
                {depensesDuMois.toLocaleString('fr-FR')} <span className="text-xs font-bold text-muted-foreground">XAF</span>
              </p>
            </div>

            {afficherCarteEpargne && (
              <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-3">
                  <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{t('overview.savings_reserves')}</span>
                  <div className="p-2 rounded-xl bg-orange-500/10 text-orange-600 dark:text-orange-400">
                    <PiggyBank className="h-5 w-5" />
                  </div>
                </div>
                <p className="text-2xl sm:text-3xl font-black tracking-tight text-orange-600 dark:text-orange-400 tabular-nums">
                  {totalEpargne.toLocaleString('fr-FR')} <span className="text-xs font-bold text-muted-foreground">XAF</span>
                </p>
                <div className="flex items-center gap-1.5 text-xs font-semibold text-orange-600 dark:text-orange-400">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>{t('overview.goals_count', { count: objectifsEpargne.length })}</span>
                </div>
              </div>
            )}

            {afficherCarteDettes && (
              <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-3">
                  <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{t('overview.debts_ongoing')}</span>
                  <div className="p-2 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
                    <HandCoins className="h-5 w-5" />
                  </div>
                </div>
                <p className="text-2xl sm:text-3xl font-black tracking-tight text-blue-600 dark:text-blue-400 tabular-nums">
                  {totalDettesDues.toLocaleString('fr-FR')} <span className="text-xs font-bold text-muted-foreground">XAF</span>
                </p>
                <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400">
                  <HandCoins className="h-3.5 w-3.5" />
                  <span>{t('overview.active_debts_count', { count: dettesActives.length })}</span>
                </div>
              </div>
            )}
          </div>
          )}

          {activeTab === 'accounts' ? (
            <ComptesSection
              comptes={comptes}
              transferts={transferts}
              nomCompte={nomCompte}
              onOpenCompteModal={() => setIsCompteModalOpen(true)}
              onOpenTransfertModal={() => setIsTransfertModalOpen(true)}
              onEditCompte={(c) => setCompteEnEdition(c)}
              onReconcilierCompte={reconcilierCompte}
              onToggleActifCompte={toggleActifCompte}
              onOpenTransfertDetail={(id) => setTransfertDetailId(id)}
              actionError={compteActionError}
            />
          ) : activeTab === 'budgets' ? (
            <BudgetsSection
              comptes={comptesActifs}
              categories={categories}
              budgets={budgets}
              nomCategorie={nomCategorie}
              onGoToAccounts={() => setActiveTab('accounts')}
              onOpenCategorieModal={() => setIsCategorieModalOpen(true)}
              onOpenBudgetModal={() => setIsBudgetModalOpen(true)}
              onEditCategorie={setCategorieEnEdition}
              onToggleActifCategorie={toggleActifCategorie}
              onEditBudget={setBudgetEnEdition}
              onToggleActifBudget={toggleActifBudget}
            />
          ) : activeTab === 'transactions' ? (
            <TransactionsSection
              transactions={transactions}
              comptes={comptes}
              nomCategorie={nomCategorie}
              nomCompte={nomCompte}
              onAnnuler={async (id) => {
                try {
                  await api.request(`/transactions/${id}/annuler`, { method: 'POST' });
                  chargerDonnees();
                } catch (err) {
                  setLoadError(err instanceof Error ? err.message : t('transactions.error_cancel'));
                }
              }}
              onOpenDetail={(id) => setTransactionDetailId(id)}
              onOpenTransactionModal={() => setIsModalOpen(true)}
              categorieParId={categorieParId}
            />
          ) : activeTab === 'savings' ? (
            !abonnement?.plan.acces_epargne ? (
              <LockedFeatureBanner
                titre={t('dashboard.nav.savings')}
                count={donneesVerrouillees?.epargne}
                onUpgrade={() => setIsUpgradeModalOpen(true)}
              />
            ) : (
              <EpargneSection
                objectifs={objectifsEpargne}
                onOpenObjectifModal={() => setIsObjectifModalOpen(true)}
                onAlimenter={(o) => setObjectifOperation({ objectif: o, operation: 'alimenter' })}
                onRetirer={(o) => setObjectifOperation({ objectif: o, operation: 'retirer' })}
                onAbandonner={(o) => setObjectifOperation({ objectif: o, operation: 'abandonner' })}
              />
            )
          ) : activeTab === 'debts' ? (
            !abonnement?.plan.acces_dettes ? (
              <LockedFeatureBanner
                titre={t('dashboard.nav.debts')}
                count={donneesVerrouillees?.dettes}
                onUpgrade={() => setIsUpgradeModalOpen(true)}
              />
            ) : (
              <DettesSection
                dettes={dettes}
                onOpenDetteModal={() => setIsDetteModalOpen(true)}
                onOperation={(d) => setDetteOperation(d)}
                onMarquerPerte={marquerDettePerte}
                onSupprimer={supprimerDette}
              />
            )
          ) : activeTab === 'tontines' ? (
            !abonnement?.plan.acces_tontine ? (
              <LockedFeatureBanner
                titre={t('dashboard.nav.tontines')}
                count={donneesVerrouillees?.tontines}
                onUpgrade={() => setIsUpgradeModalOpen(true)}
              />
            ) : (
              <TontinesSection
                tontines={tontines}
                onOpenTontineModal={() => setIsTontineModalOpen(true)}
                onOpenDetail={(id) => setIdTontineDetail(id)}
              />
            )
          ) : activeTab === 'jarvis' ? (
            !abonnement?.plan.acces_jarvis ? (
              <LockedFeatureBanner
                titre={t('dashboard.nav.jarvis')}
                count={donneesVerrouillees?.jarvis}
                onUpgrade={() => setIsUpgradeModalOpen(true)}
              />
            ) : (
              <JarvisWidget />
            )
          ) : activeTab === 'analyse' ? (
            !abonnement?.plan.acces_analyse ? (
              <LockedFeatureBanner
                titre={t('dashboard.nav.analyse')}
                onUpgrade={() => setIsUpgradeModalOpen(true)}
              />
            ) : (
              <AnalyseSection />
            )
          ) : activeTab === 'automatisations' ? (
            <AutomatisationsSection
              comptesActifs={comptesActifs}
              categories={categories}
              accesRecurrentes={abonnement?.plan.acces_recurrentes ?? false}
              accesTemplates={abonnement?.plan.acces_templates ?? false}
              nombreRecurrentesVerrouillees={donneesVerrouillees?.transactions_recurrentes}
              nombreTemplatesVerrouilles={donneesVerrouillees?.templates}
              onOpenUpgradeModal={() => setIsUpgradeModalOpen(true)}
              nomCompte={nomCompte}
              nomCategorie={nomCategorie}
              onDataChange={chargerDonnees}
            />
          ) : activeTab === 'reports' ? (
            <RapportsSection
              rapports={rapports}
              plan={abonnement?.plan}
              onGenere={chargerRapports}
            />
          ) : activeTab === 'settings' ? (
            <SettingsSection
              plan={abonnement?.plan}
              abonnement={abonnement}
              onOpenUpgradeModal={() => setIsUpgradeModalOpen(true)}
            />
          ) : (
          <>
          {/* 3. Section Grille Principale (2 Colonnes) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Colonne Gauche (Comptes & Transactions) - 2 tiers */}
            <div className="lg:col-span-2 space-y-8">
              {/* Bloc Mes Comptes Financiers */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                    <Wallet className="h-5 w-5 text-primary" />
                    <span>{t('overview.my_accounts')}</span>
                  </h3>
                </div>

                {comptesActifs.length === 0 ? (
                  <div className="p-6 rounded-2xl border border-dashed border-border text-center space-y-2">
                    <p className="text-sm text-muted-foreground">{t('overview.no_accounts_yet')}</p>
                    <button
                      onClick={() => setIsCompteModalOpen(true)}
                      className="text-xs font-bold text-primary hover:underline"
                    >
                      {t('accounts.create')}
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {comptesActifs.map((acc) => (
                      <div
                        key={acc.id_compte}
                        className="p-4 rounded-2xl border bg-card shadow-sm hover:shadow-md transition-all space-y-3"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="p-2 rounded-xl text-xs font-bold bg-primary/10 text-primary">
                              {ICONS_PAR_TYPE_COMPTE[acc.type] ?? <Wallet className="h-4 w-4" />}
                            </div>
                            <div>
                              <h4 className="text-sm font-bold text-foreground leading-tight">{acc.nom}</h4>
                              <span className="text-[11px] text-muted-foreground leading-tight">{acc.type}</span>
                            </div>
                          </div>
                        </div>

                        <div className="pt-1 flex items-baseline justify-between border-t border-border/40">
                          <span className="text-xs font-medium text-muted-foreground">{t('accounts.balance')}</span>
                          <span className="text-lg font-black text-foreground tabular-nums">
                            {formatMontant(Number(acc.solde))}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Bloc Dernières Transactions */}
              <div className="bg-card rounded-2xl border border-border p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-4">
                  <div>
                    <h3 className="text-base font-bold text-foreground">{t('overview.recent_transactions')}</h3>
                    <p className="text-xs text-muted-foreground">{t('overview.recent_transactions_desc')}</p>
                  </div>
                </div>

                {transactionsRecentes.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-6">{t('transactions.none_yet')}</p>
                ) : (
                  <div className="divide-y divide-border">
                    {transactionsRecentes.map((tx) => {
                      const credit = estCredit(tx, transactions);
                      return (
                      <div key={tx.id_transaction} className="py-3.5 flex items-center justify-between hover:bg-muted/30 px-2 rounded-xl transition-colors">
                        <div className="flex items-center gap-3.5">
                          <div className={`p-2.5 rounded-xl ${credit ? 'bg-forest-500/10 text-forest-600' : 'bg-destructive/10 text-destructive'}`}>
                            {credit ? <ArrowDownRight className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
                          </div>

                          <div>
                            <h4 className="text-sm font-bold text-foreground leading-tight">
                              {tx.description || nomCategorie(tx.id_categorie)}
                            </h4>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                              <span>{nomCompte(tx.id_compte)}</span>
                              <span>•</span>
                              <span>{new Date(tx.date).toLocaleDateString('fr-FR')}</span>
                            </div>
                          </div>
                        </div>

                        <span className={`block text-sm font-black tabular-nums ${credit ? 'text-forest-600 dark:text-forest-400' : 'text-foreground'}`}>
                          {credit ? '+ ' : '- '}{Number(tx.montant).toLocaleString('fr-FR')} XAF
                        </span>
                      </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Colonne Droite (Budgets, Épargne & Widget JARVIS) - 1 tier */}
            <div className="space-y-8">
              {/* Widget Assistant Virtuel JARVIS IA — réservé au forfait Premium */}
              {abonnement?.plan.acces_jarvis && <JarvisWidget />}

              {/* Suivi des Budgets par Catégorie */}
              <div className="bg-card rounded-2xl border border-border p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <PieChart className="h-4 w-4 text-primary" />
                    <span>{t('budgets.caps_title')}</span>
                  </h3>
                </div>

                {budgetsActifs.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">{t('budgets.none_yet')}</p>
                ) : (
                  <div className="space-y-4">
                    {budgetsActifs.map((b) => {
                      const percent = Math.round(b.pourcentage_utilise);
                      const color = b.est_depasse ? 'bg-destructive' : percent >= 80 ? 'bg-amber-500' : 'bg-primary';
                      return (
                        <div key={b.id_budget} className="space-y-1.5">
                          <div className="flex justify-between text-xs font-semibold">
                            <span className="text-foreground">{nomCategorie(b.id_categorie)}</span>
                            <span className="text-muted-foreground">
                              <strong className="text-foreground">{Number(b.montant_depense).toLocaleString('fr-FR')}</strong> / {Number(b.montant_limite).toLocaleString('fr-FR')} XAF
                            </span>
                          </div>

                          <div className="w-full bg-muted h-2.5 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full transition-all duration-300 ${color}`} style={{ width: `${Math.min(percent, 100)}%` }} />
                          </div>

                          {b.est_depasse && (
                            <p className="text-[11px] font-bold text-destructive flex items-center gap-1 pt-0.5">
                              <AlertTriangle className="h-3 w-3" />
                              <span>{t('budgets.exceeded', { percent })}</span>
                            </p>
                          )}
                          {!b.est_depasse && percent >= 80 && (
                            <p className="text-[11px] font-bold text-amber-600 dark:text-amber-400 flex items-center gap-1 pt-0.5">
                              <AlertTriangle className="h-3 w-3" />
                              <span>{t('budgets.threshold_warning')}</span>
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Projets d'Épargne — réservé aux forfaits Standard et Premium */}
              {abonnement?.plan.acces_epargne && (
              <div className="bg-card rounded-2xl border border-border p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <PiggyBank className="h-4 w-4 text-forest-600" />
                    <span>{t('savings.goals_title')}</span>
                  </h3>
                </div>

                {objectifsEpargne.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">{t('savings.none_yet')}</p>
                ) : (
                  <div className="space-y-3">
                    {objectifsEpargne.map((g) => (
                      <div key={g.id_objectif} className="p-3.5 rounded-xl border border-border bg-muted/20 space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-foreground">{g.nom}</span>
                          <span className="font-black text-forest-600 dark:text-forest-400">{Math.round(g.pourcentage_atteint)}%</span>
                        </div>
                        <div className="w-full bg-muted h-2 rounded-full overflow-hidden">
                          <div className="bg-forest-500 h-full rounded-full transition-all" style={{ width: `${Math.min(g.pourcentage_atteint, 100)}%` }} />
                        </div>
                        <div className="flex justify-between text-[11px] text-muted-foreground">
                          <span>{t('savings.current_amount')} : {formatMontant(Number(g.montant_actuel))}</span>
                          <span>{t('savings.target_amount')} : {formatMontant(Number(g.montant_cible))}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              )}
            </div>
          </div>
          </>
          )}
        </>
      )}

      {/* Modal d'enregistrement rapide */}
      <TransactionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={chargerDonnees}
      />

      {/* Modal de changement de formule (Standard / Premium) */}
      <PlanUpgradeModal
        isOpen={isUpgradeModalOpen}
        onClose={() => setIsUpgradeModalOpen(false)}
        onSuccess={chargerAbonnement}
        planActuel={abonnement?.plan.nom}
        abonnement={abonnement}
      />

      <AvisModal
        isOpen={isAvisModalOpen}
        onClose={() => setIsAvisModalOpen(false)}
        onSubmitted={chargerMonAvis}
      />

      {/* Modal de création/modification d'un compte financier */}
      <CompteModal
        isOpen={isCompteModalOpen || compteEnEdition !== null}
        onClose={() => { setIsCompteModalOpen(false); setCompteEnEdition(null); }}
        onSuccess={chargerDonnees}
        compte={compteEnEdition}
      />

      {/* Modal de transfert entre comptes */}
      <TransfertModal
        isOpen={isTransfertModalOpen}
        onClose={() => setIsTransfertModalOpen(false)}
        onSuccess={chargerDonnees}
        comptes={comptesActifs}
      />

      {/* Modal de création/modification d'une catégorie */}
      <CategorieModal
        isOpen={isCategorieModalOpen || categorieEnEdition !== null}
        onClose={() => { setIsCategorieModalOpen(false); setCategorieEnEdition(null); }}
        onSuccess={chargerDonnees}
        categorie={categorieEnEdition}
      />

      {/* Modal de définition/modification d'un budget */}
      <BudgetModal
        isOpen={isBudgetModalOpen || budgetEnEdition !== null}
        onClose={() => { setIsBudgetModalOpen(false); setBudgetEnEdition(null); }}
        onSuccess={chargerDonnees}
        categoriesDepense={categories.filter((c) => c.type === 'DEPENSE' && c.est_actif)}
        budget={budgetEnEdition}
        nomCategorie={nomCategorie}
      />

      {/* Modal de déclaration d'une dette/créance */}
      <DetteModal
        isOpen={isDetteModalOpen}
        onClose={() => setIsDetteModalOpen(false)}
        onSuccess={() => { setIsDetteModalOpen(false); api.request<Dette[]>('/dettes').then(setDettes).catch(() => {}); chargerDonnees(); }}
        comptes={comptesActifs}
      />

      {/* Modal de remboursement/encaissement d'une dette */}
      <DetteOperationModal
        isOpen={detteOperation !== null}
        onClose={() => setDetteOperation(null)}
        onSuccess={() => { api.request<Dette[]>('/dettes').then(setDettes).catch(() => {}); chargerDonnees(); }}
        dette={detteOperation}
        comptes={comptesActifs}
      />

      {/* Modal de création d'une tontine */}
      <TontineModal
        isOpen={isTontineModalOpen}
        onClose={() => setIsTontineModalOpen(false)}
        onSuccess={fetchTontines}
      />

      {/* Modal de détail/gestion d'une tontine (tours, cotisations) */}
      <TontineDetailModal
        isOpen={idTontineDetail !== null}
        idTontine={idTontineDetail}
        onClose={() => setIdTontineDetail(null)}
        onChange={fetchTontines}
      />

      {/* Modal de création d'un objectif d'épargne */}
      <ObjectifModal
        isOpen={isObjectifModalOpen}
        onClose={() => setIsObjectifModalOpen(false)}
        onSuccess={() => { setIsObjectifModalOpen(false); api.request<ObjectifEpargne[]>('/epargne').then(setObjectifsEpargne).catch(() => {}); }}
      />

      {/* Modal d'alimentation/retrait d'un objectif d'épargne */}
      <ObjectifOperationModal
        isOpen={objectifOperation !== null}
        onClose={() => setObjectifOperation(null)}
        onSuccess={() => { api.request<ObjectifEpargne[]>('/epargne').then(setObjectifsEpargne).catch(() => {}); chargerDonnees(); }}
        objectif={objectifOperation?.objectif ?? null}
        operation={objectifOperation?.operation ?? 'alimenter'}
        comptes={comptesActifs}
      />

      {/* Détail d'une transaction (avec gestion de la suspicion) */}
      <TransactionDetailModal
        isOpen={transactionDetailId !== null}
        onClose={() => setTransactionDetailId(null)}
        onChange={chargerDonnees}
        idTransaction={transactionDetailId}
        nomCategorie={nomCategorie}
        nomCompte={nomCompte}
        peutAnnuler={transactionDetailId !== null && peutAnnulerTransaction(transactionDetailId)}
        onAnnuler={async (id) => {
          try {
            await api.request(`/transactions/${id}/annuler`, { method: 'POST' });
            chargerDonnees();
          } catch (err) {
            setLoadError(err instanceof Error ? err.message : t('transactions.error_cancel'));
          }
        }}
      />

      {/* Détail d'un transfert entre comptes */}
      {transfertDetailId !== null && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card w-full max-w-sm rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
              <h3 className="text-lg font-bold tracking-tight">{t('transfers.detail_title')}</h3>
              <button onClick={() => setTransfertDetailId(null)} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                <X className="h-5 w-5" />
              </button>
            </div>
            {isLoadingTransfertDetail ? (
              <div className="flex justify-center py-14">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : !transfertDetail ? (
              <p className="p-6 text-sm text-destructive text-center">{t('transfers.not_found')}</p>
            ) : (
              <div className="p-6 space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-muted-foreground">{t('transfers.from')}</span><strong className="text-foreground">{nomCompte(transfertDetail.id_compte_source)}</strong></div>
                <div className="flex justify-between"><span className="text-muted-foreground">{t('transfers.to')}</span><strong className="text-foreground">{nomCompte(transfertDetail.id_compte_destination)}</strong></div>
                <div className="flex justify-between"><span className="text-muted-foreground">{t('transfers.amount')}</span><strong className="text-foreground">{formatMontant(Number(transfertDetail.montant))}</strong></div>
                <div className="flex justify-between"><span className="text-muted-foreground">{t('common.date')}</span><strong className="text-foreground">{new Date(transfertDetail.date).toLocaleDateString('fr-FR')}</strong></div>
                {transfertDetail.description && (
                  <div className="flex justify-between gap-3"><span className="text-muted-foreground shrink-0">{t('common.description')}</span><strong className="text-foreground text-right">{transfertDetail.description}</strong></div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};

interface ComptesSectionProps {
  comptes: CompteFinancier[];
  transferts: Transfert[];
  nomCompte: (idCompte: number) => string;
  onOpenCompteModal: () => void;
  onOpenTransfertModal: () => void;
  onEditCompte: (compte: CompteFinancier) => void;
  onReconcilierCompte: (compte: CompteFinancier) => void;
  onToggleActifCompte: (compte: CompteFinancier) => void;
  onOpenTransfertDetail: (idTransfert: number) => void;
  actionError: string | null;
}

interface ActionMenuItem {
  label: string;
  icon: React.ElementType;
  onClick: () => void;
  tone?: 'default' | 'destructive' | 'positive';
}

// Menu d'actions générique (kebab) réutilisé pour les comptes, catégories,
// budgets, transactions récurrentes et templates — évite de dupliquer le
// pattern d'ouverture/fermeture au clic extérieur à chaque section.
const MenuActions: React.FC<{ items: ActionMenuItem[]; ariaLabel?: string }> = ({ items, ariaLabel = 'Actions' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setIsOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative shrink-0" ref={ref}>
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={ariaLabel}
        className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      >
        <MoreVertical className="h-4 w-4" />
      </button>
      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-52 bg-card border border-border rounded-xl shadow-xl z-20 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.label}
                onClick={() => { setIsOpen(false); item.onClick(); }}
                className={`w-full flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold transition-colors text-left ${
                  item.tone === 'destructive'
                    ? 'text-destructive hover:bg-destructive/10'
                    : item.tone === 'positive'
                    ? 'text-forest-600 dark:text-forest-400 hover:bg-forest-500/10'
                    : 'text-foreground hover:bg-muted'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

const ComptesSection: React.FC<ComptesSectionProps> = ({
  comptes, transferts, nomCompte, onOpenCompteModal, onOpenTransfertModal, onEditCompte, onReconcilierCompte, onToggleActifCompte,
  onOpenTransfertDetail, actionError,
}) => {
  const { t } = useTranslation();
  const comptesActifs = comptes.filter((c) => c.est_actif);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <Wallet className="h-5 w-5 text-primary" />
          <span>{t('overview.my_accounts')}</span>
        </h3>
        <div className="flex items-center gap-2">
          {/* Un transfert n'a de sens qu'entre deux comptes actifs existants —
              camouflé tant qu'il n'y en a pas au moins deux, même principe
              que Créer catégorie / Définir budget pour les Dettes/Épargne. */}
          {comptesActifs.length >= 2 && (
            <button
              onClick={onOpenTransfertModal}
              className="bg-muted hover:bg-accent text-foreground font-bold text-xs py-2.5 px-4 rounded-xl border border-border transition-all flex items-center gap-2"
            >
              <ArrowRightLeft className="h-4 w-4" />
              <span>{t('accounts.transfer_between')}</span>
            </button>
          )}
          <button
            onClick={onOpenCompteModal}
            className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            <span>{t('accounts.create')}</span>
          </button>
        </div>
      </div>

      {actionError && <p className="text-sm text-destructive text-center">{actionError}</p>}

      {comptes.length === 0 ? (
        <div className="p-6 rounded-2xl border border-dashed border-border text-center space-y-2">
          <p className="text-sm text-muted-foreground">{t('overview.no_accounts_yet')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {comptes.map((acc) => (
            <div
              key={acc.id_compte}
              className={`p-4 rounded-2xl border bg-card shadow-sm hover:shadow-md transition-all space-y-3 ${!acc.est_actif ? 'opacity-60' : ''}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-2 rounded-xl text-xs font-bold bg-primary/10 text-primary shrink-0">
                    {ICONS_PAR_TYPE_COMPTE[acc.type] ?? <Wallet className="h-4 w-4" />}
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-sm font-bold text-foreground leading-tight truncate">{acc.nom}</h4>
                    <span className="text-[11px] text-muted-foreground leading-tight">
                      {acc.type}{!acc.est_actif && ` • ${t('common.disabled')}`}
                    </span>
                  </div>
                </div>
                <MenuActions
                  ariaLabel={t('accounts.actions_aria')}
                  items={[
                    { label: t('common.edit'), icon: Pencil, onClick: () => onEditCompte(acc) },
                    ...(acc.est_actif ? [{ label: t('accounts.reconcile'), icon: RefreshCw, onClick: () => onReconcilierCompte(acc) }] : []),
                    {
                      label: acc.est_actif ? t('common.disable') : t('common.reactivate'),
                      icon: acc.est_actif ? PowerOff : Power,
                      onClick: () => onToggleActifCompte(acc),
                      tone: acc.est_actif ? 'destructive' : 'positive',
                    },
                  ]}
                />
              </div>
              <div className="pt-1 flex items-baseline justify-between border-t border-border/40">
                <span className="text-xs font-medium text-muted-foreground">{t('accounts.balance')}</span>
                <span className="text-lg font-black text-foreground tabular-nums">{formatMontant(Number(acc.solde))}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {transferts.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <ArrowRightLeft className="h-4 w-4 text-primary" />
            <span>{t('transfers.history')}</span>
          </h3>
          <div className="bg-card rounded-2xl border border-border shadow-sm divide-y divide-border">
            {transferts.map((tr) => (
              <button
                key={tr.id_transfert}
                onClick={() => onOpenTransfertDetail(tr.id_transfert)}
                className="w-full py-3 px-4 flex items-center justify-between hover:bg-muted/30 transition-colors text-left"
              >
                <div className="min-w-0">
                  <p className="text-sm font-bold text-foreground truncate">
                    {nomCompte(tr.id_compte_source)} <ArrowRightLeft className="h-3 w-3 inline mx-1 text-muted-foreground" /> {nomCompte(tr.id_compte_destination)}
                  </p>
                  <span className="text-xs text-muted-foreground">{new Date(tr.date).toLocaleDateString('fr-FR')}</span>
                </div>
                <span className="text-sm font-black text-foreground tabular-nums shrink-0">{formatMontant(Number(tr.montant))}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

interface BudgetsSectionProps {
  comptes: CompteFinancier[];
  categories: Categorie[];
  budgets: Budget[];
  nomCategorie: (idCategorie: number | null) => string;
  onGoToAccounts: () => void;
  onOpenCategorieModal: () => void;
  onOpenBudgetModal: () => void;
  onEditCategorie: (categorie: Categorie) => void;
  onToggleActifCategorie: (categorie: Categorie) => void;
  onEditBudget: (budget: Budget) => void;
  onToggleActifBudget: (budget: Budget) => void;
}

const BudgetsSection: React.FC<BudgetsSectionProps> = ({
  comptes,
  categories,
  budgets,
  nomCategorie,
  onGoToAccounts,
  onOpenCategorieModal,
  onOpenBudgetModal,
  onEditCategorie,
  onToggleActifCategorie,
  onEditBudget,
  onToggleActifBudget,
}) => {
  const { t } = useTranslation();
  if (comptes.length === 0) {
    return (
      <div className="p-8 rounded-2xl border border-dashed border-border text-center space-y-3">
        <AlertTriangle className="h-8 w-8 mx-auto text-amber-500" />
        <p className="text-sm font-semibold text-foreground">{t('budgets.create_account_first')}</p>
        <p className="text-xs text-muted-foreground max-w-sm mx-auto">
          {t('budgets.create_account_first_desc')}
        </p>
        <button onClick={onGoToAccounts} className="text-xs font-bold text-primary hover:underline">
          {t('budgets.go_to_accounts')}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Catégories */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-foreground flex items-center gap-2">
            <Tag className="h-5 w-5 text-primary" />
            <span>{t('categories.my_categories')}</span>
          </h3>
          <button
            onClick={onOpenCategorieModal}
            className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            <span>{t('categories.create')}</span>
          </button>
        </div>

        {categories.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">{t('categories.none_yet')}</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {categories.map((c) => (
              <span
                key={c.id_categorie}
                className={`text-xs font-semibold pl-3 pr-1.5 py-1.5 rounded-full border flex items-center gap-1.5 ${
                  !c.est_actif
                    ? 'bg-muted text-muted-foreground border-border opacity-60'
                    : c.type === 'DEPENSE'
                    ? 'bg-destructive/10 text-destructive border-destructive/20'
                    : 'bg-forest-500/10 text-forest-600 dark:text-forest-400 border-forest-500/20'
                }`}
              >
                <CategorieBadge icone={c.icone} couleur={c.couleur} size="sm" />
                {c.nom}{!c.est_actif && ` • ${t('common.disabled_fem')}`}
                <MenuActions
                  ariaLabel={t('categories.actions_aria', { nom: c.nom })}
                  items={[
                    { label: t('common.edit'), icon: Pencil, onClick: () => onEditCategorie(c) },
                    {
                      label: c.est_actif ? t('common.disable') : t('common.reactivate'),
                      icon: c.est_actif ? PowerOff : Power,
                      onClick: () => onToggleActifCategorie(c),
                      tone: c.est_actif ? 'destructive' : 'positive',
                    },
                  ]}
                />
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Budgets */}
      <div className="bg-card rounded-2xl border border-border p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <PieChart className="h-4 w-4 text-primary" />
            <span>{t('budgets.caps_title')}</span>
          </h3>
          <button
            onClick={onOpenBudgetModal}
            className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2 px-3.5 rounded-xl shadow-md transition-all flex items-center gap-2"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>{t('budgets.define')}</span>
          </button>
        </div>

        {budgets.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">{t('budgets.none_yet')}</p>
        ) : (
          <div className="space-y-4">
            {budgets.map((b) => {
              const percent = Math.round(b.pourcentage_utilise);
              const color = !b.est_actif ? 'bg-muted-foreground/40' : b.est_depasse ? 'bg-destructive' : percent >= 80 ? 'bg-amber-500' : 'bg-primary';
              return (
                <div key={b.id_budget} className={`space-y-1.5 ${!b.est_actif ? 'opacity-60' : ''}`}>
                  <div className="flex justify-between items-center text-xs font-semibold gap-2">
                    <span className="text-foreground">
                      {nomCategorie(b.id_categorie)}{!b.est_actif && ` • ${t('common.disabled')}`}
                    </span>
                    <div className="flex items-center gap-1 shrink-0">
                      <span className="text-muted-foreground">
                        <strong className="text-foreground">{Number(b.montant_depense).toLocaleString('fr-FR')}</strong> / {Number(b.montant_limite).toLocaleString('fr-FR')} XAF
                      </span>
                      <MenuActions
                        ariaLabel={t('budgets.actions_aria', { nom: nomCategorie(b.id_categorie) })}
                        items={[
                          { label: t('budgets.edit_cap'), icon: Pencil, onClick: () => onEditBudget(b) },
                          {
                            label: b.est_actif ? t('common.disable') : t('common.reactivate'),
                            icon: b.est_actif ? PowerOff : Power,
                            onClick: () => onToggleActifBudget(b),
                            tone: b.est_actif ? 'destructive' : 'positive',
                          },
                        ]}
                      />
                    </div>
                  </div>
                  <div className="w-full bg-muted h-2.5 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-300 ${color}`} style={{ width: `${Math.min(percent, 100)}%` }} />
                  </div>
                  {b.est_actif && b.est_depasse && (
                    <p className="text-[11px] font-bold text-destructive flex items-center gap-1 pt-0.5">
                      <AlertTriangle className="h-3 w-3" />
                      <span>{t('budgets.exceeded', { percent })}</span>
                    </p>
                  )}
                  {b.est_actif && !b.est_depasse && percent >= 80 && (
                    <p className="text-[11px] font-bold text-amber-600 dark:text-amber-400 flex items-center gap-1 pt-0.5">
                      <AlertTriangle className="h-3 w-3" />
                      <span>{t('budgets.threshold_warning')}</span>
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

interface TransactionsSectionProps {
  transactions: Transaction[];
  comptes: CompteFinancier[];
  nomCategorie: (idCategorie: number | null) => string;
  nomCompte: (idCompte: number) => string;
  onAnnuler: (idTransaction: number) => void;
  onOpenDetail: (idTransaction: number) => void;
  onOpenTransactionModal: () => void;
  categorieParId: (idCategorie: number | null) => Categorie | undefined;
}

// Signe de l'impact sur le solde par type — reflète IMPACT_PAR_TYPE côté
// backend (transactions.models). ANNULATION n'y figure pas volontairement :
// son signe est toujours l'inverse de la transaction qu'elle annule (voir
// estCredit ci-dessous), jamais une valeur fixe.
const SIGNE_PAR_TYPE: Partial<Record<Transaction['type'], 1 | -1>> = {
  DEPENSE: -1,
  REVENU: 1,
  DEPOT_INITIAL: 1,
  REMBOURSEMENT_DETTE: -1,
  ENCAISSEMENT_CREANCE: 1,
  DETTE_RECUE: 1,
  CREANCE_ACCORDEE: -1,
};

const estCredit = (tx: Transaction, toutes: Transaction[]): boolean => {
  if (tx.type === 'ANNULATION') {
    const originale = toutes.find((t) => t.id_transaction === tx.id_transaction_annulee);
    // Une annulation ne porte jamais sur une autre annulation (voir
    // TransactionDejaAnnuleeError côté backend) : une seule résolution suffit.
    return originale ? (SIGNE_PAR_TYPE[originale.type] ?? 1) < 0 : true;
  }
  return (SIGNE_PAR_TYPE[tx.type] ?? 1) > 0;
};

const TransactionsSection: React.FC<TransactionsSectionProps> = ({ transactions, comptes, nomCategorie, nomCompte, onAnnuler, onOpenDetail, onOpenTransactionModal, categorieParId }) => {
  const { t } = useTranslation();
  const [filtreCompte, setFiltreCompte] = useState('');
  const [filtreType, setFiltreType] = useState('');

  // Une transaction déjà annulée ne doit pas pouvoir l'être une seconde
  // fois — repéré via id_transaction_annulee des annulations existantes.
  const idsDejaAnnules = new Set(transactions.map((t) => t.id_transaction_annulee).filter((id): id is number => id !== null));

  const transactionsFiltrees = transactions
    .filter((t) => !filtreCompte || t.id_compte === Number(filtreCompte))
    .filter((t) => !filtreType || t.type === filtreType)
    .sort((a, b) => new Date(b.date_creation).getTime() - new Date(a.date_creation).getTime());

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <ArrowUpRight className="h-5 w-5 text-primary" />
          <span>{t('dashboard.nav.transactions')}</span>
        </h3>
        <div className="flex items-center gap-3 text-xs">
          <button
            onClick={onOpenTransactionModal}
            className="bg-primary hover:bg-primary/95 text-primary-foreground font-semibold text-xs py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            <span>{t('transactions.make')}</span>
          </button>
          <Filter className="h-3.5 w-3.5 text-muted-foreground" />
          <select
            value={filtreCompte}
            onChange={(e) => setFiltreCompte(e.target.value)}
            className="bg-background border border-border rounded-lg px-2.5 py-1.5 font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">{t('transactions.all_accounts')}</option>
            {comptes.map((c) => (
              <option key={c.id_compte} value={c.id_compte}>{c.nom}</option>
            ))}
          </select>
          <select
            value={filtreType}
            onChange={(e) => setFiltreType(e.target.value)}
            className="bg-background border border-border rounded-lg px-2.5 py-1.5 font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">{t('transactions.all_types')}</option>
            <option value="DEPENSE">{t('transactions.expenses')}</option>
            <option value="REVENU">{t('transactions.income')}</option>
          </select>
        </div>
      </div>

      <div className="bg-card rounded-2xl border border-border shadow-sm">
        {transactionsFiltrees.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-10">{t('transactions.none_match')}</p>
        ) : (
          <div className="divide-y divide-border">
            {transactionsFiltrees.map((tx) => {
              const peutAnnuler = tx.type !== 'ANNULATION' && !idsDejaAnnules.has(tx.id_transaction);
              const credit = estCredit(tx, transactions);
              const categorieTx = categorieParId(tx.id_categorie);
              return (
                <div
                  key={tx.id_transaction}
                  onClick={() => onOpenDetail(tx.id_transaction)}
                  className="py-3.5 flex items-center justify-between hover:bg-muted/30 px-4 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    {categorieTx ? (
                      <CategorieBadge icone={categorieTx.icone} couleur={categorieTx.couleur} />
                    ) : (
                      <div className={`p-2.5 rounded-xl shrink-0 ${credit ? 'bg-forest-500/10 text-forest-600' : 'bg-destructive/10 text-destructive'}`}>
                        {credit ? <ArrowDownRight className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
                      </div>
                    )}
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-bold text-foreground leading-tight truncate">
                          {tx.description || nomCategorie(tx.id_categorie)}
                        </h4>
                        {tx.est_suspecte && (
                          <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 shrink-0">
                            {t('transactions.suspicious')}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                        <span>{nomCompte(tx.id_compte)}</span>
                        <span>•</span>
                        <span>{new Date(tx.date).toLocaleDateString('fr-FR')}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`block text-sm font-black tabular-nums ${credit ? 'text-forest-600 dark:text-forest-400' : 'text-foreground'}`}>
                      {credit ? '+ ' : '- '}{Number(tx.montant).toLocaleString('fr-FR')} XAF
                    </span>
                    {peutAnnuler && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onAnnuler(tx.id_transaction); }}
                        title={t('transactions.cancel_this')}
                        className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                      >
                        <Ban className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

interface DettesSectionProps {
  dettes: Dette[];
  onOpenDetteModal: () => void;
  onOperation: (dette: Dette) => void;
  onMarquerPerte: (dette: Dette) => void;
  onSupprimer: (dette: Dette) => void;
}

const DettesSection: React.FC<DettesSectionProps> = ({ dettes, onOpenDetteModal, onOperation, onMarquerPerte, onSupprimer }) => {
  const { t } = useTranslation();
  const dettesDues = dettes.filter((d) => d.type === 'DETTE');
  const creances = dettes.filter((d) => d.type === 'CREANCE');

  const renderListe = (liste: Dette[], estDette: boolean) => (
    liste.length === 0 ? (
      <p className="text-xs text-muted-foreground text-center py-4">{estDette ? t('debts.none_debt_yet') : t('debts.none_claim_yet')}</p>
    ) : (
      <div className="space-y-3">
        {liste.map((d) => {
          const montantTotal = Number(d.montant_total);
          const montantRestant = Number(d.montant_restant);
          const percent = montantTotal > 0 ? Math.round(((montantTotal - montantRestant) / montantTotal) * 100) : 0;
          const verrouille = d.statut === 'SOLDE' || d.statut === 'PERTE';
          return (
            <div key={d.id_dette} className="p-4 rounded-xl border border-border bg-muted/20 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <h4 className="text-sm font-bold text-foreground truncate">{d.nom}</h4>
                  {d.personne_impliquee && <span className="text-xs text-muted-foreground">{d.personne_impliquee}</span>}
                </div>
                <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full shrink-0 ${
                  d.statut === 'SOLDE' ? 'bg-forest-500/10 text-forest-600' : d.statut === 'PERTE' ? 'bg-destructive/10 text-destructive' : 'bg-primary/10 text-primary'
                }`}>
                  {d.statut}
                </span>
              </div>
              <div className="w-full bg-muted h-2 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${estDette ? 'bg-destructive' : 'bg-primary'}`} style={{ width: `${Math.min(percent, 100)}%` }} />
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">
                  <strong className="text-foreground">{montantRestant.toLocaleString('fr-FR')}</strong> / {montantTotal.toLocaleString('fr-FR')} XAF {t('debts.remaining')}
                </span>
                {d.date_echeance && (
                  <span className="text-muted-foreground">
                    {d.jours_avant_echeance !== null && d.jours_avant_echeance >= 0
                      ? t('debts.days_left', { count: d.jours_avant_echeance })
                      : t('debts.overdue')}
                  </span>
                )}
              </div>
              {!verrouille && (
                <div className="flex gap-2">
                  <button
                    onClick={() => onOperation(d)}
                    className="flex-1 mt-1 py-2 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary text-xs font-bold transition-colors"
                  >
                    {estDette ? t('debts.repay') : t('debts.collect')}
                  </button>
                  {/* Seule une créance peut être classée irrécouvrable (voir
                      TypeOperationIncompatibleError côté backend) — jamais
                      une dette que le client doit lui-même. */}
                  {!estDette && (
                    <button
                      onClick={() => onMarquerPerte(d)}
                      title={t('debts.write_off_title')}
                      className="mt-1 py-2 px-3 rounded-lg bg-destructive/10 hover:bg-destructive/20 text-destructive text-xs font-bold transition-colors"
                    >
                      {t('debts.write_off')}
                    </button>
                  )}
                </div>
              )}
              {/* Suppression réservée aux dettes/créances déjà SOLDE : une
                  dette encore en cours (ou classée PERTE) représente ou a
                  représenté un mouvement réel, elle reste affichée — voir
                  DetteNonSoldeeError côté backend. L'historique des
                  transactions liées est conservé après suppression. */}
              {d.statut === 'SOLDE' && (
                <button
                  onClick={() => onSupprimer(d)}
                  title={t('debts.delete_title')}
                  className="w-full mt-1 py-2 rounded-lg bg-muted hover:bg-destructive/10 text-muted-foreground hover:text-destructive text-xs font-bold transition-colors flex items-center justify-center gap-1.5"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>{t('common.delete')}</span>
                </button>
              )}
            </div>
          );
        })}
      </div>
    )
  );

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <HandCoins className="h-5 w-5 text-primary" />
          <span>{t('dashboard.nav.debts')}</span>
        </h3>
        <button
          onClick={onOpenDetteModal}
          className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          <span>{t('debts.declare')}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-card rounded-2xl border border-border p-5 shadow-sm space-y-3">
          <h4 className="text-sm font-bold text-foreground">{t('debts.my_debts')}</h4>
          {renderListe(dettesDues, true)}
        </div>
        <div className="bg-card rounded-2xl border border-border p-5 shadow-sm space-y-3">
          <h4 className="text-sm font-bold text-foreground">{t('debts.my_claims')}</h4>
          {renderListe(creances, false)}
        </div>
      </div>
    </div>
  );
};

interface TontinesSectionProps {
  tontines: Tontine[];
  onOpenTontineModal: () => void;
  onOpenDetail: (idTontine: number) => void;
}

const STATUT_TONTINE_BADGE: Record<string, string> = {
  ACTIVE: 'bg-primary/10 text-primary border-primary/20',
  TERMINEE: 'bg-forest-500/10 text-forest-600 dark:text-forest-400 border-forest-500/20',
  ANNULEE: 'bg-muted text-muted-foreground border-border',
};

const TontinesSection: React.FC<TontinesSectionProps> = ({ tontines, onOpenTontineModal, onOpenDetail }) => {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          <span>{t('dashboard.nav.tontines')}</span>
        </h3>
        <button
          onClick={onOpenTontineModal}
          className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          <span>{t('tontines.create')}</span>
        </button>
      </div>

      {tontines.length === 0 ? (
        <div className="bg-card rounded-2xl border border-dashed border-border p-10 text-center space-y-2">
          <Users className="h-8 w-8 text-muted-foreground mx-auto" />
          <p className="text-sm text-muted-foreground">{t('tontines.none_yet')}</p>
          <p className="text-xs text-muted-foreground">{t('tontines.explainer')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {tontines.map((tontine) => (
            <button
              key={tontine.id_tontine}
              onClick={() => onOpenDetail(tontine.id_tontine)}
              className="text-left bg-card rounded-2xl border border-border p-5 shadow-sm hover:shadow-md hover:border-primary/30 transition-all space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <h4 className="text-sm font-bold text-foreground truncate">{tontine.nom}</h4>
                <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border shrink-0 ${STATUT_TONTINE_BADGE[tontine.statut]}`}>
                  {tontine.statut}
                </span>
              </div>
              <div className="space-y-1 text-xs">
                <p className="text-muted-foreground">
                  <strong className="text-foreground">{tontine.nombre_membres}</strong> {t('tontines.members')} • {tontine.frequence === 'HEBDOMADAIRE' ? t('tontines.weekly') : t('tontines.monthly')}
                </p>
                <p className="text-muted-foreground">
                  {t('tontines.pot')} : <strong className="text-primary">{Number(tontine.montant_total_par_tour).toLocaleString('fr-FR')} XAF</strong>
                </p>
                {tontine.numero_tour_actuel !== null && (
                  <p className="text-muted-foreground">{t('tontines.current_round')} : <strong className="text-foreground">{tontine.numero_tour_actuel}/{tontine.nombre_membres}</strong></p>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

interface EpargneSectionProps {
  objectifs: ObjectifEpargne[];
  onOpenObjectifModal: () => void;
  onAlimenter: (objectif: ObjectifEpargne) => void;
  onRetirer: (objectif: ObjectifEpargne) => void;
  onAbandonner: (objectif: ObjectifEpargne) => void;
}

const EpargneSection: React.FC<EpargneSectionProps> = ({ objectifs, onOpenObjectifModal, onAlimenter, onRetirer, onAbandonner }) => {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <PiggyBank className="h-5 w-5 text-forest-600" />
          <span>{t('dashboard.nav.savings')}</span>
        </h3>
        <button
          onClick={onOpenObjectifModal}
          className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          <span>{t('savings.create')}</span>
        </button>
      </div>

      {objectifs.length === 0 ? (
        <div className="p-8 rounded-2xl border border-dashed border-border text-center">
          <p className="text-sm text-muted-foreground">{t('savings.none_yet')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {objectifs.map((o) => {
            const verrouille = o.statut === 'ABANDONNE' || o.statut === 'ATTEINT';
            return (
              <div key={o.id_objectif} className="p-4 rounded-2xl border bg-card shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-foreground">{o.nom}</h4>
                  <span className="font-black text-forest-600 dark:text-forest-400 text-sm">{Math.round(o.pourcentage_atteint)}%</span>
                </div>
                <div className="w-full bg-muted h-2.5 rounded-full overflow-hidden">
                  <div className="bg-forest-500 h-full rounded-full transition-all" style={{ width: `${Math.min(o.pourcentage_atteint, 100)}%` }} />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{t('savings.current_amount')} : <strong className="text-foreground">{Number(o.montant_actuel).toLocaleString('fr-FR')}</strong> XAF</span>
                  <span>{t('savings.target_amount')} : {Number(o.montant_cible).toLocaleString('fr-FR')} XAF</span>
                </div>
                {o.montant_mensuel_requis !== null && !verrouille && (
                  <p className="text-[11px] text-muted-foreground">
                    {t('savings.monthly_needed', { montant: Number(o.montant_mensuel_requis).toLocaleString('fr-FR') })}
                  </p>
                )}
                {!verrouille && (
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={() => onAlimenter(o)}
                      className="flex-1 py-2 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary text-xs font-bold transition-colors"
                    >
                      {t('savings.contribute')}
                    </button>
                    <button
                      onClick={() => onRetirer(o)}
                      disabled={o.montant_actuel <= 0}
                      className="flex-1 py-2 rounded-lg bg-muted hover:bg-accent text-foreground text-xs font-bold transition-colors disabled:opacity-40"
                    >
                      {t('savings.withdraw')}
                    </button>
                    <button
                      onClick={() => onAbandonner(o)}
                      title={t('savings.abandon_title')}
                      className="py-2 px-3 rounded-lg bg-destructive/10 hover:bg-destructive/20 text-destructive text-xs font-bold transition-colors"
                    >
                      {t('savings.abandon')}
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const TYPES_RAPPORT: { valeur: Rapport['type']; labelKey: string; acces: 'acces_dettes' | 'acces_analyse' | null }[] = [
  { valeur: 'RELEVE_TRANSACTIONS', labelKey: 'reports.type_statement', acces: null },
  { valeur: 'BILAN_BUDGETAIRE', labelKey: 'reports.type_budget_summary', acces: null },
  { valeur: 'DETTES_EPARGNE', labelKey: 'reports.type_debts_savings', acces: 'acces_dettes' },
  { valeur: 'BILAN_FINANCIER', labelKey: 'reports.type_financial_summary', acces: 'acces_analyse' },
  { valeur: 'PREDICTIONS', labelKey: 'reports.type_predictions', acces: 'acces_analyse' },
];

interface RapportsSectionProps {
  rapports: Rapport[];
  plan?: { acces_dettes: boolean; acces_analyse: boolean } | null;
  onGenere: () => void;
}

const RapportsSection: React.FC<RapportsSectionProps> = ({ rapports, plan, onGenere }) => {
  const { t } = useTranslation();
  // Calculées une seule fois via l'initialiseur paresseux de useState — les
  // appeler directement dans le corps du composant serait un effet de bord
  // impur à chaque rendu (Date.now()/new Date()).
  const [aujourdHui] = useState(() => new Date().toISOString().slice(0, 10));
  const [type, setType] = useState<Rapport['type']>('RELEVE_TRANSACTIONS');
  const [periodeDebut, setPeriodeDebut] = useState(() => new Date(Date.now() - 30 * 86_400_000).toISOString().slice(0, 10));
  const [periodeFin, setPeriodeFin] = useState(() => new Date().toISOString().slice(0, 10));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statutsAJour, setStatutsAJour] = useState<Record<number, Rapport>>({});
  const [idEnActualisation, setIdEnActualisation] = useState<number | null>(null);

  const rapportsAffiches = rapports.map((r) => statutsAJour[r.id_rapport] ?? r);

  const actualiserStatut = async (idRapport: number) => {
    setIdEnActualisation(idRapport);
    try {
      const frais = await api.request<Rapport>(`/rapports/${idRapport}`);
      setStatutsAJour((prev) => ({ ...prev, [idRapport]: frais }));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('reports.error_refresh'));
    } finally {
      setIdEnActualisation(null);
    }
  };

  const typesDisponibles = TYPES_RAPPORT.filter((tr) => !tr.acces || plan?.[tr.acces]);

  const handleGenerer = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      await api.request('/rapports', {
        method: 'POST',
        body: JSON.stringify({ type, periode_debut: periodeDebut, periode_fin: periodeFin }),
      });
      onGenere();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('reports.error_generate'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const telecharger = async (rapport: Rapport) => {
    try {
      await api.download(`/rapports/${rapport.id_rapport}/telecharger`, `mynkap_${rapport.type.toLowerCase()}_${rapport.id_rapport}.pdf`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('reports.error_download'));
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-base font-bold text-foreground flex items-center gap-2 mb-4">
          <FileText className="h-5 w-5 text-primary" />
          <span>{t('reports.generate_title')}</span>
        </h3>
        <div className="bg-card rounded-2xl border border-border p-5 shadow-sm space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('reports.type_label')}</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as Rapport['type'])}
                className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {typesDisponibles.map((tr) => (
                  <option key={tr.valeur} value={tr.valeur}>{t(tr.labelKey)}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('reports.period_start')}</label>
              <input
                type="date"
                value={periodeDebut}
                max={periodeFin}
                onChange={(e) => setPeriodeDebut(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('reports.period_end')}</label>
              <input
                type="date"
                value={periodeFin}
                min={periodeDebut}
                max={aujourdHui}
                onChange={(e) => setPeriodeFin(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          {error && <p className="text-sm text-destructive text-center">{error}</p>}

          <button
            onClick={handleGenerer}
            disabled={isSubmitting}
            className="w-full sm:w-auto bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-sm py-2.5 px-5 rounded-xl shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>{t('reports.generate_button')}</span>
          </button>
        </div>
      </div>

      <div>
        <h3 className="text-base font-bold text-foreground mb-4">{t('reports.generated_title')}</h3>
        <div className="bg-card rounded-2xl border border-border shadow-sm">
          {rapportsAffiches.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-10">{t('reports.none_yet')}</p>
          ) : (
            <div className="divide-y divide-border">
              {rapportsAffiches.map((r) => (
                <div key={r.id_rapport} className="py-3.5 px-4 flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-bold text-foreground">
                      {t(TYPES_RAPPORT.find((tr) => tr.valeur === r.type)?.labelKey ?? '') || r.type}
                    </h4>
                    <span className="text-xs text-muted-foreground">
                      {new Date(r.periode_debut).toLocaleDateString('fr-FR')} → {new Date(r.periode_fin).toLocaleDateString('fr-FR')}
                      {r.taille !== null && ` • ${Math.round(r.taille / 1024)} Ko`}
                    </span>
                  </div>
                  {r.statut === 'GENERE' ? (
                    <button
                      onClick={() => telecharger(r)}
                      className="p-2 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary transition-colors flex items-center gap-1.5 text-xs font-bold"
                    >
                      <Download className="h-3.5 w-3.5" />
                      <span>{t('reports.download')}</span>
                    </button>
                  ) : r.statut === 'ECHEC' ? (
                    <span className="text-xs font-bold text-destructive">{t('reports.failed')}</span>
                  ) : (
                    <button
                      onClick={() => actualiserStatut(r.id_rapport)}
                      disabled={idEnActualisation === r.id_rapport}
                      title={t('reports.refresh_status')}
                      className="text-xs font-bold text-muted-foreground hover:text-foreground flex items-center gap-1.5 disabled:opacity-50"
                    >
                      {idEnActualisation === r.id_rapport ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Clock className="h-3.5 w-3.5 animate-pulse" />}
                      <span>{t('reports.in_progress')}</span>
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
