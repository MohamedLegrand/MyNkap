import React, { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { GOOGLE_CLIENT_ID } from '../config';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (response: { credential: string }) => void }) => void;
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
        };
      };
    };
  }
}

interface GoogleSignInButtonProps {
  onCredential: (credential: string) => void;
}

// Le SDK Google Identity Services (chargé une seule fois, réutilisé par
// tous les montages ultérieurs du composant) n'expose pas de callback
// React-friendly : on lui passe directement notre gestionnaire.
let scriptChargement: Promise<void> | null = null;
const chargerScriptGoogle = (): Promise<void> => {
  if (window.google) return Promise.resolve();
  if (scriptChargement) return scriptChargement;

  scriptChargement = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Impossible de charger Google Identity Services."));
    document.head.appendChild(script);
  });
  return scriptChargement;
};

export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({ onCredential }) => {
  const { i18n } = useTranslation();
  const conteneurRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !conteneurRef.current) return;
    let annule = false;

    chargerScriptGoogle()
      .then(() => {
        if (annule || !window.google || !conteneurRef.current) return;
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response) => onCredential(response.credential),
        });
        window.google.accounts.id.renderButton(conteneurRef.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          shape: 'pill',
          locale: i18n.language === 'en' ? 'en' : 'fr',
          width: 320,
        });
      })
      .catch(() => {
        // Échec silencieux : le formulaire e-mail/mot de passe reste
        // utilisable même si Google Identity Services est indisponible
        // (bloqueur de scripts, réseau...).
      });

    return () => {
      annule = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i18n.language]);

  if (!GOOGLE_CLIENT_ID) return null;

  return <div ref={conteneurRef} className="flex justify-center" />;
};
