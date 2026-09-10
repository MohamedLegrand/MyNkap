import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CreditCard, Loader2, AlertTriangle, CheckCircle2, X } from 'lucide-react';
import { api } from '../services/api';
import type { RechargeCompte, PaiementAbonnement } from '../types';

interface PaiementCarteRetourModalProps {
  isOpen: boolean;
  // 'recharge' -> GET /recharges/:id ; 'abonnement' -> GET /abonnement/paiements/:id
  type: 'recharge' | 'abonnement';
  idPaiement: number | null;
  // Le client est revenu par cancel_url (a abandonné sur la page Flocash).
  annule: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

type Etape = 'attente' | 'succes' | 'echec' | 'annule';

/**
 * Écran de retour d'un paiement par carte bancaire. Après avoir réglé sur la
 * page hébergée Flocash, le client est redirigé vers
 * /dashboard?carte=...&ref=... : le rebond navigateur n'est jamais la source
 * de vérité, on interroge donc le backend (qui revérifie auprès d'E-NKAP)
 * jusqu'à un statut définitif — même logique de polling que les modales
 * Mobile Money.
 */
export const PaiementCarteRetourModal: React.FC<PaiementCarteRetourModalProps> = ({
  isOpen, type, idPaiement, annule, onClose, onSuccess,
}) => {
  const { t } = useTranslation();
  const [etape, setEtape] = useState<Etape>('attente');
  const [montant, setMontant] = useState<number | null>(null);
  const [devise, setDevise] = useState('XAF');
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const arreterPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  useEffect(() => {
    if (!isOpen || idPaiement === null) return;

    // Retour par cancel_url : le client a explicitement abandonné sur la
    // page Flocash. Inutile de sonder le statut (encore PENDING côté
    // backend jusqu'à ce qu'E-NKAP rapporte CANCELED — la tâche planifiée
    // s'en charge). On affiche directement l'écran d'annulation.
    if (annule) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEtape('annule');
      return;
    }

    const endpoint = type === 'abonnement'
      ? `/abonnement/paiements/${idPaiement}`
      : `/recharges/${idPaiement}`;

    setEtape('attente');
    setMontant(null);

    const lire = async () => {
      try {
        const p = await api.request<RechargeCompte | PaiementAbonnement>(endpoint);
        setMontant(p.montant);
        setDevise(p.devise);
        if (p.statut === 'SUCCESS') {
          arreterPolling();
          setEtape('succes');
          onSuccess?.();
        } else if (p.statut === 'FAILED') {
          arreterPolling();
          setEtape('echec');
        }
      } catch {
        // Erreur réseau ponctuelle : on retentera au prochain tick.
      }
    };

    lire();
    pollingRef.current = setInterval(lire, 3000);
    return () => arreterPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, idPaiement, type, annule]);

  if (!isOpen || idPaiement === null) return null;

  const titre = type === 'abonnement'
    ? t('modals.card_return.title_subscription')
    : t('modals.card_return.title_recharge');

  const montantFmt = montant !== null ? `${montant.toLocaleString('fr-FR')} ${devise}` : '';

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight flex items-center gap-2">
            <CreditCard className="h-5 w-5 text-primary" />
            <span>{titre}</span>
          </h3>
          <button
            onClick={() => { arreterPolling(); onClose(); }}
            className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6">
          {etape === 'attente' && (
            <div className="text-center space-y-3 py-6">
              <Loader2 className="h-10 w-10 mx-auto animate-spin text-primary" />
              <p className="text-sm font-bold text-foreground">{t('modals.card_return.checking_title')}</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                {t('modals.card_return.checking_desc')}
              </p>
            </div>
          )}

          {etape === 'succes' && (
            <div className="text-center space-y-3 py-6">
              <CheckCircle2 className="h-10 w-10 mx-auto text-forest-500" />
              <p className="text-sm font-bold text-foreground">{t('modals.card_return.success_title')}</p>
              <p className="text-xs text-muted-foreground">
                {type === 'abonnement'
                  ? t('modals.card_return.success_subscription', { montant: montantFmt })
                  : t('modals.card_return.success_recharge', { montant: montantFmt })}
              </p>
              <button
                type="button"
                onClick={() => { arreterPolling(); onClose(); }}
                className="mt-2 py-2.5 px-6 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95"
              >
                {t('modals.plan_upgrade.finish')}
              </button>
            </div>
          )}

          {(etape === 'echec' || etape === 'annule') && (
            <div className="text-center space-y-3 py-6">
              <AlertTriangle className="h-10 w-10 mx-auto text-destructive" />
              <p className="text-sm font-bold text-foreground">
                {etape === 'annule' ? t('modals.card_return.canceled_title') : t('modals.card_return.failed_title')}
              </p>
              <p className="text-xs text-muted-foreground">{t('modals.plan_upgrade.no_amount_charged')}</p>
              <button
                type="button"
                onClick={() => { arreterPolling(); onClose(); }}
                className="mt-2 py-2.5 px-6 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95"
              >
                {t('common.close')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
