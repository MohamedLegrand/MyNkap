import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useSearchParams, Link } from 'react-router-dom';
import {
  Sun, Moon, ArrowRight, Check,
  MessageSquare, TrendingUp, Shield, Sparkles, Database, Lock, Menu, X, Users, Globe,
  HelpCircle, Mail, Loader2, User, Phone, Eye, EyeOff, Wallet, RefreshCw,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store';
import type { TokenResponse, Client } from '../types';
import { OtpVerificationStep } from '../components/OtpVerificationStep';
import { GoogleSignInButton } from '../components/GoogleSignInButton';
import { useDarkMode } from '../hooks/useDarkMode';

// Décode la charge utile d'un jeton d'identité Google (JWT) côté client,
// uniquement pour connaître l'e-mail (et, à l'inscription, le prénom/nom) à
// afficher ou pré-remplir — la vérification de signature qui fait foi reste
// faite par le backend (voir POST /auth/google).
const decoderProfilGoogle = (credential: string): { email: string; prenom: string; nom: string } => {
  try {
    const payload = JSON.parse(atob(credential.split('.')[1]));
    return {
      email: typeof payload.email === 'string' ? payload.email : '',
      prenom: typeof payload.given_name === 'string' ? payload.given_name : '',
      nom: typeof payload.family_name === 'string' ? payload.family_name : '',
    };
  } catch {
    return { email: '', prenom: '', nom: '' };
  }
};

// Bandeau de confiance défilant (section "Conçu pour la sécurité...")
const TRUST_PILLS: { icon: LucideIcon; titre: string; description: string }[] = [
  { icon: Globe, titre: 'XAF', description: 'Devise native Afrique Centrale' },
  { icon: Users, titre: 'Mobile Money', description: 'Orange Money & MTN MoMo intégrés' },
  { icon: Database, titre: '0 écart', description: 'Aucune incohérence de solde tolérée' },
  { icon: Lock, titre: 'Chiffré', description: 'Données protégées de bout en bout' },
  { icon: Shield, titre: '2FA', description: 'Double authentification par e-mail' },
  { icon: Check, titre: 'Historique inaltérable', description: 'Aucune transaction supprimable' },
  { icon: TrendingUp, titre: 'Patrimoine en temps réel', description: 'Calculé à chaque opération' },
];

// Bouton de bascule de thème
const ThemeToggle = ({ theme, toggleTheme }: { theme: string; toggleTheme: () => void }) => (
  <button
    onClick={toggleTheme}
    aria-label={theme === 'light' ? 'Activer le mode sombre' : 'Activer le mode clair'}
    className="p-2 rounded-xl bg-muted hover:bg-accent text-foreground border border-border transition-colors duration-150"
    title="Changer de thème"
  >
    {theme === 'light' ? <Moon className="h-5 w-5 text-muted-foreground" /> : <Sun className="h-5 w-5 text-secondary" />}
  </button>
);

// En-tête partagé par la landing page et la page À propos
const SiteHeader = () => {
  const { theme, toggleTheme } = useDarkMode();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-md border-b border-border transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo & Brand */}
        <Link to="/" className="flex items-center gap-3">
          <img src="/logo.jpg" alt="MyNkap Logo" className="h-14 w-14 rounded-xl object-cover shadow-sm border border-border" />
          <span className="text-2xl font-black tracking-tight bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            MyNkap
          </span>
        </Link>

        {/* Desktop Nav Links */}
        <nav className="hidden lg:flex items-center gap-8">
          <a href="/#ia" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Intelligence Artificielle</a>
          <a href="/#features" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Fonctionnalités</a>
          <a href="/#pricing" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Tarifs</a>
          <Link to="/a-propos" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">À propos</Link>
          <Link to="/contact" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">Contact</Link>
        </nav>

        {/* CTA & Theme toggle */}
        <div className="hidden lg:flex items-center gap-4">
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
          <Link to="/login" className="text-sm font-semibold hover:text-primary transition-colors">
            Connexion
          </Link>
          <Link
            to="/register"
            className="bg-primary hover:bg-primary/95 text-primary-foreground text-sm font-semibold py-2.5 px-5 rounded-xl transition-all shadow-sm"
          >
            S'inscrire
          </Link>
        </div>

        {/* Mobile Menu Toggle */}
        <div className="flex items-center gap-4 lg:hidden">
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
            aria-expanded={mobileMenuOpen}
            className="p-2 text-muted-foreground hover:text-foreground"
          >
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-border bg-background px-4 pt-4 pb-6 space-y-3 transition-colors duration-200">
          <a href="/#ia" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-base font-medium text-muted-foreground hover:text-foreground">Intelligence Artificielle</a>
          <a href="/#features" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-base font-medium text-muted-foreground hover:text-foreground">Fonctionnalités</a>
          <a href="/#pricing" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-base font-medium text-muted-foreground hover:text-foreground">Tarifs</a>
          <Link to="/a-propos" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-base font-medium text-muted-foreground hover:text-foreground">À propos</Link>
          <Link to="/contact" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-base font-medium text-muted-foreground hover:text-foreground">Contact</Link>
          <div className="pt-4 border-t border-border flex flex-col gap-3">
            <Link to="/login" className="text-center py-2.5 font-semibold text-sm hover:text-primary transition-colors">
              Connexion
            </Link>
            <Link to="/register" className="text-center bg-primary hover:bg-primary/95 text-primary-foreground text-sm font-semibold py-2.5 rounded-xl shadow-sm">
              S'inscrire
            </Link>
          </div>
        </div>
      )}
    </header>
  );
};

// Numéro de contact WhatsApp (Cameroun, +237)
const WHATSAPP_NUMERO = '237677246900';
const WHATSAPP_LIEN = `https://wa.me/${WHATSAPP_NUMERO}`;

// Pied de page partagé par la landing page et la page À propos
const SiteFooter = () => (
  <footer className="bg-background text-muted-foreground transition-colors duration-200 border-t border-border pt-16 pb-12">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 pb-12 border-b border-border">

        {/* Colonne 1: Marque & Description */}
        <div className="md:col-span-4 space-y-4">
          <div className="flex items-center gap-3">
            <img src="/logo.jpg" alt="MyNkap" className="h-12 w-12 rounded-xl object-cover border border-border shadow-sm" />
            <span className="text-xl font-black text-foreground">MyNkap</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed max-w-sm">
            L'application intelligente d'analyse financière et de suivi budgétaire conçue pour le marché d'Afrique Centrale. Centralisez vos comptes Orange Money, MTN MoMo, cartes bancaires et cash.
          </p>

          {/* Réseaux sociaux */}
          <div className="flex gap-4 pt-2 text-muted-foreground">
            <a href="#" className="hover:text-primary transition-colors" title="Twitter / X">
              <svg className="h-5 w-5 fill-current" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>
            <a href="#" className="hover:text-primary transition-colors" title="GitHub">
              <svg className="h-5 w-5 fill-current" viewBox="0 0 24 24">
                <path d="M12 2A10 10 0 0 0 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0 0 12 2z" />
              </svg>
            </a>
            <a href="#" className="hover:text-primary transition-colors" title="LinkedIn">
              <svg className="h-5 w-5 fill-current" viewBox="0 0 24 24">
                <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
              </svg>
            </a>
          </div>
        </div>

        {/* Colonne 2: Produit */}
        <div className="md:col-span-2 space-y-4">
          <h4 className="text-sm font-bold text-foreground">Produit</h4>
          <ul className="space-y-2 text-xs">
            <li><a href="/#features" className="hover:text-foreground transition-colors">Fonctionnalités</a></li>
            <li><a href="/#ia" className="hover:text-foreground transition-colors">Intelligence Artificielle</a></li>
            <li><a href="/#pricing" className="hover:text-foreground transition-colors">Tarifs & Offres</a></li>
            <li><a href="#" className="hover:text-foreground transition-colors">Mises à jour</a></li>
          </ul>
        </div>

        {/* Colonne 3: Ressources */}
        <div className="md:col-span-2 space-y-4">
          <h4 className="text-sm font-bold text-foreground">Ressources</h4>
          <ul className="space-y-2 text-xs">
            <li><Link to="/a-propos" className="hover:text-foreground transition-colors">À propos</Link></li>
            <li><Link to="/contact" className="hover:text-foreground transition-colors">Contact</Link></li>
            <li><a href="/#about" className="hover:text-foreground transition-colors">Principes Comptables</a></li>
            <li><a href="#" className="hover:text-foreground transition-colors">Centre d'aide</a></li>
            <li><a href="#" className="hover:text-foreground transition-colors">API Développeurs</a></li>
          </ul>
        </div>

        {/* Colonne 4: Support & Localisation */}
        <div className="md:col-span-4 space-y-4">
          <h4 className="text-sm font-bold text-foreground">Support & Contact</h4>
          <ul className="space-y-2.5 text-xs">
            <li className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-primary" />
              <a href="mailto:support@mynkap.com" className="hover:text-foreground transition-colors">support@mynkap.com</a>
            </li>
            <li className="flex items-center gap-2">
              <svg className="h-4 w-4 text-forest-500 shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347M12.05 21.785h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884M20.52 3.449C18.24 1.245 15.24 0 12.05 0 5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.304-1.654a11.888 11.888 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.463-8.452" />
              </svg>
              <a
                href={WHATSAPP_LIEN}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-foreground transition-colors"
              >
                +237 677 246 900 (WhatsApp)
              </a>
            </li>
            <li className="flex items-center gap-2">
              <HelpCircle className="h-4 w-4 text-secondary" />
              <span className="text-muted-foreground">Yaoundé / Douala, Cameroun</span>
            </li>
          </ul>
          {/* Badge Sécurisé */}
          <div className="pt-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-primary/10 text-primary border border-primary/20 text-[10px] font-bold uppercase tracking-wider">
              <Shield className="h-3 w-3" />
              Données Chiffrées
            </span>
          </div>
        </div>

      </div>

      {/* Bottom Bar: Copyright et Avertissement */}
      <div className="pt-8 flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="text-left space-y-2 max-w-2xl">
          <p className="text-[10px] text-muted-foreground leading-relaxed">
            <strong>Avertissement légal :</strong> MyNkap est un outil d'analyse et de planification financière personnelle. L'application ne gère aucun dépôt de fonds réels, n'effectue aucun transfert monétaire réel et ne détient pas de licence d'établissement bancaire. Les transactions doivent être renseignées par l'utilisateur.
          </p>
          <p className="text-xs">
            &copy; {new Date().getFullYear()} MyNkap SaaS. Conçu pour le marché africain. Tous droits réservés.
          </p>
        </div>

        <div className="flex gap-4 text-xs font-semibold whitespace-nowrap">
          <a href="#" className="hover:text-foreground transition-colors">Confidentialité</a>
          <a href="#" className="hover:text-foreground transition-colors">Conditions</a>
        </div>
      </div>

    </div>
  </footer>
);

// Démo animée de l'assistant IA (section "Intelligence Artificielle") : la
// question puis la réponse s'affichent lettre par lettre, en boucle continue,
// pour simuler une vraie conversation en train de s'écrire.
const IA_DEMO_QUESTION = "Puis-je me permettre d'acheter un téléphone à 250 000 XAF ce mois-ci ?";
const IA_DEMO_REPONSE = "En analysant vos revenus (800 000 XAF) et vos dépenses fixes actuelles (300 000 XAF), oui vous le pouvez. Cependant, cela réduira votre objectif d'épargne 'Terrain Douala' de 12% ce mois-ci. Je vous recommande d'attendre le 5 du mois prochain.";

type PhaseDemoIA = 'question' | 'reflexion' | 'reponse' | 'pause';

const AiChatDemo = () => {
  const [phase, setPhase] = useState<PhaseDemoIA>('question');
  const [question, setQuestion] = useState('');
  const [reponse, setReponse] = useState('');

  useEffect(() => {
    let annule = false;
    let idTimeout: ReturnType<typeof setTimeout>;

    const attendre = (ms: number) =>
      new Promise<void>((resolve) => {
        idTimeout = setTimeout(resolve, ms);
      });

    const ecrireProgressivement = async (texte: string, onChange: (valeur: string) => void, vitesseMs: number) => {
      for (let i = 1; i <= texte.length; i++) {
        if (annule) return;
        onChange(texte.slice(0, i));
        await attendre(vitesseMs);
      }
    };

    const boucle = async () => {
      while (!annule) {
        setQuestion('');
        setReponse('');
        setPhase('question');
        await ecrireProgressivement(IA_DEMO_QUESTION, setQuestion, 35);
        if (annule) return;

        await attendre(600);
        if (annule) return;
        setPhase('reflexion');
        await attendre(1100);
        if (annule) return;

        setPhase('reponse');
        await ecrireProgressivement(IA_DEMO_REPONSE, setReponse, 18);
        if (annule) return;

        setPhase('pause');
        await attendre(4500);
      }
    };

    boucle();
    return () => {
      annule = true;
      clearTimeout(idTimeout);
    };
  }, []);

  return (
    <div className="w-full max-w-sm bg-card rounded-2xl shadow-xl border border-border p-6 space-y-4 text-left">
      <div className="flex items-center gap-2 border-b border-border pb-3">
        <div className="w-10 h-10 rounded-full bg-primary/10 flex justify-center items-center text-primary">
          <Sparkles className="w-6 h-6" />
        </div>
        <div>
          <h4 className="font-bold text-sm">Assistant Financier IA</h4>
          <span className="text-xs text-green-500 flex items-center gap-1">
            <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-ping"></span>
            En ligne
          </span>
        </div>
      </div>

      <div className="space-y-3 h-[240px] overflow-y-auto pr-1 text-xs">
        {question && (
          <div className="flex flex-col items-end">
            <div className="bg-secondary text-secondary-foreground p-3 rounded-2xl rounded-tr-none max-w-[85%]">
              "{question}
              {phase === 'question' && <span className="animate-pulse">▌</span>}"
            </div>
            <span className="text-[10px] text-muted-foreground mt-1">Vous, 14:58</span>
          </div>
        )}

        {phase === 'reflexion' && (
          <div className="flex flex-col items-start">
            <div className="bg-muted p-3 rounded-2xl rounded-tl-none border border-border flex gap-1.5">
              <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}

        {reponse && (
          <div className="flex flex-col items-start">
            <div className="bg-muted p-3 rounded-2xl rounded-tl-none max-w-[85%] border border-border leading-relaxed">
              "{reponse}
              {phase === 'reponse' && <span className="animate-pulse">▌</span>}"
            </div>
            <span className="text-[10px] text-muted-foreground mt-1">Assistant IA, 14:59</span>
          </div>
        )}
      </div>

      <div className="border-t border-border pt-3">
        <div className="flex gap-2 bg-muted p-2 rounded-xl border border-border">
          <input
            disabled
            placeholder="Posez une question financière à l'IA..."
            className="bg-transparent border-none text-xs flex-1 outline-none text-muted-foreground"
          />
          <button className="bg-primary text-primary-foreground p-1.5 rounded-lg" aria-label="Envoyer">
            <MessageSquare className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-200 font-sans selection:bg-primary/20 scroll-smooth">
      {/* 1. Header (Navigation) */}
      <SiteHeader />

      {/* 2. Hero Section */}
      <section className="relative pt-12 pb-20 md:pt-20 md:pb-28 overflow-hidden bg-gradient-to-b from-primary/5 via-transparent to-transparent">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center justify-center text-center max-w-3xl mx-auto space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold tracking-wide">
              <Sparkles className="h-4 w-4" />
              <span>Nouveau : Prise en charge native de Mobile Money</span>
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight leading-tight">
              Contrôlez Votre <span className="text-primary">Budget</span> Et Vos <span className="text-secondary">Finances</span> Facilement
            </h1>
            <p className="text-lg text-muted-foreground leading-relaxed">
              MyNkap est l'application intelligente conçue spécifiquement pour le marché d'Afrique Centrale. Centralisez vos comptes Orange Money, MTN MoMo, bancaires et cash au même endroit avec l'aide de notre assistant financier propulsé par l'intelligence artificielle.
            </p>
            <div className="flex flex-wrap justify-center gap-4 pt-2">
              <a
                href="/register"
                className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold py-3.5 px-8 rounded-xl transition-all shadow-md flex items-center gap-2 group"
              >
                <span>Essayer Gratuitement</span>
                <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </a>
              <a
                href="#ia"
                className="bg-card hover:bg-muted text-foreground border border-border font-bold py-3.5 px-8 rounded-xl transition-all shadow-sm"
              >
                Découvrir l'IA
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Trusted By / Bandeau de confiance défilant */}
      <section className="py-12 bg-muted transition-colors duration-200 border-y border-border overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-8">
            Conçu pour la sécurité et la fiabilité financière au quotidien
          </p>
        </div>

        <div className="relative w-full marquee-fade">
          <div className="flex w-max animate-marquee">
            {[...TRUST_PILLS, ...TRUST_PILLS].map((pill, idx) => (
              <div key={idx} className="flex items-center gap-3 pr-10 shrink-0">
                <span className="p-2.5 rounded-xl bg-card border border-border shadow-sm text-primary shrink-0">
                  <pill.icon className="h-5 w-5" />
                </span>
                <div className="text-left leading-tight">
                  <span className="block text-sm font-bold text-foreground whitespace-nowrap">{pill.titre}</span>
                  <span className="block text-[11px] text-muted-foreground whitespace-nowrap">{pill.description}</span>
                </div>
                <span className="text-border pl-7 select-none">•</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4. Feature Section 1: AI Assistant */}
      <section id="ia" className="py-20 md:py-28 bg-background transition-colors duration-200 scroll-mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">

            {/* Left Column (Interactive AI Conversation Box) */}
            <div className="lg:col-span-5 flex justify-center order-last lg:order-first">
              <AiChatDemo />
            </div>

            {/* Right Column (Content) */}
            <div className="lg:col-span-7 space-y-6 text-left">
              <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
                Prenez des décisions éclairées grâce à l'<span className="text-primary">Intelligence Artificielle</span>
              </h2>
              <p className="text-base text-muted-foreground leading-relaxed">
                Notre assistant IA n'est pas un simple chatbot. Il est directement connecté à vos flux financiers enregistrés. Il apprend de vos habitudes de consommation pour vous proposer des conseils d'épargne personnalisés, anticiper vos découverts et automatiser la saisie par commande vocale.
              </p>
              
              <ul className="space-y-3.5">
                {[
                  "Saisie vocale en langage naturel via dictée",
                  "Prédiction des risques de dépassement budgétaire",
                  "Conseils personnalisés d'allocation d'épargne",
                  "Détection automatique de doublons ou transactions suspectes"
                ].map((item, idx) => (
                  <li key={idx} className="flex items-center gap-3 text-sm">
                    <div className="p-1 bg-primary/10 text-primary rounded-full">
                      <Check className="h-4 w-4" />
                    </div>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            
          </div>
        </div>
      </section>

      {/* 5. Feature Section 2: Cards and Accounts */}
      <section id="features" className="py-20 md:py-28 bg-muted transition-colors duration-200 border-t border-border scroll-mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center justify-center text-center max-w-3xl mx-auto space-y-6">
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              Simplifiez Votre Portefeuille, Suivez Vos <span className="text-secondary">Comptes</span> Sans Effort
            </h2>
            <p className="text-base text-muted-foreground leading-relaxed">
              Fini le désordre des relevés sur plusieurs téléphones ou banques. Avec MyNkap, vous disposez d'un compte principal agrégateur qui additionne automatiquement l'ensemble de votre patrimoine brut en temps réel.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 w-full text-left">
              <div className="p-5 bg-card rounded-2xl border border-border shadow-sm">
                <div className="text-primary font-bold text-lg mb-2">Mobile Money</div>
                <p className="text-xs text-muted-foreground">MTN MoMo et Orange Money intégrés pour suivre vos transferts et recharges instantanément.</p>
              </div>
              <div className="p-5 bg-card rounded-2xl border border-border shadow-sm">
                <div className="text-secondary font-bold text-lg mb-2">Comptes Épargne</div>
                <p className="text-xs text-muted-foreground">Chaque objectif d'épargne possède un compte d'épargne dédié créé automatiquement.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5bis. Feature Section: Tontines & Épargne Collective */}
      <section id="tontines" className="py-20 md:py-28 bg-background transition-colors duration-200 border-t border-border scroll-mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">

            {/* Left Column (Content) */}
            <div className="lg:col-span-7 space-y-6 text-left order-last lg:order-first">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-bold uppercase tracking-wide">
                <Sparkles className="h-3.5 w-3.5" />
                Nouveau
              </span>
              <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
                Vos <span className="text-secondary">tontines</span> enfin organisées, sans jamais toucher à votre argent
              </h2>
              <p className="text-base text-muted-foreground leading-relaxed">
                MyNkap ne détient jamais l'argent de votre tontine ou njangi — l'argent continue de circuler entre vous, comme toujours. L'application se charge simplement de ce qui est fastidieux à tenir à la main : qui a cotisé, à qui c'est le tour, et quand.
              </p>

              <ul className="space-y-3.5">
                {[
                  "Rotation des tours générée automatiquement selon l'ordre des membres",
                  "Suivi des cotisations versées, tour par tour",
                  "Calendrier des échéances hebdomadaires ou mensuelles",
                  "Historique complet conservé, même après la clôture d'un tour",
                ].map((item, idx) => (
                  <li key={idx} className="flex items-center gap-3 text-sm">
                    <div className="p-1 bg-secondary/10 text-secondary rounded-full">
                      <Check className="h-4 w-4" />
                    </div>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Right Column (Visuel statique de la rotation) */}
            <div className="lg:col-span-5 flex justify-center">
              <div className="w-full max-w-sm bg-card rounded-2xl border border-border shadow-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Users className="h-5 w-5 text-secondary" />
                    <span className="font-bold text-sm">Tontine du quartier</span>
                  </div>
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-primary/10 text-primary">ACTIVE</span>
                </div>
                <div className="p-3 rounded-xl bg-secondary/5 border border-secondary/20 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <RefreshCw className="h-4 w-4 text-secondary" />
                    <span className="text-xs font-semibold">Tour 2/5 — Awa</span>
                  </div>
                  <span className="text-xs font-black text-secondary">25 000 XAF</span>
                </div>
                <div className="space-y-2">
                  {[
                    { nom: 'Biyick', ok: true },
                    { nom: 'Chantal', ok: true },
                    { nom: 'Awa', ok: false },
                    { nom: 'Junior', ok: false },
                  ].map((m) => (
                    <div key={m.nom} className="flex items-center gap-2 text-xs">
                      <div className={`h-2 w-2 rounded-full ${m.ok ? 'bg-forest-500' : 'bg-muted-foreground/30'}`} />
                      <span className={m.ok ? 'text-foreground font-semibold' : 'text-muted-foreground'}>{m.nom}</span>
                      <span className="ml-auto text-muted-foreground">{m.ok ? 'Versé' : 'En attente'}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* 6. Feature Section 3: Accounting Rigor (About Section) */}
      <section id="about" className="py-20 md:py-28 bg-background transition-colors duration-200 scroll-mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-12">
          <div className="max-w-2xl mx-auto space-y-4">
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              Rigueur Comptable & Financière Stricte
            </h2>
            <p className="text-base text-muted-foreground leading-relaxed">
              MyNkap repose sur les principes de la comptabilité moderne pour vous garantir une traçabilité sans faille et une image fidèle de votre situation patrimoniale brute et nette.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-card p-6 rounded-2xl border border-border shadow-sm text-left space-y-3">
              <div className="p-3 bg-primary/10 text-primary w-12 h-12 rounded-xl flex justify-center items-center">
                <Database className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold">Immuabilité des flux</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Une transaction enregistrée ne peut jamais être supprimée directement. Toutes les corrections s'effectuent par transaction d'annulation inverse, assurant un historique d'audit inaltérable.
              </p>
            </div>

            <div className="bg-card p-6 rounded-2xl border border-border shadow-sm text-left space-y-3">
              <div className="p-3 bg-secondary/10 text-secondary w-12 h-12 rounded-xl flex justify-center items-center">
                <TrendingUp className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold">Patrimoine Net Réel</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Le patrimoine net est calculé dynamiquement : Somme des soldes actifs moins la somme de vos dettes plus la somme de vos créances accordées.
              </p>
            </div>

            <div className="bg-card p-6 rounded-2xl border border-border shadow-sm text-left space-y-3">
              <div className="p-3 bg-primary/10 text-primary w-12 h-12 rounded-xl flex justify-center items-center">
                <Shield className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold">Opérations Atomiques</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Aucun écart de solde n'est toléré. Chaque opération financière (transfert, virement, achat) est exécutée de manière atomique sous forme de transaction SQL.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 7. Pricing Section */}
      <section id="pricing" className="py-20 md:py-28 bg-muted transition-colors duration-200 border-t border-border scroll-mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-12">
          <div className="max-w-2xl mx-auto space-y-4">
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              Des Plans Adaptés À Vos Besoins
            </h2>
            <p className="text-base text-muted-foreground leading-relaxed">
              Choisissez l'offre qui correspond le mieux à votre rythme de gestion financière.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
            {/* Plan Gratuit */}
            <div className="bg-card p-8 rounded-2xl border border-border shadow-sm flex flex-col justify-between text-left relative">
              <div className="space-y-4">
                <h3 className="text-xl font-bold">GRATUIT</h3>
                <div className="text-3xl font-extrabold text-primary">0 XAF</div>
                <p className="text-xs text-muted-foreground">Toute la gestion financière de base, sans limite.</p>
                <hr className="border-border" />
                <ul className="space-y-3 text-xs">
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Comptes financiers</li>
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Transactions & Transferts</li>
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Budgets</li>
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Catégories</li>
                  <li className="flex items-center gap-2 text-muted-foreground/60"><Check className="w-4 h-4 text-muted-foreground/40" /> Dettes & Créances, Épargne indisponibles</li>
                  <li className="flex items-center gap-2 text-muted-foreground/60"><Check className="w-4 h-4 text-muted-foreground/40" /> Analyse, Prédictions et JARVIS indisponibles</li>
                </ul>
              </div>
              <Link to="/register" className="mt-8 block text-center bg-muted hover:bg-accent border border-border text-foreground font-semibold py-2.5 rounded-xl transition-all text-xs">
                Commencer
              </Link>
            </div>

            {/* Plan Essentiel */}
            <div className="bg-card p-8 rounded-2xl border-2 border-primary shadow-md flex flex-col justify-between text-left relative transform md:-translate-y-2">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-[10px] font-black uppercase tracking-wider px-3.5 py-1 rounded-full">
                Recommandé
              </div>
              <div className="space-y-4">
                <h3 className="text-xl font-bold">ESSENTIEL</h3>
                <div className="text-3xl font-extrabold text-primary">1 000 XAF <span className="text-xs font-normal text-muted-foreground">/ mois</span></div>
                <p className="text-xs text-muted-foreground">10 000 XAF / an (2 mois offerts). Tout le Gratuit, plus :</p>
                <hr className="border-border" />
                <ul className="space-y-3 text-xs">
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Dettes & Créances</li>
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Objectifs d'épargne</li>
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Transactions récurrentes automatiques</li>
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Templates de transaction</li>
                </ul>
              </div>
              <Link to="/register" className="mt-8 block text-center bg-primary hover:bg-primary/95 text-primary-foreground font-semibold py-2.5 rounded-xl transition-all text-xs shadow-sm">
                Choisir Essentiel
              </Link>
            </div>

            {/* Plan Premium */}
            <div className="bg-card p-8 rounded-2xl border border-border shadow-sm flex flex-col justify-between text-left relative">
              <div className="space-y-4">
                <h3 className="text-xl font-bold">PREMIUM</h3>
                <div className="text-3xl font-extrabold text-primary">2 500 XAF <span className="text-xs font-normal text-muted-foreground">/ mois</span></div>
                <p className="text-xs text-muted-foreground">25 000 XAF / an (2 mois offerts). Tout l'Essentiel, plus :</p>
                <hr className="border-border" />
                <ul className="space-y-3 text-xs">
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Analyse & Prédictions financières</li>
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Score financier personnalisé</li>
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> JARVIS — chat texte et vocal</li>
                  <li className="flex items-center gap-2"><Check className="w-4 h-4 text-primary" /> Conseils financiers personnalisés</li>
                </ul>
              </div>
              <Link to="/register" className="mt-8 block text-center bg-muted hover:bg-accent border border-border text-foreground font-semibold py-2.5 rounded-xl transition-all text-xs">
                Choisir Premium
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 8. Footer */}
      <SiteFooter />
    </div>
  );
};

const AboutPage = () => {
  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-200 font-sans selection:bg-primary/20 scroll-smooth">
      <SiteHeader />

      {/* Hero */}
      <section className="relative pt-16 pb-16 md:pt-20 md:pb-20 overflow-hidden bg-gradient-to-b from-primary/5 via-transparent to-transparent">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold tracking-wide">
            <Sparkles className="h-4 w-4" />
            <span>À propos de MyNkap</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-black tracking-tight leading-tight">
            Une application pensée pour les finances personnelles en <span className="text-primary">Afrique Centrale</span>
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-2xl mx-auto">
            MyNkap est né d'un constat simple : gérer son argent au quotidien en zone CEMAC (FCFA) — entre Mobile Money, comptes bancaires et espèces — reste éclaté entre plusieurs applications qui ne se parlent pas. MyNkap réunit tout cela en un seul endroit clair et fiable.
          </p>
        </div>
      </section>

      {/* Notre objectif */}
      <section className="py-16 md:py-20 bg-muted border-t border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
          <div className="space-y-4">
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Notre objectif</h2>
            <p className="text-base text-muted-foreground leading-relaxed">
              Donner à chacun une vision claire et fidèle de sa situation financière réelle : combien vous possédez, combien vous devez, combien vous pouvez épargner — sans avoir à additionner mentalement plusieurs comptes Mobile Money, un compte bancaire et de l'argent en espèces.
            </p>
            <p className="text-base text-muted-foreground leading-relaxed">
              MyNkap ne déplace pas d'argent réel : c'est un outil de suivi, de budgétisation et d'analyse. Vous gardez le contrôle total de vos comptes existants, MyNkap vous aide simplement à voir clair.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm space-y-1.5">
              <Wallet className="h-6 w-6 text-primary" />
              <h3 className="text-sm font-bold">Comptes unifiés</h3>
              <p className="text-xs text-muted-foreground">Mobile Money, banque et espèces au même endroit.</p>
            </div>
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm space-y-1.5">
              <TrendingUp className="h-6 w-6 text-secondary" />
              <h3 className="text-sm font-bold">Budgets clairs</h3>
              <p className="text-xs text-muted-foreground">Catégories et plafonds pour garder le cap chaque mois.</p>
            </div>
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm space-y-1.5">
              <Sparkles className="h-6 w-6 text-primary" />
              <h3 className="text-sm font-bold">Assistant IA</h3>
              <p className="text-xs text-muted-foreground">Des conseils personnalisés basés sur vos vraies données.</p>
            </div>
            <div className="bg-card p-5 rounded-2xl border border-border shadow-sm space-y-1.5">
              <Shield className="h-6 w-6 text-secondary" />
              <h3 className="text-sm font-bold">Données protégées</h3>
              <p className="text-xs text-muted-foreground">Chiffrement et double authentification par défaut.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Pour qui */}
      <section className="py-16 md:py-20 border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Pour qui ?</h2>
          <p className="text-base text-muted-foreground leading-relaxed max-w-2xl mx-auto">
            MyNkap s'adresse à toute personne en Afrique Centrale qui utilise Orange Money, MTN MoMo, un ou plusieurs comptes bancaires, et souhaite enfin suivre ses finances personnelles sans jongler entre plusieurs applications ou tableurs.
          </p>
          <div className="flex flex-wrap justify-center gap-3 pt-2">
            {['Salariés', 'Indépendants & commerçants', 'Étudiants', 'Familles'].map((profil) => (
              <span key={profil} className="px-4 py-2 rounded-full bg-muted border border-border text-sm font-semibold">
                {profil}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Contact */}
      <section className="py-16 md:py-20 bg-muted border-t border-border">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Une question ?</h2>
          <p className="text-base text-muted-foreground leading-relaxed">
            Notre équipe basée à Yaoundé et Douala vous répond directement sur WhatsApp.
          </p>
          <a
            href={WHATSAPP_LIEN}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2.5 bg-forest-500 hover:bg-forest-600 text-white font-semibold py-3 px-6 rounded-xl transition-all shadow-md"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347M12.05 21.785h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884M20.52 3.449C18.24 1.245 15.24 0 12.05 0 5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.304-1.654a11.888 11.888 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.463-8.452" />
            </svg>
            <span>Discuter sur WhatsApp — +237 677 246 900</span>
          </a>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
};

const ContactPage = () => {
  const [nom, setNom] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [estEnvoye, setEstEnvoye] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // MyNkap n'a pas de service d'envoi d'e-mail pour ce formulaire : le
    // message est transmis directement via WhatsApp (numéro de contact),
    // pré-rempli pour que l'utilisateur n'ait plus qu'à appuyer sur envoyer.
    const texte = `Nouveau message depuis le site MyNkap :\n\nNom : ${nom}\nEmail : ${email}\n\nMessage :\n${message}`;
    window.open(`${WHATSAPP_LIEN}?text=${encodeURIComponent(texte)}`, '_blank', 'noopener,noreferrer');
    setEstEnvoye(true);
  };

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-200 font-sans selection:bg-primary/20 scroll-smooth">
      <SiteHeader />

      <section className="relative pt-16 pb-16 md:pt-20 md:pb-20 overflow-hidden bg-gradient-to-b from-primary/5 via-transparent to-transparent">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold tracking-wide">
            <MessageSquare className="h-4 w-4" />
            <span>Contact</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-black tracking-tight leading-tight">
            Une question ? <span className="text-primary">Écrivez-nous</span>
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-xl mx-auto">
            Remplissez le formulaire ci-dessous : votre message s'ouvre directement dans WhatsApp, prêt à être envoyé à notre équipe.
          </p>
        </div>
      </section>

      <section className="pb-20 md:pb-28">
        <div className="max-w-xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-card p-8 rounded-2xl border border-border shadow-lg">
            {estEnvoye ? (
              <div className="text-center space-y-4 py-6">
                <div className="mx-auto w-14 h-14 rounded-full bg-forest-500/10 text-forest-600 dark:text-forest-400 flex items-center justify-center">
                  <Check className="h-7 w-7" />
                </div>
                <h2 className="text-xl font-bold">WhatsApp est en train de s'ouvrir</h2>
                <p className="text-sm text-muted-foreground">
                  Un nouvel onglet WhatsApp s'est ouvert avec votre message pré-rempli. Il ne reste plus qu'à appuyer sur envoyer.
                </p>
                <button
                  onClick={() => { setEstEnvoye(false); setNom(''); setEmail(''); setMessage(''); }}
                  className="text-sm font-bold text-primary hover:underline"
                >
                  Envoyer un autre message
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label htmlFor="contact_nom" className="text-sm font-medium">Nom complet</label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <input
                      id="contact_nom"
                      type="text"
                      required
                      value={nom}
                      onChange={(e) => setNom(e.target.value)}
                      placeholder="Votre nom"
                      className="w-full bg-background border border-border rounded-xl pl-10 pr-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="contact_email" className="text-sm font-medium">Adresse e-mail</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <input
                      id="contact_email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="vous@exemple.com"
                      className="w-full bg-background border border-border rounded-xl pl-10 pr-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="contact_message" className="text-sm font-medium">Message</label>
                  <textarea
                    id="contact_message"
                    required
                    rows={5}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Comment pouvons-nous vous aider ?"
                    className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-semibold py-3 rounded-xl transition-all shadow-md flex items-center justify-center gap-2"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347M12.05 21.785h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884M20.52 3.449C18.24 1.245 15.24 0 12.05 0 5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.304-1.654a11.888 11.888 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.463-8.452" />
                  </svg>
                  <span>Envoyer via WhatsApp</span>
                </button>
              </form>
            )}
          </div>

          <p className="text-center text-xs text-muted-foreground mt-6">
            Vous préférez l'e-mail ? Écrivez-nous à{' '}
            <a href="mailto:support@mynkap.com" className="font-semibold text-primary hover:underline">support@mynkap.com</a>
          </p>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
};

// Mise en page partagée par les pages Connexion et Inscription
const AuthLayout = ({
  title,
  subtitle,
  maxWidthClassName = 'max-w-md',
  children,
}: {
  title: string;
  subtitle: string;
  maxWidthClassName?: string;
  children: React.ReactNode;
}) => {
  const { theme, toggleTheme } = useDarkMode();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background text-foreground transition-colors duration-200">
      <div className="absolute top-6 right-6">
        <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
      </div>

      <div className={`w-full ${maxWidthClassName}`}>
        <Link to="/" className="flex flex-col items-center gap-3 mb-8">
          <img src="/logo.jpg" alt="MyNkap" className="h-20 w-20 rounded-2xl object-cover shadow-md border border-border" />
          <span className="text-2xl font-black tracking-tight bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            MyNkap
          </span>
        </Link>

        <div className="bg-card p-8 rounded-2xl shadow-lg border border-border">
          <h2 className="text-2xl font-bold mb-2 text-center">{title}</h2>
          <p className="text-muted-foreground text-center mb-6 text-sm">{subtitle}</p>
          {children}
        </div>

        <Link to="/" className="block text-center text-sm text-muted-foreground hover:text-foreground font-medium mt-6">
          ← Retour à l'accueil
        </Link>
      </div>
    </div>
  );
};

const baseInputClassName =
  'w-full py-2.5 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40';
const inputClassName = `${baseInputClassName} pl-11 pr-4`;

// Champ de formulaire avec icône, pour un rendu plus professionnel sur les pages d'authentification
const IconInput = ({
  icon: Icon,
  className,
  ...props
}: { icon: LucideIcon } & React.InputHTMLAttributes<HTMLInputElement>) => (
  <div className="relative">
    <Icon className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
    <input {...props} className={className ?? inputClassName} />
  </div>
);

// Champ mot de passe avec bouton afficher/masquer, pour un rendu plus professionnel
const PasswordInput = ({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) => {
  const [visible, setVisible] = useState(false);

  return (
    <div className="relative">
      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      <input
        {...props}
        type={visible ? 'text' : 'password'}
        className={className ?? `${baseInputClassName} pl-11 pr-11`}
      />
      <button
        type="button"
        onClick={() => setVisible((prev) => !prev)}
        aria-label={visible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
      >
        {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
};

const LoginPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setSession = useAuthStore((state) => state.setSession);
  const setClient = useAuthStore((state) => state.setClient);

  const [step, setStep] = useState<1 | 2>(1);
  const [email, setEmail] = useState('');
  const [motDePasse, setMotDePasse] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Jeton Google en attente de vérification OTP — distinct de motDePasse
  // pour que handleResend sache quel endpoint rappeler (voir plus bas).
  const [googleCredential, setGoogleCredential] = useState<string | null>(null);
  const compteVientDetreCree = searchParams.get('compte_cree') === '1';

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      // Étape 1 : mot de passe vérifié, un code à 6 chiffres est envoyé
      // par e-mail (aucun jeton n'est émis à ce stade — voir /auth/verify-otp).
      await api.request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, mot_de_passe: motDePasse }),
      });
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Adresse e-mail ou mot de passe incorrect.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleCredential = async (credential: string) => {
    setError(null);
    setIsSubmitting(true);
    try {
      // Même étape 1 que le mot de passe : un code OTP est envoyé par
      // e-mail, la double authentification s'applique aussi à Google.
      await api.request('/auth/google', {
        method: 'POST',
        body: JSON.stringify({ id_token: credential }),
      });
      setGoogleCredential(credential);
      setEmail(decoderProfilGoogle(credential).email);
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connexion Google impossible.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyCode = async (code: string): Promise<string | null> => {
    try {
      const tokens = await api.request<TokenResponse>('/auth/verify-otp', {
        method: 'POST',
        body: JSON.stringify({ email, code }),
      });

      const isAdminUser = tokens.user_type === 'administrateur';
      setSession({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token }, isAdminUser);

      if (!isAdminUser) {
        // /auth/me n'existe que pour les clients (403 pour un administrateur).
        const moi = await api.request<Client>('/auth/me');
        setClient(moi);
      }

      navigate(isAdminUser ? '/admin' : '/dashboard');
      return null;
    } catch (err) {
      return err instanceof Error ? err.message : 'Code de vérification invalide ou expiré.';
    }
  };

  const handleResend = async (): Promise<string | null> => {
    try {
      // Réutilise /auth/login ou /auth/google (identifiants déjà validés
      // une première fois à l'étape 1, toujours en mémoire côté client)
      // plutôt qu'un endpoint dédié : évite d'exposer une route de renvoi
      // d'OTP sans ré-authentification.
      if (googleCredential) {
        await api.request('/auth/google', {
          method: 'POST',
          body: JSON.stringify({ id_token: googleCredential }),
        });
      } else {
        await api.request('/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email, mot_de_passe: motDePasse }),
        });
      }
      return null;
    } catch (err) {
      return err instanceof Error ? err.message : "Impossible de renvoyer le code.";
    }
  };

  return (
    <AuthLayout
      title={step === 1 ? 'Se connecter à MyNkap' : 'Vérification de sécurité'}
      subtitle={step === 1 ? 'Accédez à votre tableau de bord financier' : 'Saisissez le code reçu par e-mail'}
    >
      {step === 1 ? (
        <form onSubmit={handleSubmit} className="space-y-4">
          {compteVientDetreCree && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-secondary/10 border border-secondary/20 text-sm text-secondary font-medium">
              <Check className="h-4 w-4 shrink-0" />
              <span>Compte créé ! Connectez-vous pour continuer.</span>
            </div>
          )}
          <div className="space-y-1.5">
            <label htmlFor="email" className="text-sm font-medium">Adresse e-mail</label>
            <IconInput
              icon={Mail}
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="vous@gmail.com"
            />
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label htmlFor="mot_de_passe" className="text-sm font-medium">Mot de passe</label>
              <Link to="/forgot-password" className="text-xs text-secondary hover:underline font-medium">
                Mot de passe oublié ?
              </Link>
            </div>
            <PasswordInput
              id="mot_de_passe"
              required
              minLength={6}
              autoComplete="current-password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          {error && <p className="text-sm text-destructive text-center">{error}</p>}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-primary hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed text-primary-foreground font-semibold py-3 rounded-xl transition-all shadow-md flex items-center justify-center gap-2"
          >
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {isSubmitting ? 'Vérification des identifiants...' : 'Se connecter'}
          </button>

          <p className="text-center text-sm text-muted-foreground pt-1">
            Pas encore de compte ?{' '}
            <Link to="/register" className="text-secondary hover:underline font-medium">Créer un compte</Link>
          </p>

          <div className="flex items-center gap-3 pt-1">
            <div className="flex-1 h-px bg-border" />
            <span className="text-xs text-muted-foreground">ou</span>
            <div className="flex-1 h-px bg-border" />
          </div>

          <GoogleSignInButton onCredential={handleGoogleCredential} />
        </form>
      ) : (
        <OtpVerificationStep
          email={email}
          onVerifyCode={handleVerifyCode}
          onResend={handleResend}
          onBackToLogin={() => { setStep(1); setGoogleCredential(null); }}
        />
      )}
    </AuthLayout>
  );
};

import { ClientDashboard } from '../pages/ClientDashboard';
import { AdminDashboard } from '../pages/AdminDashboard';

// Garde de route réservé aux clients authentifiés
const RequireClientAuth = ({ children }: { children: React.ReactElement }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

// Garde de route réservé aux administrateurs (Superadmin / Modérateur / Support)
const RequireAdminAuth = ({ children }: { children: React.ReactElement }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isAdmin = useAuthStore((state) => state.isAdmin);

  if (!isAuthenticated || !isAdmin) {
    return <Navigate to="/login?admin=1" replace />;
  }
  return children;
};

export const AppRoutes: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/a-propos" element={<AboutPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route
          path="/dashboard"
          element={
            <RequireClientAuth>
              <ClientDashboard />
            </RequireClientAuth>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireAdminAuth>
              <AdminDashboard />
            </RequireAdminAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

const RegisterPage = () => {
  const navigate = useNavigate();

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [motDePasse, setMotDePasse] = useState('');
  const [confirmMotDePasse, setConfirmMotDePasse] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [prerempliParGoogle, setPrerempliParGoogle] = useState(false);

  const handleGoogleCredential = (credential: string) => {
    // Google ne fournit pas de numéro de téléphone (requis pour le Mobile
    // Money) : on ne peut pas créer le compte à la volée. On se contente de
    // pré-remplir le formulaire — le mot de passe et le téléphone restent à
    // saisir avant de soumettre /auth/register normalement.
    const profil = decoderProfilGoogle(credential);
    setError(null);
    setPrerempliParGoogle(true);
    if (profil.email) setEmail(profil.email);
    if (profil.prenom) setFirstName(profil.prenom);
    if (profil.nom) setLastName(profil.nom);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (motDePasse !== confirmMotDePasse) {
      setError('Les mots de passe ne correspondent pas.');
      return;
    }

    setIsSubmitting(true);
    try {
      await api.request<Client>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          email,
          mot_de_passe: motDePasse,
          first_name: firstName,
          last_name: lastName,
          phone,
        }),
      });

      // Pas de connexion automatique : l'inscription ne renvoie aucun
      // jeton, seule /auth/login (suivi du code OTP envoyé par e-mail)
      // établit une session. On redirige vers /login pour ce vrai flux.
      navigate('/login?compte_cree=1');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Une erreur est survenue.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Créer votre compte MyNkap"
      subtitle="Commencez à maîtriser vos finances en quelques secondes"
      maxWidthClassName="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <GoogleSignInButton onCredential={handleGoogleCredential} />
        {prerempliParGoogle && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-secondary/10 border border-secondary/20 text-sm text-secondary font-medium">
            <Check className="h-4 w-4 shrink-0" />
            <span>Infos reprises de votre compte Google. Ajoutez votre téléphone et un mot de passe pour terminer.</span>
          </div>
        )}

        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-border" />
          <span className="text-xs text-muted-foreground">ou remplissez le formulaire</span>
          <div className="flex-1 h-px bg-border" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label htmlFor="first_name" className="text-sm font-medium">Prénom</label>
            <IconInput
              icon={User}
              id="first_name"
              type="text"
              required
              autoComplete="given-name"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="Mohamed"
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="last_name" className="text-sm font-medium">Nom</label>
            <IconInput
              icon={User}
              id="last_name"
              type="text"
              required
              autoComplete="family-name"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Legrand"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="email" className="text-sm font-medium">Adresse e-mail</label>
          <IconInput
            icon={Mail}
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="vous@gmail.com"
          />
        </div>

        <div className="space-y-1.5">
          <label htmlFor="phone" className="text-sm font-medium">Téléphone</label>
          <IconInput
            icon={Phone}
            id="phone"
            type="tel"
            required
            autoComplete="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+237 6XX XXX XXX"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label htmlFor="mot_de_passe" className="text-sm font-medium">Mot de passe</label>
            <PasswordInput
              id="mot_de_passe"
              required
              minLength={8}
              autoComplete="new-password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="confirm_mot_de_passe" className="text-sm font-medium">Confirmer</label>
            <PasswordInput
              id="confirm_mot_de_passe"
              required
              minLength={8}
              autoComplete="new-password"
              value={confirmMotDePasse}
              onChange={(e) => setConfirmMotDePasse(e.target.value)}
              placeholder="••••••••"
            />
          </div>
        </div>

        {error && <p className="text-sm text-destructive text-center">{error}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-primary hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed text-primary-foreground font-semibold py-3 rounded-xl transition-all shadow-md flex items-center justify-center gap-2"
        >
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
          {isSubmitting ? 'Création du compte...' : 'Créer mon compte'}
        </button>

        <p className="text-center text-sm text-muted-foreground pt-1">
          Déjà un compte ?{' '}
          <Link to="/login" className="text-secondary hover:underline font-medium">Se connecter</Link>
        </p>
      </form>
    </AuthLayout>
  );
};

const ForgotPasswordPage = () => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await api.request('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
      setIsSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Une erreur est survenue.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Mot de passe oublié"
      subtitle="Indiquez votre e-mail pour recevoir un lien de réinitialisation"
    >
      {isSubmitted ? (
        <div className="text-center space-y-4">
          <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
            <Check className="h-6 w-6" />
          </div>
          <p className="text-sm text-muted-foreground">
            Si un compte existe pour <span className="font-medium text-foreground">{email}</span>, un e-mail de
            réinitialisation vient de lui être envoyé.
          </p>
          <Link to="/login" className="block text-sm text-secondary hover:underline font-medium">
            Retour à la connexion
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="email" className="text-sm font-medium">Adresse e-mail</label>
            <IconInput
              icon={Mail}
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="vous@gmail.com"
            />
          </div>

          {error && <p className="text-sm text-destructive text-center">{error}</p>}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-primary hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed text-primary-foreground font-semibold py-3 rounded-xl transition-all shadow-md flex items-center justify-center gap-2"
          >
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {isSubmitting ? 'Envoi en cours...' : 'Envoyer le lien de réinitialisation'}
          </button>

          <p className="text-center text-sm text-muted-foreground pt-1">
            <Link to="/login" className="text-secondary hover:underline font-medium">Retour à la connexion</Link>
          </p>
        </form>
      )}
    </AuthLayout>
  );
};

const ResetPasswordPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [nouveauMotDePasse, setNouveauMotDePasse] = useState('');
  const [confirmMotDePasse, setConfirmMotDePasse] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (nouveauMotDePasse !== confirmMotDePasse) {
      setError('Les mots de passe ne correspondent pas.');
      return;
    }

    setIsSubmitting(true);
    try {
      await api.request('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({ token, nouveau_mot_de_passe: nouveauMotDePasse }),
      });
      setIsSuccess(true);
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Une erreur est survenue.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout title="Réinitialiser le mot de passe" subtitle="Choisissez un nouveau mot de passe">
      {!token ? (
        <p className="text-sm text-destructive text-center">
          Ce lien de réinitialisation est invalide. Merci de refaire une demande depuis la page{' '}
          <Link to="/forgot-password" className="text-secondary hover:underline font-medium">mot de passe oublié</Link>.
        </p>
      ) : isSuccess ? (
        <div className="text-center space-y-4">
          <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
            <Check className="h-6 w-6" />
          </div>
          <p className="text-sm text-muted-foreground">
            Mot de passe modifié avec succès. Redirection vers la connexion...
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="nouveau_mot_de_passe" className="text-sm font-medium">Nouveau mot de passe</label>
            <PasswordInput
              id="nouveau_mot_de_passe"
              required
              minLength={8}
              autoComplete="new-password"
              value={nouveauMotDePasse}
              onChange={(e) => setNouveauMotDePasse(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="confirm_mot_de_passe" className="text-sm font-medium">Confirmer</label>
            <PasswordInput
              id="confirm_mot_de_passe"
              required
              minLength={8}
              autoComplete="new-password"
              value={confirmMotDePasse}
              onChange={(e) => setConfirmMotDePasse(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          {error && <p className="text-sm text-destructive text-center">{error}</p>}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-primary hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed text-primary-foreground font-semibold py-3 rounded-xl transition-all shadow-md flex items-center justify-center gap-2"
          >
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {isSubmitting ? 'Modification en cours...' : 'Réinitialiser le mot de passe'}
          </button>
        </form>
      )}
    </AuthLayout>
  );
};


