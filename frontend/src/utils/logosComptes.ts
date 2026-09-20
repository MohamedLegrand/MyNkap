import type { CompteFinancier } from '../types';

// Logos prédéfinis proposables au client pour ses comptes (fichiers de
// public/). Les chemins doivent rester acceptés par le validateur du
// backend (comptes.schemas.LOGO_PREDEFINI) : tout autre chemin est refusé.
export const LOGOS_PREDEFINIS: { id: string; label: string; src: string }[] = [
  { id: 'orange', label: 'Orange Money', src: '/mobile-money/orange-money.jpg' },
  { id: 'mtn', label: 'MTN MoMo', src: '/mobile-money/mtn.jpg' },
  { id: 'moov', label: 'Moov Money', src: '/mobile-money/movv-money.png' },
  { id: 'airtel', label: 'Airtel Money', src: '/mobile-money/airtel-money.jpg' },
  { id: 'wave', label: 'Wave', src: '/mobile-money/wave.jpg' },
  { id: 'mpesa', label: 'M-Pesa', src: '/mobile-money/m-pesa.jpg' },
  { id: 'afrimoney', label: 'AfriMoney', src: '/mobile-money/afrimoney.png' },
  { id: 'coris', label: 'Coris Money', src: '/mobile-money/coris-money.avif' },
  { id: 'expresso', label: 'Expresso', src: '/mobile-money/expresso.jpg' },
  { id: 'flooz', label: 'Flooz', src: '/mobile-money/flooz.jpg' },
  { id: 'qmoney', label: 'QMoney', src: '/mobile-money/q-money.jpg' },
  { id: 'tmoney', label: 'TMoney', src: '/mobile-money/t-money.webp' },
  { id: 'mobile-money', label: 'Mobile Money', src: '/mobile-money/mobile-money.jpg' },
  { id: 'carte-bancaire', label: 'Carte bancaire', src: '/mobile-money/carte-bancaire.jpg' },
  { id: 'cash', label: 'Espèces', src: '/cash.jpg' },
];

// Logo par défaut d'un compte SANS logo choisi : seulement mobile money
// (Orange reconnu dans le nom, sinon MTN MoMo) et espèces. Tous les autres
// types (bancaire, épargne...) restent sans logo tant que le client n'en a
// pas choisi ou importé un.
const logoParDefaut = (compte: Pick<CompteFinancier, 'type' | 'nom'>): string | null => {
  if (compte.type === 'ESPECES') return '/cash.jpg';
  if (compte.type === 'MOBILE_MONEY') {
    return compte.nom.toLowerCase().includes('orange') ? '/orange.jpg' : '/momo.jpg';
  }
  return null;
};

// Logo à afficher : le choix du client (prédéfini ou importé) prime, puis le
// logo par défaut du type, sinon null (logo vide).
export const obtenirLogoCompte = (compte: Pick<CompteFinancier, 'type' | 'nom' | 'logo'>): string | null =>
  compte.logo || logoParDefaut(compte);

// Formats acceptés à l'import (mêmes que le backend : SVG exclu, il peut
// embarquer du script) et taille maximale (3 Mo, comme la photo de profil).
export const TYPES_LOGO_IMPORTE = ['image/jpeg', 'image/png', 'image/webp'];
export const TAILLE_MAX_LOGO_OCTETS = 3 * 1024 * 1024;
