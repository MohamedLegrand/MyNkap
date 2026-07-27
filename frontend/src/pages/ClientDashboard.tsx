import React, { useState } from 'react';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  ArrowRight,
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
  Filter,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { TransactionModal } from '../components/TransactionModal';

export const ClientDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [jarvisQuery, setJarvisQuery] = useState('');
  const [jarvisMessages, setJarvisMessages] = useState<Array<{ sender: 'user' | 'jarvis'; text: string }>>([
    {
      sender: 'jarvis',
      text: 'Bonjour Mohamed ! Je suis JARVIS, votre assistant financier IA. Vos budgets ce mois-ci sont respectés à 85%. Comment puis-je vous aider aujourd\'hui ?',
    },
  ]);

  const handleSendJarvis = (e: React.FormEvent) => {
    e.preventDefault();
    if (!jarvisQuery.trim()) return;

    const q = jarvisQuery.trim();
    setJarvisMessages(prev => [...prev, { sender: 'user', text: q }]);
    setJarvisQuery('');

    // Réponse simulée de JARVIS
    setTimeout(() => {
      let reply = 'D\'après l\'analyse de vos comptes Orange Money et MTN MoMo, votre capacité d\'épargne ce mois-ci est estimée à 120 000 XAF.';
      if (q.toLowerCase().includes('budget') || q.toLowerCase().includes('transport')) {
        reply = 'Attention : votre budget Transport atteint 90% (45 000 XAF / 50 000 XAF). Il vous reste 5 000 XAF jusqu\'à la fin du mois.';
      } else if (q.toLowerCase().includes('iphone') || q.toLowerCase().includes('achat')) {
        reply = 'Acheter cet équipement aujourd\'hui impacterait votre fonds d\'urgence. Je vous recommande d\'attendre le versement de votre prochain revenu le 30.';
      }

      setJarvisMessages(prev => [...prev, { sender: 'jarvis', text: reply }]);
    }, 700);
  };

  // Données financières réalistes (Cameroun / Zone CEMAC FCFA)
  const accounts = [
    {
      id: 1,
      name: 'Orange Money',
      phone: '+237 699 12 34 56',
      balance: '450,000 XAF',
      type: 'MOBILE_MONEY',
      provider: 'ORANGE',
      color: 'from-orange-500/10 via-orange-500/5 to-transparent border-orange-500/30',
      iconColor: 'bg-orange-500 text-white',
    },
    {
      id: 2,
      name: 'MTN Mobile Money',
      phone: '+237 677 98 76 54',
      balance: '280,000 XAF',
      type: 'MOBILE_MONEY',
      provider: 'MTN',
      color: 'from-yellow-500/10 via-yellow-500/5 to-transparent border-yellow-500/30',
      iconColor: 'bg-amber-400 text-black',
    },
    {
      id: 3,
      name: 'Afriland First Bank',
      phone: 'RIB: 10005 00012 3456...',
      balance: '620,000 XAF',
      type: 'BANQUE',
      provider: 'AFRILAND',
      color: 'from-blue-500/10 via-blue-500/5 to-transparent border-blue-500/30',
      iconColor: 'bg-blue-600 text-white',
    },
    {
      id: 4,
      name: 'Espèces / Cash Portefeuille',
      phone: 'Trésorerie physique',
      balance: '100,000 XAF',
      type: 'CASH',
      provider: 'CASH',
      color: 'from-emerald-500/10 via-emerald-500/5 to-transparent border-emerald-500/30',
      iconColor: 'bg-emerald-600 text-white',
    },
  ];

  const recentTransactions = [
    {
      id: 1,
      title: 'Dépôt Salaire Pro',
      account: 'Afriland First Bank',
      category: 'Revenu',
      type: 'REVENU',
      amount: '+ 850,000 XAF',
      date: '25 Juillet 2026',
      badge: 'Virement',
      badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    },
    {
      id: 2,
      title: 'Facture Eneo Électricité',
      account: 'Orange Money',
      category: 'Factures',
      type: 'DEPENSE',
      amount: '- 35,000 XAF',
      date: '24 Juillet 2026',
      badge: 'Facture',
      badgeColor: 'bg-destructive/10 text-destructive',
    },
    {
      id: 3,
      title: 'Recharge Carburant Total',
      account: 'MTN Mobile Money',
      category: 'Transport',
      type: 'DEPENSE',
      amount: '- 25,000 XAF',
      date: '22 Juillet 2026',
      badge: 'Mobile Money',
      badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
    },
    {
      id: 4,
      title: 'Alimentation & Marché Central',
      account: 'Espèces / Cash',
      category: 'Alimentation',
      type: 'DEPENSE',
      amount: '- 45,000 XAF',
      date: '20 Juillet 2026',
      badge: 'Espèces',
      badgeColor: 'bg-muted text-muted-foreground',
    },
    {
      id: 5,
      title: 'Transfert vers Épargne Sécurité',
      account: 'Orange Money',
      category: 'Épargne',
      type: 'DEPENSE',
      amount: '- 50,000 XAF',
      date: '18 Juillet 2026',
      badge: 'Projet',
      badgeColor: 'bg-secondary/10 text-secondary',
    },
  ];

  const budgets = [
    {
      category: 'Transport & Carburant',
      limit: '50,000 XAF',
      spent: '45,000 XAF',
      percent: 90,
      status: 'WARNING', // Warning > 80%
      color: 'bg-amber-500',
    },
    {
      category: 'Alimentation & Courses',
      limit: '150,000 XAF',
      spent: '95,000 XAF',
      percent: 63,
      status: 'OK',
      color: 'bg-primary',
    },
    {
      category: 'Factures & Abonnements',
      limit: '60,000 XAF',
      spent: '35,000 XAF',
      percent: 58,
      status: 'OK',
      color: 'bg-secondary',
    },
    {
      category: 'Loisirs & Sorties',
      limit: '40,000 XAF',
      spent: '42,000 XAF',
      percent: 105,
      status: 'DANGER', // Over 100%
      color: 'bg-destructive',
    },
  ];

  const savingsGoals = [
    {
      title: 'Fonds de Roulement Pro',
      target: '1,000,000 XAF',
      current: '650,000 XAF',
      percent: 65,
    },
    {
      title: 'Fonds d\'Urgence Santé',
      target: '500,000 XAF',
      current: '380,000 XAF',
      percent: 76,
    },
  ];

  return (
    <DashboardLayout
      activeTab={activeTab}
      onTabChange={setActiveTab}
      onOpenTransactionModal={() => setIsModalOpen(true)}
    >
      {/* 1. Bannière de Bienvenue Réaliste */}
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
              Bonjour Mohamed 👋
            </h2>
            <p className="text-sm text-white/80 max-w-xl leading-relaxed">
              Voici votre bilan financier consolidé. Votre trésorerie globale s'élève à <strong className="text-white underline decoration-white/40">1,450,000 XAF</strong> répartis sur 4 comptes actifs.
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

            <button
              onClick={() => setActiveTab('jarvis')}
              className="bg-white/15 hover:bg-white/25 text-white font-bold text-xs py-3 px-5 rounded-xl border border-white/25 backdrop-blur-md transition-all flex items-center gap-2"
            >
              <Bot className="h-4 w-4" />
              <span>Demander à JARVIS</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. Cartes Métriques "Hero" (4 colonnes) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Solde Total */}
        <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
          <div className="flex justify-between items-start mb-3">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Solde Total Agrégé</span>
            <div className="p-2 rounded-xl bg-primary/10 text-primary">
              <Wallet className="h-5 w-5" />
            </div>
          </div>
          <div className="space-y-1">
            <p className="text-2xl sm:text-3xl font-black tracking-tight text-primary tabular-nums">
              1,450,000 <span className="text-xs font-bold text-muted-foreground">XAF</span>
            </p>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              <ArrowUpRight className="h-3.5 w-3.5" />
              <span>+ 8.4% vs mois dernier</span>
            </div>
          </div>
        </div>

        {/* Revenus */}
        <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-3">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Revenus du Mois</span>
            <div className="p-2 rounded-xl bg-secondary/10 text-secondary">
              <TrendingUp className="h-5 w-5" />
            </div>
          </div>
          <div className="space-y-1">
            <p className="text-2xl sm:text-3xl font-black tracking-tight text-secondary tabular-nums">
              850,000 <span className="text-xs font-bold text-muted-foreground">XAF</span>
            </p>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
              <span>Salaire & virements reçus</span>
            </div>
          </div>
        </div>

        {/* Dépenses */}
        <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-3">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Dépenses Cumulées</span>
            <div className="p-2 rounded-xl bg-destructive/10 text-destructive">
              <TrendingDown className="h-5 w-5" />
            </div>
          </div>
          <div className="space-y-1">
            <p className="text-2xl sm:text-3xl font-black tracking-tight text-destructive tabular-nums">
              217,000 <span className="text-xs font-bold text-muted-foreground">XAF</span>
            </p>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>49% des plafonds de budgets</span>
            </div>
          </div>
        </div>

        {/* Épargne & Projets */}
        <div className="bg-card p-5 rounded-2xl border border-border shadow-sm hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-3">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Réserves Épargne</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <PiggyBank className="h-5 w-5" />
            </div>
          </div>
          <div className="space-y-1">
            <p className="text-2xl sm:text-3xl font-black tracking-tight text-foreground tabular-nums">
              1,030,000 <span className="text-xs font-bold text-muted-foreground">XAF</span>
            </p>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>2 objectifs en bonne voie</span>
            </div>
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
              <button
                onClick={() => setActiveTab('accounts')}
                className="text-xs font-bold text-primary hover:underline flex items-center gap-1"
              >
                <span>Gérer les comptes</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {accounts.map((acc) => (
                <div
                  key={acc.id}
                  className={`p-4 rounded-2xl border bg-gradient-to-br ${acc.color} bg-card shadow-sm hover:shadow-md transition-all space-y-3`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className={`p-2 rounded-xl text-xs font-bold ${acc.iconColor}`}>
                        {acc.type === 'MOBILE_MONEY' ? <Phone className="h-4 w-4" /> : acc.type === 'BANQUE' ? <Building2 className="h-4 w-4" /> : <Coins className="h-4 w-4" />}
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-foreground leading-tight">{acc.name}</h4>
                        <span className="text-[11px] text-muted-foreground leading-tight">{acc.phone}</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-1 flex items-baseline justify-between border-t border-border/40">
                    <span className="text-xs font-medium text-muted-foreground">Solde</span>
                    <span className="text-lg font-black text-foreground tabular-nums">{acc.balance}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Bloc Dernières Transactions */}
          <div className="bg-card rounded-2xl border border-border p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div>
                <h3 className="text-base font-bold text-foreground">Dernières Transactions</h3>
                <p className="text-xs text-muted-foreground">Historique récent des mouvements sur tous vos comptes</p>
              </div>

              <div className="flex items-center gap-2">
                <button className="p-2 rounded-xl bg-muted text-muted-foreground hover:text-foreground text-xs font-semibold flex items-center gap-1.5">
                  <Filter className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Filtrer</span>
                </button>
              </div>
            </div>

            <div className="divide-y divide-border">
              {recentTransactions.map((tx) => (
                <div key={tx.id} className="py-3.5 flex items-center justify-between hover:bg-muted/30 px-2 rounded-xl transition-colors">
                  <div className="flex items-center gap-3.5">
                    <div className={`p-2.5 rounded-xl ${tx.type === 'REVENU' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-destructive/10 text-destructive'}`}>
                      {tx.type === 'REVENU' ? <ArrowDownRight className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
                    </div>

                    <div>
                      <h4 className="text-sm font-bold text-foreground leading-tight">{tx.title}</h4>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                        <span>{tx.account}</span>
                        <span>•</span>
                        <span>{tx.date}</span>
                      </div>
                    </div>
                  </div>

                  <div className="text-right space-y-1">
                    <span className={`block text-sm font-black tabular-nums ${tx.type === 'REVENU' ? 'text-emerald-600 dark:text-emerald-400' : 'text-foreground'}`}>
                      {tx.amount}
                    </span>
                    <span className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full ${tx.badgeColor}`}>
                      {tx.badge}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-2 text-center border-t border-border">
              <button
                onClick={() => setActiveTab('transactions')}
                className="text-xs font-bold text-primary hover:underline inline-flex items-center gap-1"
              >
                <span>Voir tout l'historique des transactions</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Colonne Droite (Budgets, Épargne & Widget JARVIS) - 1 tier */}
        <div className="space-y-8">
          {/* Widget Assistant Virtual JARVIS IA */}
          <div className="bg-gradient-to-b from-secondary/10 via-card to-card rounded-2xl border border-secondary/30 p-5 shadow-sm space-y-4">
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

            {/* Zone de discussion réactive */}
            <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
              {jarvisMessages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
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
            </div>

            {/* Input rapide */}
            <form onSubmit={handleSendJarvis} className="relative">
              <input
                type="text"
                placeholder="Posez votre question à JARVIS..."
                value={jarvisQuery}
                onChange={(e) => setJarvisQuery(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-xs pr-10 focus:outline-none focus:ring-2 focus:ring-secondary"
              />
              <button
                type="submit"
                className="absolute right-2 top-2 p-1.5 rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/90 transition-colors"
              >
                <Send className="h-3.5 w-3.5" />
              </button>
            </form>
          </div>

          {/* Suivi des Budgets par Catégorie */}
          <div className="bg-card rounded-2xl border border-border p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <PieChart className="h-4 w-4 text-primary" />
                <span>Plafonds Budgétaires</span>
              </h3>
              <span className="text-xs font-semibold text-muted-foreground">Juillet 2026</span>
            </div>

            <div className="space-y-4">
              {budgets.map((b, idx) => (
                <div key={idx} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-foreground">{b.category}</span>
                    <span className="text-muted-foreground">
                      <strong className="text-foreground">{b.spent}</strong> / {b.limit}
                    </span>
                  </div>

                  {/* Barre de progression */}
                  <div className="w-full bg-muted h-2.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${b.color}`}
                      style={{ width: `${Math.min(b.percent, 100)}%` }}
                    />
                  </div>

                  {b.status === 'WARNING' && (
                    <p className="text-[11px] font-bold text-amber-600 dark:text-amber-400 flex items-center gap-1 pt-0.5">
                      <AlertTriangle className="h-3 w-3" />
                      <span>Attention : seuil de 80% dépassé !</span>
                    </p>
                  )}
                  {b.status === 'DANGER' && (
                    <p className="text-[11px] font-bold text-destructive flex items-center gap-1 pt-0.5">
                      <AlertTriangle className="h-3 w-3" />
                      <span>Budget dépassé ({b.percent}%) !</span>
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Projets d'Épargne */}
          <div className="bg-card rounded-2xl border border-border p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <PiggyBank className="h-4 w-4 text-emerald-600" />
                <span>Objectifs d'Épargne</span>
              </h3>
              <button
                onClick={() => setActiveTab('savings')}
                className="text-xs font-bold text-primary hover:underline"
              >
                + Créer
              </button>
            </div>

            <div className="space-y-3">
              {savingsGoals.map((g, idx) => (
                <div key={idx} className="p-3.5 rounded-xl border border-border bg-muted/20 space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-foreground">{g.title}</span>
                    <span className="font-black text-emerald-600 dark:text-emerald-400">{g.percent}%</span>
                  </div>
                  <div className="w-full bg-muted h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-500 h-full rounded-full transition-all"
                      style={{ width: `${g.percent}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px] text-muted-foreground">
                    <span>Actuel : {g.current}</span>
                    <span>Cible : {g.target}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Modal d'enregistrement rapide */}
      <TransactionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </DashboardLayout>
  );
};
