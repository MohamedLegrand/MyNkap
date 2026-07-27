import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  Users,
  ShieldCheck,
  History,
  Sliders,
  CreditCard,
  AlertOctagon,
  Sun,
  Moon,
  LogOut,
  Bell,
  Menu,
  X,
  Shield,
  Zap,
  Lock,
} from 'lucide-react';
import { useAuthStore } from '../store';
import { api } from '../services/api';

interface AdminLayoutProps {
  children: React.ReactNode;
  activeTab?: string;
  onTabChange?: (tab: string) => void;
}

export const useDarkMode = () => {
  const [theme, setTheme] = React.useState(localStorage.getItem('theme') || 'dark');

  React.useEffect(() => {
    const root = window.document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(prev => (prev === 'light' ? 'dark' : 'light'));

  return { theme, toggleTheme };
};

export const AdminLayout: React.FC<AdminLayoutProps> = ({
  children,
  activeTab = 'kpis',
  onTabChange,
}) => {
  const { theme, toggleTheme } = useDarkMode();
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const refreshToken = useAuthStore((state) => state.refreshToken);

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    if (refreshToken) {
      api.request('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => {});
    }
    logout();
    navigate('/login');
  };

  const navItems = [
    { id: 'kpis', label: 'KPIs Globaux 360°', icon: BarChart3, badge: 'M7' },
    { id: 'clients', label: 'Gestion des Clients', icon: Users, badge: 'M1' },
    { id: 'admins', label: 'Équipe Administrateur', icon: ShieldCheck, badge: 'M2' },
    { id: 'audit', label: 'Journaux d\'Audit', icon: History, badge: 'M3' },
    { id: 'config', label: 'Configuration Système', icon: Sliders, badge: 'M4' },
    { id: 'subscriptions', label: 'Abonnements & Paiements', icon: CreditCard, badge: 'M5' },
    { id: 'fraud', label: 'Surveillance Anti-Fraude', icon: AlertOctagon, badge: 'M6', alert: true },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col md:flex-row font-sans transition-colors duration-200 selection:bg-amber-500/20">
      {/* 1. Sidebar Latérale Desktop Admin */}
      <aside className="hidden md:flex flex-col w-68 border-r border-border bg-card/80 backdrop-blur-xl sticky top-0 h-screen z-30">
        {/* Brand Header Admin */}
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-amber-500 via-primary to-secondary p-0.5 shadow-md">
              <div className="h-full w-full bg-card rounded-[10px] flex items-center justify-center">
                <Shield className="h-5 w-5 text-amber-500" />
              </div>
            </div>
            <div>
              <span className="text-lg font-black tracking-tight bg-gradient-to-r from-amber-500 via-primary to-secondary bg-clip-text text-transparent">
                MyNkap Admin
              </span>
              <span className="block text-[10px] font-bold text-amber-500 uppercase tracking-widest">
                Console de Contrôle
              </span>
            </div>
          </div>
        </div>

        {/* Badge Niveaux & Status Admin */}
        <div className="p-4 border-b border-border bg-amber-500/5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-500 animate-pulse" />
              <span className="text-xs font-bold text-foreground">Accès Superadmin</span>
            </div>
            <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30">
              Niveau 3
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1.5 leading-tight">
            Privilèges élevés : Gestion système, audit complet et contrôle anti-fraude.
          </p>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 p-3 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onTabChange?.(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-amber-500 text-slate-950 shadow-lg shadow-amber-500/20'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`h-4 w-4 ${isActive ? 'text-slate-950' : 'text-muted-foreground'}`} />
                  <span>{item.label}</span>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-md font-black ${
                  isActive ? 'bg-slate-950/20 text-slate-950' : 'bg-muted text-muted-foreground'
                }`}>
                  {item.badge}
                </span>
              </button>
            );
          })}
        </nav>

        {/* Footer Sidebar */}
        <div className="p-4 border-t border-border space-y-2">
          <button
            onClick={toggleTheme}
            className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-muted transition-colors border border-border"
          >
            <span className="flex items-center gap-2">
              {theme === 'light' ? <Moon className="h-4 w-4 text-secondary" /> : <Sun className="h-4 w-4 text-amber-400" />}
              <span>{theme === 'light' ? 'Mode Sombre' : 'Mode Clair'}</span>
            </span>
            <span className="text-[10px] text-muted-foreground uppercase">{theme}</span>
          </button>

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold text-destructive hover:bg-destructive/10 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span>Quitter la Console Admin</span>
          </button>
        </div>
      </aside>

      {/* 2. Menu Mobile Drawer Admin */}
      <div className="md:hidden sticky top-0 z-40 bg-background/90 backdrop-blur-md border-b border-border px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Shield className="h-6 w-6 text-amber-500" />
          <span className="text-lg font-black bg-gradient-to-r from-amber-500 to-primary bg-clip-text text-transparent">
            MyNkap Admin
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl bg-muted text-foreground border border-border"
          >
            {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4 text-amber-400" />}
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
              <Shield className="h-7 w-7 text-amber-500" />
              <span className="text-xl font-black text-amber-500">Console Admin</span>
            </div>
            <button onClick={() => setMobileMenuOpen(false)} className="p-2 rounded-xl bg-muted">
              <X className="h-6 w-6" />
            </button>
          </div>

          <nav className="space-y-2 flex-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onTabChange?.(item.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm ${
                    activeTab === item.id ? 'bg-amber-500 text-slate-950' : 'text-muted-foreground'
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

      {/* 3. Zone Principal Admin */}
      <main className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Header Admin Navbar */}
        <header className="hidden md:flex items-center justify-between h-16 px-8 border-b border-border bg-card/40 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-black text-foreground uppercase tracking-wider">
              {navItems.find(i => i.id === activeTab)?.label || 'Console Admin'}
            </h1>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
              <Lock className="h-3 w-3" />
              <span>Environnement Sécurisé SSL</span>
            </span>
          </div>

          <div className="flex items-center gap-4">
            <button className="relative p-2 rounded-xl bg-muted hover:bg-accent text-foreground transition-colors border border-border">
              <Bell className="h-4 w-4 text-muted-foreground" />
              <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
            </button>

            <div className="h-5 w-[1px] bg-border" />

            {/* Profile Admin */}
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-amber-500 to-primary text-slate-950 font-black flex items-center justify-center shadow-sm">
                A
              </div>
              <div className="text-left">
                <span className="block text-xs font-bold leading-tight">Administrateur Principal</span>
                <span className="block text-[10px] text-amber-500 font-semibold leading-tight">Superadmin (Niveau 3)</span>
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
