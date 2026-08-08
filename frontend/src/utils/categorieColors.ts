// Catalogue fermé, miroir exact de budgets.schemas.COULEURS_CATEGORIE côté
// backend — seules ces valeurs sont proposées à la sélection et acceptées
// à l'enregistrement (le serveur revalide de toute façon côté API).
export const COULEURS_CATEGORIE: { valeur: string; label: string }[] = [
  { valeur: '#254E2A', label: 'Vert forêt' },
  { valeur: '#22C55E', label: 'Vert' },
  { valeur: '#F97316', label: 'Orange' },
  { valeur: '#EF4444', label: 'Rouge' },
  { valeur: '#EAB308', label: 'Jaune' },
  { valeur: '#3B82F6', label: 'Bleu' },
  { valeur: '#8B5CF6', label: 'Violet' },
  { valeur: '#EC4899', label: 'Rose' },
  { valeur: '#14B8A6', label: 'Sarcelle' },
  { valeur: '#06B6D4', label: 'Cyan' },
  { valeur: '#64748B', label: 'Ardoise' },
  { valeur: '#F59E0B', label: 'Ambre' },
  { valeur: '#84CC16', label: 'Citron vert' },
  { valeur: '#6366F1', label: 'Indigo' },
];

export const COULEUR_CATEGORIE_PAR_DEFAUT = '#64748B';

export const estCouleurCategorieValide = (couleur: string | null | undefined): couleur is string =>
  !!couleur && COULEURS_CATEGORIE.some((c) => c.valeur === couleur);
