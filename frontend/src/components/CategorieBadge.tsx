import React from 'react';
import { ICONES_CATEGORIE, ICONE_CATEGORIE_PAR_DEFAUT } from '../utils/categorieIcons';
import { COULEUR_CATEGORIE_PAR_DEFAUT, estCouleurCategorieValide } from '../utils/categorieColors';

interface CategorieBadgeProps {
  icone?: string | null;
  couleur?: string | null;
  size?: 'sm' | 'md';
  className?: string;
}

// Pastille ronde icône+couleur pour identifier une catégorie d'un coup
// d'œil (liste des catégories, lignes de transaction...). La couleur n'est
// jamais injectée telle quelle dans un style arbitraire : seule une valeur
// présente dans le catalogue fermé COULEURS_CATEGORIE est utilisée, sinon
// on retombe sur la couleur neutre par défaut.
export const CategorieBadge: React.FC<CategorieBadgeProps> = ({ icone, couleur, size = 'md', className = '' }) => {
  const Icon = (icone && ICONES_CATEGORIE[icone]) || ICONE_CATEGORIE_PAR_DEFAUT;
  const couleurSure = estCouleurCategorieValide(couleur) ? couleur : COULEUR_CATEGORIE_PAR_DEFAUT;
  const dimensions = size === 'sm' ? 'h-6 w-6' : 'h-9 w-9';
  const iconeTaille = size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4';

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full shrink-0 ${dimensions} ${className}`}
      style={{ backgroundColor: `${couleurSure}22`, color: couleurSure }}
    >
      <Icon className={iconeTaille} />
    </span>
  );
};
