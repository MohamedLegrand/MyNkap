import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Wallet,
  Receipt,
  PieChart,
  PiggyBank,
  HandCoins,
  Bot,
  LineChart,
  FileText,
  Sun,
  Moon,
  LogOut,
  Menu,
  X,
  Crown,
  Sparkles,
  Plus,
  CheckCircle2,
} from 'lucide-react';
import { useAuthStore } from '../store';
import { api } from '../services/api';
import { NotificationsBell } from '../components/NotificationsBell';
import { useDarkMode } from '../hooks/useDarkMode';
import type { Plan, Abonnement } from '../types';

interface DashboardLayoutProps {
  children: React.ReactNode;
  activeTab?: string;
  onTabChange?: (tab: string) => void;
  onOpenTransactionModal?: () => void;
  onOpenUpgradeModal?: () => void;
  plan?: Plan | null;
  abonnement?: Abonnement | null;
  nombreComptes?: number;
}

// Nombre de jours restants avant la fin de l'essai gratuit (arrondi au
// jour supérieur pour ne jamais afficher "0 jour" alors qu'il en reste
// encore quelques heures).
const joursRestants = (dateFin: string): number =>
  Math.max(0, Math.ceil((new Date(dateFin).getTime() - Date.now()) / 86_400_000));

const LABEL_PLAN: Record<string, string> = {
  GRATUIT: 'GRATUIT',
  ESSENTIEL: 'STANDARD',
  PREMIUM: 'PREMIUM',
};

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  activeTab = 'overview',
  onTabChange,
  onOpenTransactionModal,
  onOpenUpgradeModal,
  plan,
  abonnement,
  nombreComptes = 0,
}) => {
  const nomPlan = plan?.nom ?? 'GRATUIT';
  const estEnEssai = abonnement?.statut === 'ESSAI' && !!abonnement.date_fin;
  // Rien à proposer au-dessus de PREMIUM une fois l'essai terminé — le
  // bouton "upgrade" n'a alors plus de sens (voir plus bas).
  const dejaAuMaximum = nomPlan === 'PREMIUM' && !estEnEssai;
  const { theme, toggleTheme } = useDarkMode();
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const client = useAuthStore((state) => state.client);
  const refreshToken = useAuthStore((state) => state.refreshToken);

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    if (refreshToken) {
      // Révoque le refresh token côté serveur ; ne bloque jamais la
      // déconnexion locale si l'appel échoue (backend éteint, etc.).
      api.request('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => {});
    }
    logout();
    navigate('/login');
  };

  const navItems = [
    { id: 'overview', label: 'Vue d\'ensemble', icon: LayoutDashboard },
    { id: 'accounts', label: 'Mes Comptes', icon: Wallet, badge: nombreComptes > 0 ? String(nombreComptes) : undefined },
    { id: 'transactions', label: 'Transactions', icon: Receipt },
    { id: 'budgets', label: 'Budgets & Alertes', icon: PieChart },
    { id: 'savings', label: 'Épargne & Projets', icon: PiggyBank, gate: 'acces_epargne' as const },
    { id: 'debts', label: 'Dettes & Créances', icon: HandCoins, gate: 'acces_dettes' as const },
    { id: 'jarvis', label: 'Assistant JARVIS IA', icon: Bot, isNew: true, gate: 'acces_jarvis' as const },
    { id: 'analyse', label: 'Analyse & Prédictions', icon: LineChart, gate: 'acces_analyse' as const },
    // Pas de `gate` ici : RELEVE_TRANSACTIONS et BILAN_BUDGETAIRE sont
    // gratuits pour tous les paliers (seuls certains types de rapports,
    // filtrés à l'intérieur de la page elle-même, sont réservés — voir
    // TYPES_RAPPORT dans ClientDashboard.tsx). `acces_rapport` n'est encore
    // activé par aucun plan, gater l'onglet dessus le cacherait pour tout
    // le monde.
    { id: 'reports', label: 'Rapports PDF', icon: FileText },
  ];

  // Un item sans `gate` est toujours visible ; un item gaté n'apparaît que
  // si le forfait actif y donne accès — évite d'afficher des fonctionnalités
  // inutilisables et de saturer le menu avant un upgrade.
  const navItemsVisibles = navItems.filter((item) => !item.gate || plan?.[item.gate]);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col md:flex-row font-sans transition-colors duration-200">
      {/* 1. Sidebar Latérale Desktop */}
      <aside className="hidden md:flex flex-col w-64 border-r border-border bg-card/60 backdrop-blur-md sticky top-0 h-screen z-30">
        {/* Brand Header */}
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/logo.jpg" alt="MyNkap Logo" className="h-14 w-14 rounded-xl object-cover shadow-sm border border-border" />
            <div>
              <span className="text-xl font-black tracking-tight bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                MyNkap
              </span>
              <span className="block text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">
                Finances Personnelles
              </span>
            </div>
          </div>
        </div>

        {/* User Badge / Plan */}
        <div className="p-4 border-b border-border bg-muted/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-muted-foreground">
              {estEnEssai ? 'Essai gratuit' : 'Formule Actuelle'}
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
              <Crown className="h-3 w-3" />
              <span>{LABEL_PLAN[nomPlan] ?? nomPlan}</span>
            </span>
          </div>
          {estEnEssai && abonnement?.date_fin && (
            <p className="text-[11px] text-muted-foreground mb-2">
              Accès complet, JARVIS inclus — encore{' '}
              <strong className="text-foreground">{joursRestants(abonnement.date_fin)} jour{joursRestants(abonnement.date_fin) > 1 ? 's' : ''}</strong>.
            </p>
          )}
          {dejaAuMaximum ? (
            <p className="text-[11px] font-semibold text-forest-600 dark:text-forest-400 flex items-center justify-center gap-1.5 py-1.5">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Toutes les fonctionnalités débloquées</span>
            </p>
          ) : (
            <button
              onClick={onOpenUpgradeModal}
              className="w-full text-xs font-semibold py-1.5 px-3 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary transition-colors flex items-center justify-center gap-1.5"
            >
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span>{estEnEssai ? "Garder l'accès après l'essai" : 'Passer à la vitesse supérieure'}</span>
            </button>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 p-3 space-y-1.5 overflow-y-auto">
          {navItemsVisibles.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => {
                  onTabChange?.(item.id);
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-md shadow-primary/20'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/80'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`h-4 w-4 ${isActive ? 'text-primary-foreground' : 'text-muted-foreground'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                    isActive ? 'bg-primary-foreground/20 text-primary-foreground' : 'bg-muted text-muted-foreground'
                  }`}>
                    {item.badge}
                  </span>
                )}
                {item.isNew && (
                  <span className="text-[10px] uppercase font-black px-1.5 py-0.5 rounded-md bg-secondary/15 text-secondary border border-secondary/30">
                    IA
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Footer Sidebar */}
        <div className="p-4 border-t border-border space-y-2">
          <button
            onClick={toggleTheme}
            className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-muted transition-colors border border-border/50"
          >
            <span className="flex items-center gap-2">
              {theme === 'light' ? <Moon className="h-4 w-4 text-secondary" /> : <Sun className="h-4 w-4 text-secondary" />}
              <span>{theme === 'light' ? 'Mode Sombre' : 'Mode Clair'}</span>
            </span>
            <span className="text-[10px] text-muted-foreground uppercase">{theme}</span>
          </button>

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-destructive hover:bg-destructive/10 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span>Déconnexion</span>
          </button>
        </div>
      </aside>

      {/* 2. Drawer Mobile Menu */}
      <div className="md:hidden sticky top-0 z-40 bg-background/90 backdrop-blur-md border-b border-border px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <img src="/logo.jpg" alt="MyNkap Logo" className="h-12 w-12 rounded-xl object-cover border border-border" />
          <span className="text-xl font-black bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            MyNkap
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleTheme}
            aria-label="Basculer le thème"
            className="p-2 rounded-xl bg-muted text-foreground border border-border"
          >
            {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4 text-secondary" />}
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-xl bg-muted text-foreground border border-border"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-50 bg-background/95 backdrop-blur-xl flex flex-col p-6 space-y-4">
          <div className="flex justify-between items-center pb-4 border-b border-border">
            <div className="flex items-center gap-3">
              <img src="/logo.jpg" alt="MyNkap Logo" className="h-14 w-14 rounded-xl" />
              <span className="text-xl font-black text-primary">MyNkap</span>
            </div>
            <button onClick={() => setMobileMenuOpen(false)} className="p-2 rounded-xl bg-muted">
              <X className="h-6 w-6" />
            </button>
          </div>

          <nav className="space-y-2 flex-1">
            {navItemsVisibles.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onTabChange?.(item.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-semibold text-base ${
                    activeTab === item.id ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          <button
            onClick={handleLogout}
            className="w-full py-3 rounded-xl bg-destructive/10 text-destructive font-bold flex items-center justify-center gap-2"
          >
            <LogOut className="h-5 w-5" />
            <span>Déconnexion</span>
          </button>
        </div>
      )}

      {/* 3. Zone de Contenu Principal (Main Section) */}
      <main className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Top Navbar Header */}
        <header className="hidden md:flex items-center justify-between h-16 px-8 border-b border-border bg-card sticky top-0 z-20">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold text-foreground capitalize tracking-tight">
              {navItems.find(i => i.id === activeTab)?.label || 'Tableau de bord'}
            </h1>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
              Zone Afrique Centrale (XAF)
            </span>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={onOpenTransactionModal}
              className="bg-primary hover:bg-primary/95 text-primary-foreground font-semibold text-xs py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              <span>Effectuer transaction</span>
            </button>

            <div className="h-5 w-[1px] bg-border" />

            {/* Notifications */}
            <NotificationsBell basePath="/notifications" />

            {/* User Profile Info */}
            <div className="flex items-center gap-3 pl-2">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-primary to-secondary text-primary-foreground font-bold flex items-center justify-center shadow-sm">
                {client?.first_name ? client.first_name[0].toUpperCase() : 'M'}
              </div>
              <div className="text-left">
                <span className="block text-xs font-bold leading-tight">
                  {client?.first_name ? `${client.first_name} ${client.last_name || ''}` : 'Mohamed Legrand'}
                </span>
                <span className="block text-[10px] text-muted-foreground leading-tight">
                  {client?.email || 'client@mynkap.cm'}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Content Body */}
        <div className="flex-1 p-4 sm:p-6 lg:p-8 space-y-6">
          {children}
        </div>
      </main>
    </div>
  );
};
