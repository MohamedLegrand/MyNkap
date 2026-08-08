import React, { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { Budget, Categorie } from '../types';

interface BudgetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  categoriesDepense: Categorie[];
  // Présent = mode édition (PUT sur ce budget, seul le plafond change) ;
  // absent/null = création.
  budget?: Budget | null;
  nomCategorie?: (id: number | null) => string;
}

const MOIS_LABELS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
];

export const BudgetModal: React.FC<BudgetModalProps> = ({
  isOpen, onClose, onSuccess, categoriesDepense, budget = null, nomCategorie,
}) => {
  const modeEdition = budget !== null;
  const maintenant = new Date();
  const [idCategorie, setIdCategorie] = useState('');
  const [montantLimite, setMontantLimite] = useState('');
  const [mois, setMois] = useState(maintenant.getMonth() + 1);
  const [annee, setAnnee] = useState(maintenant.getFullYear());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && categoriesDepense.length > 0 && !idCategorie && !modeEdition) {
      // Présélectionne la première catégorie de dépense à l'ouverture — pas
      // une synchronisation d'état dérivé d'un rendu précédent.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIdCategorie(String(categoriesDepense[0].id_categorie));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, categoriesDepense]);

  useEffect(() => {
    // Relit le budget depuis le serveur à l'ouverture (recalcule aussi ses
    // alertes) plutôt que de se fier à la liste locale — pas une
    // synchronisation d'état dérivé d'un rendu précédent.
    if (isOpen && budget) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsLoadingDetail(true);
      setError(null);
      api
        .request<Budget>(`/budgets/${budget.id_budget}`)
        .then((frais) => {
          setIdCategorie(String(frais.id_categorie));
          setMontantLimite(String(frais.montant_limite));
          setMois(frais.mois);
          setAnnee(frais.annee);
        })
        .catch((err) => setError(err instanceof Error ? err.message : 'Impossible de charger ce budget.'))
        .finally(() => setIsLoadingDetail(false));
    } else if (isOpen) {
      setMontantLimite('');
    }
  }, [isOpen, budget]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idCategorie) return;
    setError(null);
    setIsSubmitting(true);
    try {
      if (modeEdition && budget) {
        await api.request(`/budgets/${budget.id_budget}`, {
          method: 'PUT',
          body: JSON.stringify({ montant_limite: Number(montantLimite) }),
        });
      } else {
        await api.request('/budgets', {
          method: 'POST',
          body: JSON.stringify({ id_categorie: Number(idCategorie), montant_limite: Number(montantLimite), mois, annee }),
        });
      }
      setMontantLimite('');
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : `${modeEdition ? 'Modification' : 'Définition'} du budget impossible.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">{modeEdition ? 'Modifier budget' : 'Définir budget'}</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {isLoadingDetail ? (
          <div className="flex justify-center py-14">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : !modeEdition && categoriesDepense.length === 0 ? (
          <div className="p-6 space-y-3 text-center">
            <p className="text-sm text-muted-foreground">
              Créez d'abord une catégorie de dépense pour pouvoir lui définir un budget.
            </p>
            <button onClick={onClose} className="text-sm font-bold text-primary hover:underline">
              Fermer
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {modeEdition ? (
              <p className="text-xs text-muted-foreground">
                <strong className="text-foreground">{nomCategorie ? nomCategorie(Number(idCategorie)) : `Catégorie #${idCategorie}`}</strong>
                {' '}— {MOIS_LABELS[mois - 1]} {annee}
              </p>
            ) : (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Catégorie de dépense</label>
                <select
                  value={idCategorie}
                  onChange={(e) => setIdCategorie(e.target.value)}
                  className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  {categoriesDepense.map((c) => (
                    <option key={c.id_categorie} value={c.id_categorie}>{c.nom}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Plafond mensuel (FCFA / XAF)</label>
              <input
                type="number"
                required
                min={1}
                step={1}
                placeholder="ex: 50000"
                value={montantLimite}
                onChange={(e) => setMontantLimite(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {!modeEdition && (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Mois</label>
                  <select
                    value={mois}
                    onChange={(e) => setMois(Number(e.target.value))}
                    className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    {MOIS_LABELS.map((label, idx) => (
                      <option key={label} value={idx + 1}>{label}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Année</label>
                  <input
                    type="number"
                    required
                    min={2000}
                    max={2100}
                    value={annee}
                    onChange={(e) => setAnnee(Number(e.target.value))}
                    className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>
            )}

            {error && <p className="text-sm text-destructive text-center">{error}</p>}

            <div className="pt-2 flex gap-3">
              <button type="button" onClick={onClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">
                Annuler
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>{modeEdition ? 'Enregistrer' : 'Définir budget'}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
