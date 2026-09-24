// Indicatifs téléphoniques des pays couverts par HR-Skills Pay (voir
// GET /abonnement/pays-disponibles, source de vérité pour la liste des
// pays/opérateurs). Recopiés ici uniquement pour préremplir le numéro —
// un pays absent de cette table reste utilisable, simplement sans préfixe
// affiché (le client saisit alors son numéro complet comme avant).
export const INDICATIFS_PAYS: Record<string, string> = {
  CM: '237', // Cameroun
  SN: '221', // Sénégal
  CI: '225', // Côte d'Ivoire
  GA: '241', // Gabon
  CD: '243', // RD Congo
  CG: '242', // Congo Brazzaville
  TD: '235', // Tchad
  CF: '236', // République Centrafricaine
  ML: '223', // Mali
  BF: '226', // Burkina Faso
  TG: '228', // Togo
  BJ: '229', // Bénin
  NE: '227', // Niger
  GW: '245', // Guinée-Bissau
  GN: '224', // Guinée
  GM: '220', // Gambie
};

// Nettoie un numéro tel que saisi ou déjà enregistré (espaces, tirets,
// "+", indicatif déjà présent, zéro initial local) pour ne garder que le
// numéro local à concaténer après l'indicatif affiché en préfixe fixe du
// champ. Ex: extraireNumeroLocal('+237 06 55 50 03 93', 'CM') -> '655500393'.
export const extraireNumeroLocal = (numeroBrut: string, pays: string): string => {
  let chiffres = numeroBrut.replace(/\D/g, '');
  const indicatif = INDICATIFS_PAYS[pays];
  if (indicatif && chiffres.startsWith(indicatif)) {
    chiffres = chiffres.slice(indicatif.length);
  }
  return chiffres.replace(/^0+/, '');
};
