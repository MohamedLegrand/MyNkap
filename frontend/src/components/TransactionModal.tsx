import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, ArrowDownCircle, ArrowUpCircle, Wallet, Tag, FileText, Calendar, Loader2, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { ICONES_CATEGORIE, ICONE_CATEGORIE_PAR_DEFAUT } from '../utils/categorieIcons';
import type { CompteFinancier, Categorie, Transaction } from '../types';

interface TransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  // Historique récent, pour trier les catégories par fréquence d'usage
  // (les plus utilisées en premier) — optionnel, dégrade simplement vers
  // l'ordre par défaut si non fourni.
  transactions?: Transaction[];
}

// Format YYYY-MM-DD en heure locale (pas toISOString(), qui bascule sur UTC
// et peut faire retomber sur "hier" pour tout utilisateur à l'est de
// Greenwich en fin de journée — ce qui inclut l'Afrique Centrale).
const formatDateLocale = (d: Date): string => {
  const annee = d.getFullYear();
  const mois = String(d.getMonth() + 1).padStart(2, '0');
  const jour = String(d.getDate()).padStart(2, '0');
  return `${annee}-${mois}-${jour}`;
};

const AUJOURDHUI = formatDateLocale(new Date());

// Mémorise le dernier compte utilisé (par appareil, jamais synchronisé
// entre clients) pour le présélectionner au prochain ajout — évite un
// clic répétitif à chaque saisie pour qui utilise toujours le même compte.
const CLE_DERNIER_COMPTE = 'mynkap_dernier_compte_transaction';

const MONTANTS_RAPIDES = [500, 1000, 2000, 5000, 10000];

// Correspondance mot-clé -> nom de catégorie par défaut (voir
// budgets.service.CATEGORIES_PAR_DEFAUT côté backend), pour suggérer une
// catégorie de dépense pendant la saisie de la description. Volontairement
// une simple recherche de sous-chaîne, pas d'IA : rapide, prévisible, sans
// appel réseau. Ne s'applique qu'aux dépenses — les catégories de revenu
// sont trop peu nombreuses pour en avoir besoin.
const MOTS_CLES_PAR_CATEGORIE: Record<string, string[]> = {
  'Alimentation': ['marché', 'marche', 'restaurant', 'nourriture', 'repas', 'courses', 'supermarché', 'supermarche', 'boisson'],
  'Transport': ['taxi', 'moto', 'essence', 'carburant', 'bus', 'transport', 'uber', 'péage', 'peage', 'moto-taxi'],
  'Logement': ['loyer', 'maison', 'charges', 'entretien'],
  'Santé': ['pharmacie', 'médecin', 'medecin', 'hôpital', 'hopital', 'médicament', 'medicament', 'clinique'],
  'Éducation': ['école', 'ecole', 'université', 'universite', 'scolarité', 'scolarite', 'fournitures', 'formation'],
  'Factures & Services': ['facture', 'internet', 'abonnement', 'électricité', 'electricite', 'eau', 'téléphone', 'telephone'],
  'Loisirs': ['cinéma', 'cinema', 'sortie', 'jeu', 'concert', 'fête', 'fete', 'bar'],
  'Achats personnels': ['vêtement', 'vetement', 'chaussure', 'habit', 'shopping', 'coiffure'],
};

export const TransactionModal: React.FC<TransactionModalProps> = ({ isOpen, onClose, onSuccess, transactions }) => {
  const { t } = useTranslation();
  const [type, setType] = useState<'DEPENSE' | 'REVENU'>('DEPENSE');
  const [montant, setMontant] = useState('');
  const [idCompte, setIdCompte] = useState('');
  const [idCategorie, setIdCategorie] = useState('');
  const [categorieChoisieManuellement, setCategorieChoisieManuellement] = useState(false);
  const [description, setDescription] = useState('');
  const [date, setDate] = useState(AUJOURDHUI);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [comptes, setComptes] = useState<CompteFinancier[]>([]);
  const [categories, setCategories] = useState<Categorie[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Création du tout premier compte financier (aucune transaction n'est
  // possible sans compte source/destination) : nom + type suffisent, le
  // solde de départ est facultatif.
  const [nouveauCompteNom, setNouveauCompteNom] = useState('');
  const [nouveauCompteType, setNouveauCompteType] = useState<'MOBILE_MONEY' | 'BANCAIRE' | 'ESPECES'>('MOBILE_MONEY');
  const [nouveauCompteSolde, setNouveauCompteSolde] = useState('');
  const [isCreatingCompte, setIsCreatingCompte] = useState(false);

  const chargerComptesEtCategories = () => {
    setError(null);
    setIsLoading(true);
    return Promise.all([api.request<CompteFinancier[]>('/comptes'), api.request<Categorie[]>('/categories')])
      .then(([comptesData, categoriesData]) => {
        setComptes(comptesData);
        setCategories(categoriesData);
        if (comptesData.length > 0) {
          let dernierCompte: string | null = null;
          try {
            dernierCompte = localStorage.getItem(CLE_DERNIER_COMPTE);
          } catch {
            // Stockage indisponible (navigation privée...) : retombe sur le premier compte.
          }
          const dernierToujoursValide = dernierCompte && comptesData.some((c) => String(c.id_compte) === dernierCompte);
          setIdCompte(dernierToujoursValide ? dernierCompte! : String(comptesData[0].id_compte));
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : t('modals.transaction.error_load')))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    if (!isOpen) return;
    // Chargement à l'ouverture de la modale, pas une synchronisation d'état
    // dérivé d'un rendu précédent.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    chargerComptesEtCategories();
    setDate(AUJOURDHUI);
    setCategorieChoisieManuellement(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const handleCreerCompte = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsCreatingCompte(true);
    try {
      await api.request('/comptes', {
        method: 'POST',
        body: JSON.stringify({
          nom: nouveauCompteNom,
          type: nouveauCompteType,
          solde_initial: nouveauCompteSolde ? Number(nouveauCompteSolde) : 0,
        }),
      });
      setNouveauCompteNom('');
      setNouveauCompteSolde('');
      await chargerComptesEtCategories();
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.compte.error_create'));
    } finally {
      setIsCreatingCompte(false);
    }
  };

  const categoriesFiltrees = categories.filter((c) => c.type === type);

  // Les plus utilisées récemment en premier — plus rapide à repérer dans
  // la grille qu'un ordre alphabétique ou de création.
  const frequenceParCategorie = useMemo(() => {
    const compte: Record<number, number> = {};
    for (const tx of transactions ?? []) {
      if (tx.id_categorie != null) compte[tx.id_categorie] = (compte[tx.id_categorie] ?? 0) + 1;
    }
    return compte;
  }, [transactions]);

  const categoriesTriees = useMemo(
    () => [...categoriesFiltrees].sort((a, b) => (frequenceParCategorie[b.id_categorie] ?? 0) - (frequenceParCategorie[a.id_categorie] ?? 0)),
    [categoriesFiltrees, frequenceParCategorie]
  );

  useEffect(() => {
    // Réinitialise la catégorie sélectionnée quand la liste filtrée change
    // (bascule DEPENSE/REVENU) — un choix de l'utilisateur reste ensuite
    // libre tant que la liste ne change pas, ce n'est pas un état dérivable
    // en continu.
    if (categoriesFiltrees.length > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIdCategorie(String(categoriesFiltrees[0].id_categorie));
    } else {
      setIdCategorie('');
    }
    setCategorieChoisieManuellement(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, categories]);

  useEffect(() => {
    // Suggestion automatique de catégorie à partir de la description — ne
    // prend jamais le dessus sur un choix déjà fait explicitement par le
    // client (voir categorieChoisieManuellement), et seulement pour une
    // dépense (les catégories de revenu sont trop peu nombreuses pour ça).
    if (type !== 'DEPENSE' || categorieChoisieManuellement || !description.trim()) return;
    const texte = description.toLowerCase();
    for (const [nomCategorie, motsCles] of Object.entries(MOTS_CLES_PAR_CATEGORIE)) {
      if (motsCles.some((mot) => texte.includes(mot))) {
        const trouvee = categoriesFiltrees.find((c) => c.nom === nomCategorie);
        if (trouvee) {
          // eslint-disable-next-line react-hooks/set-state-in-effect
          setIdCategorie(String(trouvee.id_categorie));
        }
        break;
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [description]);

  if (!isOpen) return null;

  const memoriserDernierCompte = (id: string) => {
    try {
      localStorage.setItem(CLE_DERNIER_COMPTE, id);
    } catch {
      // Stockage indisponible : purement un confort, jamais bloquant.
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idCompte || !idCategorie) return;

    setError(null);
    setIsSubmitting(true);
    try {
      await api.request('/transactions', {
        method: 'POST',
        body: JSON.stringify({
          id_compte: Number(idCompte),
          id_categorie: Number(idCategorie),
          montant: Number(montant),
          type,
          description: description || undefined,
          date,
        }),
      });
      memoriserDernierCompte(idCompte);
      setMontant('');
      setDescription('');
      setDate(AUJOURDHUI);
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.transaction.error_generic'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 max-h-[90vh] flex flex-col">
        {/* Header Modal */}
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40 shrink-0">
          <h3 className="text-lg font-bold tracking-tight">{t('modals.transaction.title')}</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {isLoading ? (
          <div className="p-10 flex justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : comptes.length === 0 ? (
          <form onSubmit={handleCreerCompte} className="p-6 space-y-4 overflow-y-auto">
            <div className="text-center space-y-2">
              <AlertTriangle className="h-8 w-8 mx-auto text-amber-500" />
              <p className="text-sm font-semibold text-foreground">{t('modals.transaction.no_account')}</p>
              <p className="text-xs text-muted-foreground">
                {t('modals.transaction.no_account_desc')}
              </p>
            </div>

            {error && <p className="text-sm text-destructive text-center">{error}</p>}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('modals.compte.name_label')}</label>
              <input
                type="text"
                required
                placeholder={t('modals.compte.name_placeholder')}
                value={nouveauCompteNom}
                onChange={(e) => setNouveauCompteNom(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('modals.compte.type_label')}</label>
              <select
                value={nouveauCompteType}
                onChange={(e) => setNouveauCompteType(e.target.value as 'MOBILE_MONEY' | 'BANCAIRE' | 'ESPECES')}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="MOBILE_MONEY">{t('modals.compte.type_mobile_money')}</option>
                <option value="BANCAIRE">{t('modals.compte.type_bank')}</option>
                <option value="ESPECES">{t('modals.compte.type_cash')}</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('modals.compte.initial_balance_label')}</label>
              <input
                type="number"
                min={0}
                placeholder="0"
                value={nouveauCompteSolde}
                onChange={(e) => setNouveauCompteSolde(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="pt-2 flex gap-3">
              <button type="button" onClick={onClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                disabled={isCreatingCompte}
                className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isCreatingCompte && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>{t('modals.compte.title_create')}</span>
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto">
            {/* Selector Type (DEPENSE / REVENU) */}
            <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
              <button
                type="button"
                onClick={() => setType('DEPENSE')}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition-all ${
                  type === 'DEPENSE'
                    ? 'bg-destructive text-destructive-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <ArrowDownCircle className="h-4 w-4" />
                <span>{t('categories.expense')}</span>
              </button>
              <button
                type="button"
                onClick={() => setType('REVENU')}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition-all ${
                  type === 'REVENU'
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <ArrowUpCircle className="h-4 w-4" />
                <span>{t('modals.transaction.income_deposit')}</span>
              </button>
            </div>

            {/* Montant (XAF) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('modals.transaction.amount_label')}</label>
              <div className="relative">
                <input
                  type="number"
                  required
                  min={1}
                  step={1}
                  placeholder="ex: 15000"
                  value={montant}
                  onChange={(e) => setMontant(e.target.value)}
                  className="w-full bg-background border border-border rounded-xl px-4 py-3 text-lg font-bold focus:outline-none focus:ring-2 focus:ring-primary pr-16"
                />
                <span className="absolute right-4 top-3.5 text-xs font-black text-muted-foreground uppercase">XAF</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {MONTANTS_RAPIDES.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMontant(String(m))}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-colors ${
                      montant === String(m)
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'border-border text-muted-foreground hover:border-primary/50 hover:text-foreground'
                    }`}
                  >
                    {m.toLocaleString('fr-FR')}
                  </button>
                ))}
              </div>
            </div>

            {/* Date de l'opération (modifiable pour rattraper une transaction oubliée) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" />
                <span>{t('modals.transaction.date_label')}</span>
              </label>
              <input
                type="date"
                required
                max={AUJOURDHUI}
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {date !== AUJOURDHUI && (
                <p className="text-[11px] text-muted-foreground">
                  {t('modals.transaction.backdated_hint')}
                </p>
              )}
            </div>

            {/* Compte Source */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                <Wallet className="h-3.5 w-3.5" />
                <span>{t('modals.transaction.account_label')}</span>
              </label>
              <select
                value={idCompte}
                onChange={(e) => setIdCompte(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {comptes.map((c) => (
                  <option key={c.id_compte} value={c.id_compte}>
                    {c.nom} ({c.solde.toLocaleString('fr-FR')} {c.devise})
                  </option>
                ))}
              </select>
            </div>

            {/* Catégorie */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                <Tag className="h-3.5 w-3.5" />
                <span>{t('modals.transaction.category_label')}</span>
              </label>
              {categoriesTriees.length === 0 ? (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  {type === 'DEPENSE' ? t('modals.transaction.no_expense_category') : t('modals.transaction.no_income_category')}
                </p>
              ) : (
                <div className="grid grid-cols-3 gap-2">
                  {categoriesTriees.map((c) => {
                    const Icon = (c.icone && ICONES_CATEGORIE[c.icone]) || ICONE_CATEGORIE_PAR_DEFAUT;
                    const selectionnee = idCategorie === String(c.id_categorie);
                    return (
                      <button
                        key={c.id_categorie}
                        type="button"
                        onClick={() => {
                          setIdCategorie(String(c.id_categorie));
                          setCategorieChoisieManuellement(true);
                        }}
                        className={`flex flex-col items-center gap-1 py-2.5 px-1 rounded-xl border text-[11px] font-semibold transition-colors ${
                          selectionnee
                            ? 'border-primary bg-primary/10 text-primary'
                            : 'border-border text-muted-foreground hover:border-primary/40 hover:text-foreground'
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                        <span className="truncate w-full text-center">{c.nom}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5" />
                <span>{t('modals.transfert.note_label')}</span>
              </label>
              <input
                type="text"
                placeholder={t('modals.transaction.description_placeholder')}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {error && <p className="text-sm text-destructive text-center">{error}</p>}

            {/* Action Footer */}
            <div className="pt-2 flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted transition-colors"
              >
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !idCategorie}
                className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>{isSubmitting ? t('modals.transaction.saving') : t('transactions.make')}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
