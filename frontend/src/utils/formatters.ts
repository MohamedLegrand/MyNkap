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

/**
 * Date relative ("Il y a 5 min") pour un horodatage ISO renvoyé par le
 * backend. Le backend sérialise des datetime naïfs en UTC (datetime.utcnow(),
 * sans suffixe "Z") : `new Date(iso)` seul les interpréterait à tort comme
 * une heure locale, décalant l'affichage de tout le fuseau horaire du
 * navigateur (ex: "il y a 2 h" pour un événement qui vient de se produire).
 */
export const formatDateRelative = (iso: string): string => {
  const isoUTC = /[Zz]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : `${iso}Z`;
  const dateUTC = new Date(isoUTC);
  const diffMs = Date.now() - dateUTC.getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "À l'instant";
  if (minutes < 60) return `Il y a ${minutes} min`;
  const heures = Math.floor(minutes / 60);
  if (heures < 24) return `Il y a ${heures} h`;
  const jours = Math.floor(heures / 24);
  if (jours < 7) return `Il y a ${jours} j`;
  return dateUTC.toLocaleDateString('fr-FR');
};
