import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Loader2, AlertTriangle, ShieldCheck, ShieldAlert, Ban } from 'lucide-react';
import { api } from '../services/api';
import type { Transaction } from '../types';

interface TransactionDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  onChange: () => void;
  idTransaction: number | null;
  nomCategorie: (idCategorie: number | null) => string;
  nomCompte: (idCompte: number) => string;
  peutAnnuler: boolean;
  onAnnuler: (idTransaction: number) => void;
}

export const TransactionDetailModal: React.FC<TransactionDetailModalProps> = ({
  isOpen, onClose, onChange, idTransaction, nomCategorie, nomCompte, peutAnnuler, onAnnuler,
}) => {
  const { t } = useTranslation();
  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Chargement à l'ouverture — pas une synchronisation d'état dérivé d'un
    // rendu précédent.
    if (isOpen && idTransaction !== null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsLoading(true);
      setError(null);
      api
        .request<Transaction>(`/transactions/${idTransaction}`)
        .then(setTransaction)
        .catch((err) => setError(err instanceof Error ? err.message : t('modals.transaction_detail.error_load')))
        .finally(() => setIsLoading(false));
    } else {
      setTransaction(null);
    }
  }, [isOpen, idTransaction, t]);

  if (!isOpen || idTransaction === null) return null;

  const gererSuspicion = async (action: 'confirmer-suspicion' | 'annuler-suspicion') => {
    setError(null);
    setIsSubmitting(true);
    try {
      const maj = await api.request<Transaction>(`/transactions/${idTransaction}/${action}`, { method: 'POST' });
      setTransaction(maj);
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('common.error_action'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">{t('modals.transaction_detail.title')}</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-14">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : !transaction ? (
          <p className="p-6 text-sm text-destructive text-center">{error ?? t('modals.transaction_detail.not_found')}</p>
        ) : (
          <div className="p-6 space-y-4">
            {transaction.est_suspecte && (
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-2.5">
                <ShieldAlert className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <p className="text-xs text-amber-700 dark:text-amber-400 leading-relaxed">
                  {t('modals.transaction_detail.suspicious_notice')}
                </p>
              </div>
            )}

            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">{t('transfers.amount')}</span><strong className="text-foreground">{Number(transaction.montant).toLocaleString('fr-FR')} XAF</strong></div>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('modals.transaction_detail.type')}</span><span className="text-foreground font-semibold">{transaction.type}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('modals.transaction_detail.account')}</span><span className="text-foreground font-semibold">{nomCompte(transaction.id_compte)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('modals.transaction_detail.category')}</span><span className="text-foreground font-semibold">{nomCategorie(transaction.id_categorie)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('common.date')}</span><span className="text-foreground font-semibold">{new Date(transaction.date).toLocaleDateString('fr-FR')}</span></div>
              {transaction.description && (
                <div className="flex justify-between gap-3"><span className="text-muted-foreground shrink-0">{t('common.description')}</span><span className="text-foreground font-semibold text-right">{transaction.description}</span></div>
              )}
              <div className="flex justify-between"><span className="text-muted-foreground">{t('modals.transaction_detail.recorded_on')}</span><span className="text-foreground font-semibold">{new Date(transaction.date_creation).toLocaleString('fr-FR')}</span></div>
            </div>

            {error && <p className="text-sm text-destructive text-center">{error}</p>}

            <div className="flex flex-col gap-2 pt-2">
              {transaction.est_suspecte && (
                <div className="flex gap-2">
                  <button
                    onClick={() => gererSuspicion('confirmer-suspicion')}
                    disabled={isSubmitting}
                    className="flex-1 py-2.5 rounded-lg bg-destructive/10 hover:bg-destructive/20 text-destructive text-xs font-bold transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                  >
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>{t('modals.transaction_detail.confirm_error')}</span>
                  </button>
                  <button
                    onClick={() => gererSuspicion('annuler-suspicion')}
                    disabled={isSubmitting}
                    className="flex-1 py-2.5 rounded-lg bg-forest-500/10 hover:bg-forest-500/20 text-forest-600 dark:text-forest-400 text-xs font-bold transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                  >
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <span>{t('modals.transaction_detail.legitimate')}</span>
                  </button>
                </div>
              )}
              {peutAnnuler && (
                <button
                  onClick={() => { onAnnuler(idTransaction); onClose(); }}
                  className="py-2.5 rounded-lg bg-muted hover:bg-accent text-foreground text-xs font-bold transition-colors flex items-center justify-center gap-1.5"
                >
                  <Ban className="h-3.5 w-3.5" />
                  <span>{t('transactions.cancel_this')}</span>
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
