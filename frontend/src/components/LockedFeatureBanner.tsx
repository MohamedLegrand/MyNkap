import React from 'react';
import { useTranslation } from 'react-i18next';
import { Lock } from 'lucide-react';

interface LockedFeatureBannerProps {
  titre: string;
  // Nombre d'éléments déjà enregistrés par le client dans ce module avant
  // qu'il perde l'accès (fin d'essai, downgrade, échec de paiement) — les
  // données ne sont jamais supprimées, seul l'accès est restreint (voir
  // plans.service.compter_donnees_verrouillees côté backend). Omis ou à 0,
  // le message de comptage ne s'affiche pas.
  count?: number;
  onUpgrade?: () => void;
}

// Bannière partagée affichée à la place d'un module dont le forfait actuel
// ne couvre plus l'accès — remplace l'ancien composant local `Verrouille`
// de AutomatisationsSection.tsx, désormais réutilisé pour tous les modules
// à palier (dettes, épargne, tontines, JARVIS, analyse, automatisations).
export const LockedFeatureBanner: React.FC<LockedFeatureBannerProps> = ({ titre, count, onUpgrade }) => {
  const { t } = useTranslation();
  return (
    <div className="p-8 rounded-2xl border border-dashed border-border text-center space-y-3">
      <Lock className="h-6 w-6 mx-auto text-muted-foreground" />
      <p className="text-sm font-semibold text-foreground">{t('locked.not_included', { titre })}</p>
      {typeof count === 'number' && count > 0 && (
        <p className="text-xs text-secondary font-medium">{t('locked.saved_count', { count, titre })}</p>
      )}
      <p className="text-xs text-muted-foreground">{t('locked.upgrade_hint')}</p>
      {onUpgrade && (
        <button
          onClick={onUpgrade}
          className="inline-flex items-center gap-2 bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold py-2.5 px-5 rounded-xl transition-all shadow-sm"
        >
          {t('locked.upgrade_cta')}
        </button>
      )}
    </div>
  );
};
