// Utilitaires de formatage (devises, dates, etc.)

/**
 * Formate un montant numérique en Franc CFA (XAF).
 */
export const formatXAF = (amount: number): string => {
  return new Intl.NumberFormat('fr-CM', {
    style: 'currency',
    currency: 'XAF',
    minimumFractionDigits: 0,
  }).format(amount);
};

/**
 * Formate une chaîne de date au format local (fr-FR/fr-CM).
 */
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'medium',
  }).format(date);
};
