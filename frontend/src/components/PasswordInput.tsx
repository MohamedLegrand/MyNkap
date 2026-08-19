import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Lock, Eye, EyeOff } from 'lucide-react';

interface PasswordInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  // Icône cadenas à gauche — activée par défaut (pages d'authentification),
  // désactivable pour s'aligner sur des formulaires dont les autres champs
  // n'ont pas d'icône (ex: modales admin).
  showLockIcon?: boolean;
}

// Champ mot de passe avec bouton afficher/masquer (œil), pour un rendu plus
// professionnel — partagé entre les pages d'authentification et les
// formulaires admin qui saisissent un mot de passe.
export const PasswordInput: React.FC<PasswordInputProps> = ({ className, showLockIcon = true, ...props }) => {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);

  const defaultClassName = showLockIcon
    ? 'w-full py-2.5 pl-11 pr-11 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40'
    : 'w-full bg-background border border-border rounded-xl pl-3.5 pr-11 py-2 text-sm font-semibold focus:ring-2 focus:ring-primary focus:outline-none';

  return (
    <div className="relative">
      {showLockIcon && (
        <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      )}
      <input
        {...props}
        type={visible ? 'text' : 'password'}
        className={className ?? defaultClassName}
      />
      <button
        type="button"
        onClick={() => setVisible((prev) => !prev)}
        aria-label={visible ? t('auth.hide_password') : t('auth.show_password')}
        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
      >
        {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
};
