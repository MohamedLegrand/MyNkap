import React, { useEffect, useState } from 'react';
import { X, ArrowDownCircle, ArrowUpCircle, Wallet, Tag, FileText, Loader2, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import type { CompteFinancier, Categorie } from '../types';

interface TransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const TransactionModal: React.FC<TransactionModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [type, setType] = useState<'DEPENSE' | 'REVENU'>('DEPENSE');
  const [montant, setMontant] = useState('');
  const [idCompte, setIdCompte] = useState('');
  const [idCategorie, setIdCategorie] = useState('');
  const [description, setDescription] = useState('');
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
    return Promise.all([
      api.request<CompteFinancier[]>('/comptes'),
      api.request<Categorie[]>('/categories'),
    ])
      .then(([comptesData, categoriesData]) => {
        setComptes(comptesData);
        setCategories(categoriesData);
        if (comptesData.length > 0) setIdCompte(String(comptesData[0].id_compte));
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Impossible de charger les comptes/catégories.'))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    if (!isOpen) return;
    // Chargement à l'ouverture de la modale, pas une synchronisation d'état
    // dérivé d'un rendu précédent.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    chargerComptesEtCategories();
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
      setError(err instanceof Error ? err.message : 'Création du compte impossible.');
    } finally {
      setIsCreatingCompte(false);
    }
  };

  const categoriesFiltrees = categories.filter((c) => c.type === type);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, categories]);

  if (!isOpen) return null;

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
        }),
      });
      setMontant('');
      setDescription('');
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Une erreur est survenue.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header Modal */}
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">Nouvelle Opération Financière</h3>
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
          <form onSubmit={handleCreerCompte} className="p-6 space-y-4">
            <div className="text-center space-y-2">
              <AlertTriangle className="h-8 w-8 mx-auto text-amber-500" />
              <p className="text-sm font-semibold text-foreground">Aucun compte financier</p>
              <p className="text-xs text-muted-foreground">
                Créez d'abord un compte financier (Mobile Money, banque, espèces...) avant d'enregistrer une transaction.
              </p>
            </div>

            {error && <p className="text-sm text-destructive text-center">{error}</p>}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Nom du compte</label>
              <input
                type="text"
                required
                placeholder="ex: Orange Money"
                value={nouveauCompteNom}
                onChange={(e) => setNouveauCompteNom(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Type de compte</label>
              <select
                value={nouveauCompteType}
                onChange={(e) => setNouveauCompteType(e.target.value as 'MOBILE_MONEY' | 'BANCAIRE' | 'ESPECES')}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="MOBILE_MONEY">Mobile Money (Orange, MTN...)</option>
                <option value="BANCAIRE">Compte bancaire</option>
                <option value="ESPECES">Espèces / Cash</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Solde de départ (facultatif)</label>
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
                Annuler
              </button>
              <button
                type="submit"
                disabled={isCreatingCompte}
                className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isCreatingCompte && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>Créer compte</span>
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
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
                <span>Dépense</span>
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
                <span>Revenu / Dépôt</span>
              </button>
            </div>

            {/* Montant (XAF) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Montant (FCFA / XAF)</label>
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
            </div>

            {/* Compte Source */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                <Wallet className="h-3.5 w-3.5" />
                <span>Compte Financier</span>
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
                <span>Catégorie</span>
              </label>
              {categoriesFiltrees.length === 0 ? (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  Aucune catégorie de type {type === 'DEPENSE' ? 'dépense' : 'revenu'} disponible.
                </p>
              ) : (
                <select
                  value={idCategorie}
                  onChange={(e) => setIdCategorie(e.target.value)}
                  className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  {categoriesFiltrees.map((c) => (
                    <option key={c.id_categorie} value={c.id_categorie}>
                      {c.nom}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5" />
                <span>Note / Description (facultatif)</span>
              </label>
              <input
                type="text"
                placeholder="ex: Taxi pour la réunion de 10h"
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
                Annuler
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !idCategorie}
                className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>{isSubmitting ? 'Enregistrement...' : 'Effectuer transaction'}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
