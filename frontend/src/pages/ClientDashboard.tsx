import React, { useCallback, useEffect, useState } from 'react';
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
  Sparkles,
  ShieldCheck,
  Loader2,
  Crown,
  Tag,
} from 'lucide-react';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { TransactionModal } from '../components/TransactionModal';
import { PlanUpgradeModal } from '../components/PlanUpgradeModal';
import { CompteModal } from '../components/CompteModal';
import { CategorieModal } from '../components/CategorieModal';
import { BudgetModal } from '../components/BudgetModal';
import { JarvisWidget } from '../components/JarvisWidget';
import { api } from '../services/api';
import { useAuthStore } from '../store';
import type {
  Abonnement,
  CompteFinancier,
  ComptePrincipal,
  Transaction,
  Categorie,
  Budget,
  ObjectifEpargne,
} from '../types';

const ICONS_PAR_TYPE_COMPTE: Record<string, React.ReactNode> = {
  MOBILE_MONEY: <Phone className="h-4 w-4" />,
  BANCAIRE: <Building2 className="h-4 w-4" />,
  ESPECES: <Coins className="h-4 w-4" />,
  EPARGNE: <PiggyBank className="h-4 w-4" />,
};

const formatMontant = (valeur: number) => `${valeur.toLocaleString('fr-FR')} XAF`;

export const ClientDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isUpgradeModalOpen, setIsUpgradeModalOpen] = useState(false);
  const [isCompteModalOpen, setIsCompteModalOpen] = useState(false);
  const [isCategorieModalOpen, setIsCategorieModalOpen] = useState(false);
  const [isBudgetModalOpen, setIsBudgetModalOpen] = useState(false);
  const client = useAuthStore((state) => state.client);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [abonnement, setAbonnement] = useState<Abonnement | null>(null);
  const [comptePrincipal, setComptePrincipal] = useState<ComptePrincipal | null>(null);
  const [comptes, setComptes] = useState<CompteFinancier[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Categorie[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [objectifsEpargne, setObjectifsEpargne] = useState<ObjectifEpargne[]>([]);

  const chargerAbonnement = useCallback(async () => {
    try {
      setAbonnement(await api.request<Abonnement>('/abonnement'));
    } catch {
      setAbonnement(null);
    }
  }, []);

  const chargerDonnees = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [cp, listeComptes, listeTransactions, listeCategories, listeBudgets] = await Promise.all([
        api.request<ComptePrincipal>('/comptes/principal'),
        api.request<CompteFinancier[]>('/comptes'),
        api.request<Transaction[]>('/transactions'),
        api.request<Categorie[]>('/categories'),
        api.request<Budget[]>('/budgets'),
      ]);
      setComptePrincipal(cp);
      setComptes(listeComptes);
      setTransactions(listeTransactions);
      setCategories(listeCategories);
      setBudgets(listeBudgets);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Impossible de charger votre tableau de bord.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Chargement au montage, pas une synchronisation d'état dérivé.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    chargerDonnees();
    chargerAbonnement();
  }, [chargerDonnees, chargerAbonnement]);

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

  const nomCategorie = (idCategorie: number | null) =>
    categories.find((c) => c.id_categorie === idCategorie)?.nom ?? 'Non catégorisé';
  const nomCompte = (idCompte: number) => comptes.find((c) => c.id_compte === idCompte)?.nom ?? '—';

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

  return (
    <DashboardLayout
      activeTab={activeTab}
      onTabChange={setActiveTab}
      onOpenTransactionModal={() => setIsModalOpen(true)}
      onOpenUpgradeModal={() => setIsUpgradeModalOpen(true)}
      plan={abonnement?.plan}
    >
      {/* 1. Bannière de Bienvenue */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-primary via-forest-600 to-secondary p-6 sm:p-8 text-white shadow-xl">
        <div className="absolute right-0 top-0 translate-x-12 -translate-y-6 opacity-10 pointer-events-none">
          <Sparkles className="h-96 w-96 text-white" />
        </div>

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-xs font-semibold">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>Compte Certifié • Zone CEMAC (FCFA)</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight">
              Bonjour {client?.first_name ?? ''} 👋
            </h2>
            <p className="text-sm text-white/80 max-w-xl leading-relaxed">
              Voici votre bilan financier consolidé. Votre trésorerie globale s'élève à{' '}
              <strong className="text-white underline decoration-white/40">
                {comptePrincipal ? formatMontant(Number(comptePrincipal.solde_total)) : '—'}
              </strong>{' '}
              répartis sur {comptes.length} compte{comptes.length > 1 ? 's' : ''} actif{comptes.length > 1 ? 's' : ''}.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => setIsModalOpen(true)}
              className="bg-white text-primary hover:bg-white/95 font-bold text-xs py-3 px-5 rounded-xl shadow-lg transition-all flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              <span>Effectuer transaction</span>
            </button>

            {abonnement?.plan.acces_jarvis && (
              <button
                onClick={() => document.getElementById('jarvis-widget')?.scrollIntoView({ behavior: 'smooth' })}
                className="bg-white/15 hover:bg-white/25 text-white font-bold text-xs py-3 px-5 rounded-xl border border-white/25 backdrop-blur-md transition-all flex items-center gap-2"
              >
                <Bot className="h-4 w-4" />
                <span>Demander à JARVIS</span>
              </button>
            )}

            <button
              onClick={() => setIsUpgradeModalOpen(true)}
              className="bg-white text-primary hover:bg-white/95 font-bold text-xs py-3 px-5 rounded-xl shadow-lg transition-all flex items-center gap-2"
            >
              <Crown className="h-4 w-4" />
              <span>{abonnement?.plan.nom === 'PREMIUM' ? 'Gérer mon abonnement' : 'Passer Standard / Premium'}</span>
            </button>
          </div>
        </div>
      </div>

      {loadError && (
        <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center justify-between">
          <span>{loadError}</span>
          <button onClick={chargerDonnees} className="font-bold underline">Réessayer</button>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          {/* 2. Cartes Métriques "Hero" (4 colonnes) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
              <div className="flex justify-between items-start mb-3">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Solde Total Agrégé</span>
                <div className="p-2 rounded-xl bg-primary/10 text-primary">
                  <Wallet className="h-5 w-5" />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-black tracking-tight text-primary tabular-nums">
                {comptePrincipal ? Number(comptePrincipal.solde_total).toLocaleString('fr-FR') : '—'}{' '}
                <span className="text-xs font-bold text-muted-foreground">XAF</span>
              </p>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-3">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Revenus (Historique)</span>
                <div className="p-2 rounded-xl bg-secondary/10 text-secondary">
                  <TrendingUp className="h-5 w-5" />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-black tracking-tight text-secondary tabular-nums">
                {revenusDuMois.toLocaleString('fr-FR')} <span className="text-xs font-bold text-muted-foreground">XAF</span>
              </p>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-3">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Dépenses (Historique)</span>
                <div className="p-2 rounded-xl bg-destructive/10 text-destructive">
                  <TrendingDown className="h-5 w-5" />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-black tracking-tight text-destructive tabular-nums">
                {depensesDuMois.toLocaleString('fr-FR')} <span className="text-xs font-bold text-muted-foreground">XAF</span>
              </p>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-3">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Réserves Épargne</span>
                <div className="p-2 rounded-xl bg-forest-500/10 text-forest-600 dark:text-forest-400">
                  <PiggyBank className="h-5 w-5" />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-black tracking-tight text-foreground tabular-nums">
                {totalEpargne.toLocaleString('fr-FR')} <span className="text-xs font-bold text-muted-foreground">XAF</span>
              </p>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-forest-600 dark:text-forest-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{objectifsEpargne.length} objectif{objectifsEpargne.length > 1 ? 's' : ''}</span>
              </div>
            </div>
          </div>

          {activeTab === 'accounts' ? (
            <ComptesSection comptes={comptes} onOpenCompteModal={() => setIsCompteModalOpen(true)} />
          ) : activeTab === 'budgets' ? (
            <BudgetsSection
              comptes={comptes}
              categories={categories}
              budgets={budgets}
              nomCategorie={nomCategorie}
              onGoToAccounts={() => setActiveTab('accounts')}
              onOpenCategorieModal={() => setIsCategorieModalOpen(true)}
              onOpenBudgetModal={() => setIsBudgetModalOpen(true)}
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
                    <span>Mes Comptes Financiers</span>
                  </h3>
                </div>

                {comptes.length === 0 ? (
                  <div className="p-6 rounded-2xl border border-dashed border-border text-center space-y-2">
                    <p className="text-sm text-muted-foreground">Vous n'avez encore aucun compte financier.</p>
                    <button
                      onClick={() => setIsCompteModalOpen(true)}
                      className="text-xs font-bold text-primary hover:underline"
                    >
                      Créer compte
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {comptes.map((acc) => (
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
                          <span className="text-xs font-medium text-muted-foreground">Solde</span>
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
                    <h3 className="text-base font-bold text-foreground">Dernières Transactions</h3>
                    <p className="text-xs text-muted-foreground">Historique récent des mouvements sur tous vos comptes</p>
                  </div>
                </div>

                {transactionsRecentes.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-6">Aucune transaction pour le moment.</p>
                ) : (
                  <div className="divide-y divide-border">
                    {transactionsRecentes.map((tx) => (
                      <div key={tx.id_transaction} className="py-3.5 flex items-center justify-between hover:bg-muted/30 px-2 rounded-xl transition-colors">
                        <div className="flex items-center gap-3.5">
                          <div className={`p-2.5 rounded-xl ${tx.type === 'REVENU' ? 'bg-forest-500/10 text-forest-600' : 'bg-destructive/10 text-destructive'}`}>
                            {tx.type === 'REVENU' ? <ArrowDownRight className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
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

                        <span className={`block text-sm font-black tabular-nums ${tx.type === 'REVENU' ? 'text-forest-600 dark:text-forest-400' : 'text-foreground'}`}>
                          {tx.type === 'REVENU' ? '+ ' : '- '}{Number(tx.montant).toLocaleString('fr-FR')} XAF
                        </span>
                      </div>
                    ))}
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
                    <span>Plafonds Budgétaires</span>
                  </h3>
                </div>

                {budgets.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">Aucun budget défini pour le moment.</p>
                ) : (
                  <div className="space-y-4">
                    {budgets.map((b) => {
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
                              <span>Budget dépassé ({percent}%) !</span>
                            </p>
                          )}
                          {!b.est_depasse && percent >= 80 && (
                            <p className="text-[11px] font-bold text-amber-600 dark:text-amber-400 flex items-center gap-1 pt-0.5">
                              <AlertTriangle className="h-3 w-3" />
                              <span>Attention : seuil de 80% dépassé !</span>
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
                    <span>Objectifs d'Épargne</span>
                  </h3>
                </div>

                {objectifsEpargne.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">Aucun objectif d'épargne pour le moment.</p>
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
                          <span>Actuel : {formatMontant(Number(g.montant_actuel))}</span>
                          <span>Cible : {formatMontant(Number(g.montant_cible))}</span>
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
      />

      {/* Modal de création d'un compte financier */}
      <CompteModal
        isOpen={isCompteModalOpen}
        onClose={() => setIsCompteModalOpen(false)}
        onSuccess={chargerDonnees}
      />

      {/* Modal de création d'une catégorie */}
      <CategorieModal
        isOpen={isCategorieModalOpen}
        onClose={() => setIsCategorieModalOpen(false)}
        onSuccess={chargerDonnees}
      />

      {/* Modal de définition d'un budget */}
      <BudgetModal
        isOpen={isBudgetModalOpen}
        onClose={() => setIsBudgetModalOpen(false)}
        onSuccess={chargerDonnees}
        categoriesDepense={categories.filter((c) => c.type === 'DEPENSE' && c.est_actif)}
      />
    </DashboardLayout>
  );
};

interface ComptesSectionProps {
  comptes: CompteFinancier[];
  onOpenCompteModal: () => void;
}

const ComptesSection: React.FC<ComptesSectionProps> = ({ comptes, onOpenCompteModal }) => (
  <div className="space-y-4">
    <div className="flex items-center justify-between">
      <h3 className="text-base font-bold text-foreground flex items-center gap-2">
        <Wallet className="h-5 w-5 text-primary" />
        <span>Mes Comptes Financiers</span>
      </h3>
      <button
        onClick={onOpenCompteModal}
        className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center gap-2"
      >
        <Plus className="h-4 w-4" />
        <span>Créer compte</span>
      </button>
    </div>

    {comptes.length === 0 ? (
      <div className="p-6 rounded-2xl border border-dashed border-border text-center space-y-2">
        <p className="text-sm text-muted-foreground">Vous n'avez encore aucun compte financier.</p>
      </div>
    ) : (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {comptes.map((acc) => (
          <div key={acc.id_compte} className="p-4 rounded-2xl border bg-card shadow-sm hover:shadow-md transition-all space-y-3">
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
              <span className="text-xs font-medium text-muted-foreground">Solde</span>
              <span className="text-lg font-black text-foreground tabular-nums">{formatMontant(Number(acc.solde))}</span>
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
);

interface BudgetsSectionProps {
  comptes: CompteFinancier[];
  categories: Categorie[];
  budgets: Budget[];
  nomCategorie: (idCategorie: number | null) => string;
  onGoToAccounts: () => void;
  onOpenCategorieModal: () => void;
  onOpenBudgetModal: () => void;
}

const BudgetsSection: React.FC<BudgetsSectionProps> = ({
  comptes,
  categories,
  budgets,
  nomCategorie,
  onGoToAccounts,
  onOpenCategorieModal,
  onOpenBudgetModal,
}) => {
  if (comptes.length === 0) {
    return (
      <div className="p-8 rounded-2xl border border-dashed border-border text-center space-y-3">
        <AlertTriangle className="h-8 w-8 mx-auto text-amber-500" />
        <p className="text-sm font-semibold text-foreground">Créez d'abord un compte financier</p>
        <p className="text-xs text-muted-foreground max-w-sm mx-auto">
          Les catégories et les budgets s'appliquent à des comptes financiers. Créez votre premier compte pour débloquer ces fonctionnalités.
        </p>
        <button onClick={onGoToAccounts} className="text-xs font-bold text-primary hover:underline">
          Aller à Mes Comptes
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
            <span>Mes Catégories</span>
          </h3>
          <button
            onClick={onOpenCategorieModal}
            className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            <span>Créer catégorie</span>
          </button>
        </div>

        {categories.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">Aucune catégorie pour le moment.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {categories.map((c) => (
              <span
                key={c.id_categorie}
                className={`text-xs font-semibold px-3 py-1.5 rounded-full border ${
                  c.type === 'DEPENSE'
                    ? 'bg-destructive/10 text-destructive border-destructive/20'
                    : 'bg-forest-500/10 text-forest-600 dark:text-forest-400 border-forest-500/20'
                }`}
              >
                {c.nom}
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
            <span>Plafonds Budgétaires</span>
          </h3>
          <button
            onClick={onOpenBudgetModal}
            className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2 px-3.5 rounded-xl shadow-md transition-all flex items-center gap-2"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Définir budget</span>
          </button>
        </div>

        {budgets.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">Aucun budget défini pour le moment.</p>
        ) : (
          <div className="space-y-4">
            {budgets.map((b) => {
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
                      <span>Budget dépassé ({percent}%) !</span>
                    </p>
                  )}
                  {!b.est_depasse && percent >= 80 && (
                    <p className="text-[11px] font-bold text-amber-600 dark:text-amber-400 flex items-center gap-1 pt-0.5">
                      <AlertTriangle className="h-3 w-3" />
                      <span>Attention : seuil de 80% dépassé !</span>
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
