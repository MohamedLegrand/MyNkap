import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
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

const MOIS_KEYS = [
  'common.month_1', 'common.month_2', 'common.month_3', 'common.month_4', 'common.month_5', 'common.month_6',
  'common.month_7', 'common.month_8', 'common.month_9', 'common.month_10', 'common.month_11', 'common.month_12',
];

export const BudgetModal: React.FC<BudgetModalProps> = ({
  isOpen, onClose, onSuccess, categoriesDepense, budget = null, nomCategorie,
}) => {
  const { t } = useTranslation();
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
        .catch((err) => setError(err instanceof Error ? err.message : t('modals.budget.error_load')))
        .finally(() => setIsLoadingDetail(false));
    } else if (isOpen) {
      setMontantLimite('');
    }
  }, [isOpen, budget, t]);

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
      setError(err instanceof Error ? err.message : (modeEdition ? t('modals.budget.error_edit') : t('modals.budget.error_create')));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">{modeEdition ? t('modals.budget.title_edit') : t('modals.budget.title_create')}</h3>
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
              {t('modals.budget.no_category_yet')}
            </p>
            <button onClick={onClose} className="text-sm font-bold text-primary hover:underline">
              {t('common.close')}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {modeEdition ? (
              <p className="text-xs text-muted-foreground">
                <strong className="text-foreground">{nomCategorie ? nomCategorie(Number(idCategorie)) : t('modals.budget.category_fallback', { id: idCategorie })}</strong>
                {' '}— {t(MOIS_KEYS[mois - 1])} {annee}
              </p>
            ) : (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">{t('modals.budget.category_label')}</label>
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
              <label className="text-xs font-semibold text-muted-foreground">{t('modals.budget.limit_label')}</label>
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
                  <label className="text-xs font-semibold text-muted-foreground">{t('modals.budget.month_label')}</label>
                  <select
                    value={mois}
                    onChange={(e) => setMois(Number(e.target.value))}
                    className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    {MOIS_KEYS.map((key, idx) => (
                      <option key={key} value={idx + 1}>{t(key)}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">{t('modals.budget.year_label')}</label>
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
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>{modeEdition ? t('common.save') : t('modals.budget.title_create')}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
