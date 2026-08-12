// Catalogue fermé, miroir exact de budgets.schemas.COULEURS_CATEGORIE côté
// backend — seules ces valeurs sont proposées à la sélection et acceptées
// à l'enregistrement (le serveur revalide de toute façon côté API).
export const COULEURS_CATEGORIE: { valeur: string; labelKey: string }[] = [
  { valeur: '#254E2A', labelKey: 'colors.forest_green' },
  { valeur: '#22C55E', labelKey: 'colors.green' },
  { valeur: '#F97316', labelKey: 'colors.orange' },
  { valeur: '#EF4444', labelKey: 'colors.red' },
  { valeur: '#EAB308', labelKey: 'colors.yellow' },
  { valeur: '#3B82F6', labelKey: 'colors.blue' },
  { valeur: '#8B5CF6', labelKey: 'colors.purple' },
  { valeur: '#EC4899', labelKey: 'colors.pink' },
  { valeur: '#14B8A6', labelKey: 'colors.teal' },
  { valeur: '#06B6D4', labelKey: 'colors.cyan' },
  { valeur: '#64748B', labelKey: 'colors.slate' },
  { valeur: '#F59E0B', labelKey: 'colors.amber' },
  { valeur: '#84CC16', labelKey: 'colors.lime' },
  { valeur: '#6366F1', labelKey: 'colors.indigo' },
];

export const COULEUR_CATEGORIE_PAR_DEFAUT = '#64748B';

export const estCouleurCategorieValide = (couleur: string | null | undefined): couleur is string =>
  !!couleur && COULEURS_CATEGORIE.some((c) => c.valeur === couleur);
