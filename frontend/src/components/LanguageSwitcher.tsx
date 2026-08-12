import React from 'react';
import { useTranslation } from 'react-i18next';
import { Languages } from 'lucide-react';
import { CLE_LANGUE_STOCKEE } from '../i18n';

interface LanguageSwitcherProps {
  className?: string;
}

// Bascule FR/EN — le bouton affiche toujours la langue actuellement active
// (comme ThemeToggle affiche l'état actuel, pas l'état cible). Le choix est
// mémorisé en localStorage pour survivre à un rafraîchissement/nouvelle visite.
export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({ className = '' }) => {
  const { i18n } = useTranslation();
  const langueActuelle = i18n.language === 'en' ? 'en' : 'fr';

  const basculerLangue = () => {
    const nouvelleLangue = langueActuelle === 'fr' ? 'en' : 'fr';
    i18n.changeLanguage(nouvelleLangue);
    localStorage.setItem(CLE_LANGUE_STOCKEE, nouvelleLangue);
  };

  return (
    <button
      onClick={basculerLangue}
      aria-label={langueActuelle === 'fr' ? 'Switch to English' : 'Passer en français'}
      title={langueActuelle === 'fr' ? 'Switch to English' : 'Passer en français'}
      className={`flex items-center gap-1.5 px-2.5 py-2 rounded-xl bg-muted hover:bg-accent text-foreground border border-border transition-colors duration-150 text-xs font-bold ${className}`}
    >
      <Languages className="h-4 w-4 text-muted-foreground" />
      <span>{langueActuelle.toUpperCase()}</span>
    </button>
  );
};
