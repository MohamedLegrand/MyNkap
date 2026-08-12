import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { CompteFinancier, Dette } from '../types';

interface DetteOperationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  dette: Dette | null;
  comptes: CompteFinancier[];
}

// Rembourser une dette ou encaisser une créance : même formulaire, seul
// l'endpoint et le libellé changent selon dette.type.
export const DetteOperationModal: React.FC<DetteOperationModalProps> = ({ isOpen, onClose, onSuccess, dette, comptes }) => {
  const { t } = useTranslation();
  const [montant, setMontant] = useState('');
  const [idCompte, setIdCompte] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detteFraiche, setDetteFraiche] = useState<Dette | null>(null);

  useEffect(() => {
    if (isOpen && comptes.length > 0 && !idCompte) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIdCompte(String(comptes[0].id_compte));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, comptes]);

  useEffect(() => {
    // Relit le montant restant depuis le serveur à l'ouverture plutôt que de
    // se fier à la liste locale (potentiellement périmée depuis un autre
    // onglet/appareil) — pas une synchronisation d'état dérivé.
    if (isOpen && dette) {
      api.request<Dette>(`/dettes/${dette.id_dette}`).then(setDetteFraiche).catch(() => {});
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDetteFraiche(null);
    }
  }, [isOpen, dette]);

  if (!isOpen || !dette) return null;

  const detteAffichee = detteFraiche ?? dette;
  const estDette = detteAffichee.type === 'DETTE';
  const endpoint = estDette ? `/dettes/${detteAffichee.id_dette}/rembourser` : `/dettes/${detteAffichee.id_dette}/encaisser`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idCompte) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await api.request(endpoint, {
        method: 'POST',
        body: JSON.stringify({ montant: Number(montant), id_compte: Number(idCompte) }),
      });
      setMontant('');
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.dette_operation.error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-sm rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">{estDette ? t('debts.repay') : t('debts.collect')} — {detteAffichee.nom}</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <p className="text-xs text-muted-foreground">
            {estDette ? t('modals.dette_operation.remaining_to_repay') : t('modals.dette_operation.remaining_to_collect')} : <strong className="text-foreground">{Number(detteAffichee.montant_restant).toLocaleString('fr-FR')} XAF</strong>
          </p>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.dette_operation.amount_label')}</label>
            <input
              type="number"
              required
              min={1}
              max={detteAffichee.montant_restant}
              placeholder="ex: 10000"
              value={montant}
              onChange={(e) => setMontant(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">
              {estDette ? t('modals.dette_operation.account_debit') : t('modals.dette_operation.account_credit')}
            </label>
            <select
              value={idCompte}
              onChange={(e) => setIdCompte(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {comptes.map((c) => (
                <option key={c.id_compte} value={c.id_compte}>{c.nom}</option>
              ))}
            </select>
          </div>

          {error && <p className="text-sm text-destructive text-center">{error}</p>}

          <div className="pt-2 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !idCompte}
              className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>{t('common.confirm')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
