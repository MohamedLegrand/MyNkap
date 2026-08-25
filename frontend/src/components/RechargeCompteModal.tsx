import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Wallet, Loader2, Smartphone, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store';
import type { CompteFinancier, PaysOperateur, RechargeCompte } from '../types';

interface RechargeCompteModalProps {
  isOpen: boolean;
  compte: CompteFinancier | null;
  onClose: () => void;
  onSuccess?: () => void;
}

type Etape = 'formulaire' | 'attente' | 'succes' | 'echec';

// Même table que PlanUpgradeModal — même catalogue HR-Skills Pay, un autre
// point d'entrée (recharger un compte plutôt que payer un abonnement).
const OPERATEUR_LABELS: Record<string, string> = {
  ORANGE: 'Orange Money', MTN: 'MTN MoMo', MOOV: 'Moov Money', AIRTEL: 'Airtel Money',
  MPESA: 'M-Pesa', WAVE: 'Wave', FREE: 'Free Money', TMONEY: 'TMoney', AFRIMONEY: 'AfriMoney',
  CAMTEL: 'Camtel Money', NEXTTEL: 'Nexttel', CORIS: 'Coris Money', EXPRESSO: 'Expresso',
  FLOOZ: 'Flooz', QMONEY: 'QMoney',
};

export const RechargeCompteModal: React.FC<RechargeCompteModalProps> = ({ isOpen, compte, onClose, onSuccess }) => {
  const { t } = useTranslation();
  const client = useAuthStore((state) => state.client);

  const [etape, setEtape] = useState<Etape>('formulaire');
  const [error, setError] = useState<string | null>(null);

  const [montant, setMontant] = useState('');
  const [phone, setPhone] = useState('');
  const [paysDisponibles, setPaysDisponibles] = useState<PaysOperateur[]>([]);
  const [pays, setPays] = useState('CM');
  const [operator, setOperator] = useState('ORANGE');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [recharge, setRecharge] = useState<RechargeCompte | null>(null);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const arreterPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    // Réinitialise le formulaire à chaque ouverture — pas une
    // synchronisation d'état dérivé d'un rendu précédent.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEtape('formulaire');
    setError(null);
    setMontant('');
    setRecharge(null);
    setPhone(client?.phone ?? '');
    setPays('CM');
    setOperator('ORANGE');
    api.request<PaysOperateur[]>('/abonnement/pays-disponibles').then(setPaysDisponibles).catch(() => {});

    return () => arreterPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  if (!isOpen || !compte) return null;

  const paysActuel = paysDisponibles.find((p) => p.pays === pays);
  const operateursDuPays = paysActuel?.operateurs ?? ['ORANGE', 'MTN'];
  const deviseLocale = paysActuel?.devise ?? 'XAF';

  const handleChangerPays = (nouveauPays: string) => {
    setPays(nouveauPays);
    const operateurs = paysDisponibles.find((p) => p.pays === nouveauPays)?.operateurs;
    if (operateurs && operateurs.length > 0) setOperator(operateurs[0]);
  };

  const demarrerPolling = (idRecharge: number) => {
    pollingRef.current = setInterval(async () => {
      try {
        const resultat = await api.request<RechargeCompte>(`/recharges/${idRecharge}`);
        setRecharge(resultat);
        if (resultat.statut === 'SUCCESS') {
          arreterPolling();
          setEtape('succes');
          onSuccess?.();
        } else if (resultat.statut === 'FAILED') {
          arreterPolling();
          setEtape('echec');
        }
      } catch {
        // Erreur réseau ponctuelle : on retentera au prochain tick.
      }
    }, 3000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const montantNombre = Number(montant);
    if (!montantNombre || montantNombre <= 0 || !phone.trim()) return;

    setError(null);
    setIsSubmitting(true);
    try {
      const resultat = await api.request<RechargeCompte>('/recharges', {
        method: 'POST',
        body: JSON.stringify({
          id_compte: compte.id_compte, montant: montantNombre,
          phone_number: phone.trim(), operator, pays,
        }),
      });
      setRecharge(resultat);
      setEtape('attente');
      demarrerPolling(resultat.id_recharge);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.recharge.error_start'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    arreterPolling();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight flex items-center gap-2">
            <Wallet className="h-5 w-5 text-primary" />
            <span>{t('modals.recharge.title')}</span>
          </h3>
          <button onClick={handleClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {error && (
            <p className="text-sm text-destructive text-center flex items-center justify-center gap-1.5">
              <AlertTriangle className="h-4 w-4" />
              <span>{error}</span>
            </p>
          )}

          {etape === 'formulaire' && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="p-3 rounded-xl bg-muted/40 border border-border text-xs text-muted-foreground space-y-1.5">
                <p>
                  {t('modals.recharge.target_account')} <strong className="text-foreground">{compte.nom}</strong> —{' '}
                  {t('modals.recharge.current_balance')} <strong className="text-foreground">{compte.solde.toLocaleString('fr-FR')} {compte.devise}</strong>
                </p>
                {compte.type === 'ABONNEMENT' && <p className="leading-snug">{t('accounts.abonnement_description')}</p>}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">{t('modals.recharge.amount_label')}</label>
                <input
                  type="number"
                  required
                  min={1}
                  value={montant}
                  onChange={(e) => setMontant(e.target.value)}
                  placeholder="10000"
                  className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">{t('modals.plan_upgrade.country_label')}</label>
                <select
                  value={pays}
                  onChange={(e) => handleChangerPays(e.target.value)}
                  className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  {(paysDisponibles.length > 0 ? paysDisponibles : [{ pays: 'CM', nom: 'Cameroun', devise: 'XAF', operateurs: [] }]).map((p) => (
                    <option key={p.pays} value={p.pays}>{p.nom}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">{t('modals.plan_upgrade.operator_label')}</label>
                <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
                  {operateursDuPays.map((op) => (
                    <button
                      key={op}
                      type="button"
                      onClick={() => setOperator(op)}
                      className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                        operator === op ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {OPERATEUR_LABELS[op] ?? op}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                  <Smartphone className="h-3.5 w-3.5" />
                  <span>{t('modals.plan_upgrade.phone_label')}</span>
                </label>
                <input
                  type="tel"
                  required
                  placeholder="ex: 237655500393"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="pt-2 flex gap-3">
                <button type="button" onClick={handleClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  <span>{t('modals.recharge.submit')}</span>
                </button>
              </div>
            </form>
          )}

          {etape === 'attente' && (
            <div className="text-center space-y-3 py-6">
              <Loader2 className="h-10 w-10 mx-auto animate-spin text-primary" />
              <p className="text-sm font-bold text-foreground">{t('modals.recharge.waiting_title')}</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                {t('modals.recharge.waiting_desc', {
                  montant: (recharge?.montant ?? Number(montant)).toLocaleString('fr-FR'),
                  devise: recharge?.devise ?? deviseLocale,
                  phone,
                  operateur: OPERATEUR_LABELS[operator] ?? operator,
                })}
              </p>
              {recharge && (
                <p className="text-[11px] text-muted-foreground">{t('modals.plan_upgrade.reference')} : {recharge.reference_hrpay}</p>
              )}
            </div>
          )}

          {etape === 'succes' && (
            <div className="text-center space-y-3 py-6">
              <CheckCircle2 className="h-10 w-10 mx-auto text-forest-500" />
              <p className="text-sm font-bold text-foreground">{t('modals.recharge.confirmed')}</p>
              <p className="text-xs text-muted-foreground">{t('modals.recharge.confirmed_desc', { compte: compte.nom })}</p>
              <button
                type="button"
                onClick={handleClose}
                className="mt-2 py-2.5 px-6 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95"
              >
                {t('modals.plan_upgrade.finish')}
              </button>
            </div>
          )}

          {etape === 'echec' && (
            <div className="text-center space-y-3 py-6">
              <AlertTriangle className="h-10 w-10 mx-auto text-destructive" />
              <p className="text-sm font-bold text-foreground">{t('modals.recharge.rejected')}</p>
              <p className="text-xs text-muted-foreground">{t('modals.plan_upgrade.no_amount_charged')}</p>
              <button
                type="button"
                onClick={() => setEtape('formulaire')}
                className="mt-2 py-2.5 px-6 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95"
              >
                {t('modals.plan_upgrade.retry')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
