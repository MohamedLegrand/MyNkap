// Génère un mot de passe aléatoire côté navigateur (Web Crypto, pas
// Math.random) — exclut les caractères visuellement ambigus (0/O, 1/l/I)
// pour rester lisible si l'admin doit le retaper ou le communiquer.
const CARACTERES = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%&*';

export const genererMotDePasse = (longueur = 14): string => {
  const valeurs = new Uint32Array(longueur);
  crypto.getRandomValues(valeurs);
  return Array.from(valeurs, (v) => CARACTERES[v % CARACTERES.length]).join('');
};
