import React, { useCallback, useEffect, useState } from 'react';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Bot,
  Send,
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
} from 'lucide-react';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { TransactionModal } from '../components/TransactionModal';
import { PlanUpgradeModal } from '../components/PlanUpgradeModal';
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
  JarvisMessage,
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

  const [jarvisConversationId, setJarvisConversationId] = useState<string | null>(null);
  const [jarvisQuery, setJarvisQuery] = useState('');
  const [jarvisMessages, setJarvisMessages] = useState<Array<{ sender: 'user' | 'jarvis'; text: string }>>([
    { sender: 'jarvis', text: 'Bonjour ! Je suis JARVIS, votre assistant financier IA. Posez-moi une question sur vos finances.' },
  ]);
  const [isJarvisSending, setIsJarvisSending] = useState(false);

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
      // Requêtes indépendantes : certaines fonctionnalités (Épargne, JARVIS)
      // sont réservées à des paliers d'abonnement supérieurs et renvoient un
      // 403 pour un client GRATUIT — cela ne doit jamais empêcher le reste
      // du tableau de bord (comptes, transactions, budgets) de s'afficher.
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

      try {
        setObjectifsEpargne(await api.request<ObjectifEpargne[]>('/epargne'));
      } catch {
        setObjectifsEpargne([]);
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Impossible de charger votre tableau de bord.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    chargerDonnees();
    chargerAbonnement();
  }, [chargerDonnees, chargerAbonnement]);

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

  const handleSendJarvis = async (e: React.FormEvent) => {
    e.preventDefault();
    const question = jarvisQuery.trim();
    if (!question || isJarvisSending) return;

    setJarvisMessages((prev) => [...prev, { sender: 'user', text: question }]);
    setJarvisQuery('');
    setIsJarvisSending(true);

    try {
      let idConversation = jarvisConversationId;
      if (!idConversation) {
        const conversation = await api.request<{ id_conversation: string }>('/jarvis/conversations', {
          method: 'POST',
          body: JSON.stringify({}),
        });
        idConversation = conversation.id_conversation;
        setJarvisConversationId(idConversation);
      }

      const reponse = await api.request<JarvisMessage>(`/jarvis/conversations/${idConversation}/messages`, {
        method: 'POST',
        body: JSON.stringify({ contenu: question }),
      });
      setJarvisMessages((prev) => [...prev, { sender: 'jarvis', text: reponse.contenu }]);
    } catch (err) {
      setJarvisMessages((prev) => [
        ...prev,
        { sender: 'jarvis', text: err instanceof Error ? err.message : "JARVIS est momentanément indisponible." },
      ]);
    } finally {
      setIsJarvisSending(false);
    }
  };

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
              <span>Nouveau Mouvement</span>
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
              className="bg-amber-400 hover:bg-amber-300 text-amber-950 font-bold text-xs py-3 px-5 rounded-xl shadow-lg transition-all flex items-center gap-2"
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
                <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  <PiggyBank className="h-5 w-5" />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-black tracking-tight text-foreground tabular-nums">
                {totalEpargne.toLocaleString('fr-FR')} <span className="text-xs font-bold text-muted-foreground">XAF</span>
              </p>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{objectifsEpargne.length} objectif{objectifsEpargne.length > 1 ? 's' : ''}</span>
              </div>
            </div>
          </div>

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
                      onClick={() => setIsModalOpen(true)}
                      className="text-xs font-bold text-primary hover:underline"
                    >
                      Ajouter un mouvement pour commencer
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
                          <div className={`p-2.5 rounded-xl ${tx.type === 'REVENU' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-destructive/10 text-destructive'}`}>
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

                        <span className={`block text-sm font-black tabular-nums ${tx.type === 'REVENU' ? 'text-emerald-600 dark:text-emerald-400' : 'text-foreground'}`}>
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
              {abonnement?.plan.acces_jarvis && (
              <div id="jarvis-widget" className="bg-gradient-to-b from-secondary/10 via-card to-card rounded-2xl border border-secondary/30 p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-border">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-xl bg-secondary text-secondary-foreground shadow-sm">
                      <Bot className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                        <span>JARVIS IA</span>
                        <span className="text-[10px] bg-secondary/20 text-secondary px-1.5 py-0.2 rounded font-black uppercase">Actif</span>
                      </h3>
                      <p className="text-[11px] text-muted-foreground">Conseiller financier personnel</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
                  {jarvisMessages.map((msg, index) => (
                    <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div
                        className={`max-w-[85%] p-3 rounded-2xl text-xs leading-relaxed ${
                          msg.sender === 'user'
                            ? 'bg-secondary text-secondary-foreground font-semibold rounded-tr-none'
                            : 'bg-muted text-foreground border border-border/60 rounded-tl-none'
                        }`}
                      >
                        {msg.text}
                      </div>
                    </div>
                  ))}
                  {isJarvisSending && (
                    <div className="flex justify-start">
                      <div className="p-3 rounded-2xl bg-muted border border-border/60 rounded-tl-none">
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                      </div>
                    </div>
                  )}
                </div>

                <form onSubmit={handleSendJarvis} className="relative">
                  <input
                    type="text"
                    placeholder="Posez votre question à JARVIS..."
                    value={jarvisQuery}
                    onChange={(e) => setJarvisQuery(e.target.value)}
                    disabled={isJarvisSending}
                    className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-xs pr-10 focus:outline-none focus:ring-2 focus:ring-secondary disabled:opacity-60"
                  />
                  <button
                    type="submit"
                    disabled={isJarvisSending}
                    className="absolute right-2 top-2 p-1.5 rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/90 transition-colors disabled:opacity-60"
                  >
                    <Send className="h-3.5 w-3.5" />
                  </button>
                </form>
              </div>
              )}

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
                    <PiggyBank className="h-4 w-4 text-emerald-600" />
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
                          <span className="font-black text-emerald-600 dark:text-emerald-400">{Math.round(g.pourcentage_atteint)}%</span>
                        </div>
                        <div className="w-full bg-muted h-2 rounded-full overflow-hidden">
                          <div className="bg-emerald-500 h-full rounded-full transition-all" style={{ width: `${Math.min(g.pourcentage_atteint, 100)}%` }} />
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
    </DashboardLayout>
  );
};
