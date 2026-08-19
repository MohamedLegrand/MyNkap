import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Crown, Check, Loader2, Smartphone, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store';
import type { Plan, PaiementAbonnement, Abonnement, PaysOperateur } from '../types';

interface PlanUpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  planActuel?: string;
  abonnement?: Abonnement | null;
}

const LABEL_PLAN_KEY: Record<string, string> = {
  ESSENTIEL: 'modals.plan_upgrade.plan_essentiel',
  PREMIUM: 'modals.plan_upgrade.plan_premium',
};

const FEATURES_PAR_PLAN_KEYS: Record<string, string[]> = {
  ESSENTIEL: [
    'modals.plan_upgrade.feature_essentiel_1',
    'modals.plan_upgrade.feature_essentiel_2',
    'modals.plan_upgrade.feature_essentiel_3',
  ],
  PREMIUM: [
    'modals.plan_upgrade.feature_premium_1',
    'modals.plan_upgrade.feature_premium_2',
    'modals.plan_upgrade.feature_premium_3',
    'modals.plan_upgrade.feature_premium_4',
  ],
};

type Etape = 'choix' | 'paiement' | 'attente' | 'succes' | 'echec';

// Libellés d'affichage des opérateurs Mobile Money couverts par HR-Skills
// Pay (codes bruts renvoyés par GET /abonnement/pays-disponibles).
const OPERATEUR_LABELS: Record<string, string> = {
  ORANGE: 'Orange Money',
  MTN: 'MTN MoMo',
  MOOV: 'Moov Money',
  AIRTEL: 'Airtel Money',
  MPESA: 'M-Pesa',
  WAVE: 'Wave',
  FREE: 'Free Money',
  TMONEY: 'TMoney',
  AFRIMONEY: 'AfriMoney',
  CAMTEL: 'Camtel Money',
  NEXTTEL: 'Nexttel',
  CORIS: 'Coris Money',
  EXPRESSO: 'Expresso',
  FLOOZ: 'Flooz',
  QMONEY: 'QMoney',
};

export const PlanUpgradeModal: React.FC<PlanUpgradeModalProps> = ({ isOpen, onClose, onSuccess, planActuel, abonnement }) => {
  const { t } = useTranslation();
  const client = useAuthStore((state) => state.client);

  const [etape, setEtape] = useState<Etape>('choix');
  const [plans, setPlans] = useState<Plan[]>([]);
  const [isLoadingPlans, setIsLoadingPlans] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [planChoisi, setPlanChoisi] = useState<'ESSENTIEL' | 'PREMIUM'>('PREMIUM');
  const [cycle, setCycle] = useState<'MENSUEL' | 'ANNUEL'>('MENSUEL');
  const [phone, setPhone] = useState('');
  const [paysDisponibles, setPaysDisponibles] = useState<PaysOperateur[]>([]);
  const [pays, setPays] = useState('CM');
  const [operator, setOperator] = useState('ORANGE');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [paiement, setPaiement] = useState<PaiementAbonnement | null>(null);
  const [isSubmittingGestion, setIsSubmittingGestion] = useState(false);
  const [gestionMessage, setGestionMessage] = useState<string | null>(null);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const arreterPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    // Réinitialise l'état du formulaire à chaque ouverture de la modale
    // (pas une synchronisation d'état dérivé d'un rendu précédent).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEtape('choix');
    setError(null);
    setPaiement(null);
    setGestionMessage(null);
    setPhone(client?.phone ?? '');
    setPays('CM');
    setOperator('ORANGE');
    setIsLoadingPlans(true);
    api
      .request<Plan[]>('/plans')
      .then((data) => setPlans(data.filter((p) => p.nom !== 'GRATUIT')))
      .catch((err) => setError(err instanceof Error ? err.message : t('modals.plan_upgrade.error_load_plans')))
      .finally(() => setIsLoadingPlans(false));
    api
      .request<PaysOperateur[]>('/abonnement/pays-disponibles')
      .then(setPaysDisponibles)
      .catch(() => {
        // Pays non chargés : le pays par défaut (CM) et son opérateur
        // (ORANGE) restent utilisables tels quels, juste sans sélecteur
        // dynamique — mieux que de bloquer tout le formulaire de paiement.
      });

    return () => arreterPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  if (!isOpen) return null;

  const planSelectionne = plans.find((p) => p.nom === planChoisi);
  // Prix de référence XAF (catalogue public) — affiché à l'étape "choix",
  // avant que le pays de paiement ne soit choisi.
  const montant = planSelectionne
    ? (cycle === 'MENSUEL' ? planSelectionne.prix_mensuel : planSelectionne.prix_annuel)
    : 0;

  const paysActuel = paysDisponibles.find((p) => p.pays === pays);
  const operateursDuPays = paysActuel?.operateurs ?? ['ORANGE', 'MTN'];
  const deviseLocale = paysActuel?.devise ?? 'XAF';
  // Montant réellement facturé dans la devise du pays choisi (étape
  // "paiement"/"attente") — repli sur le prix de référence si le pays n'a
  // pas encore chargé.
  const prixLocal = planSelectionne?.prix_devises.find((pd) => pd.devise === deviseLocale);
  const montantLocal = prixLocal
    ? (cycle === 'MENSUEL' ? prixLocal.prix_mensuel : prixLocal.prix_annuel)
    : montant;

  const handleContinuer = () => {
    setError(null);
    setEtape('paiement');
  };

  const handleChangerPays = (nouveauPays: string) => {
    setPays(nouveauPays);
    const operateurs = paysDisponibles.find((p) => p.pays === nouveauPays)?.operateurs;
    if (operateurs && operateurs.length > 0) {
      setOperator(operateurs[0]);
    }
  };

  const demarrerPolling = (idPaiement: number) => {
    pollingRef.current = setInterval(async () => {
      try {
        const resultat = await api.request<PaiementAbonnement>(`/abonnement/paiements/${idPaiement}`);
        setPaiement(resultat);
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

  const handleInitierPaiement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim()) return;

    setError(null);
    setIsSubmitting(true);
    try {
      const resultat = await api.request<PaiementAbonnement>('/abonnement/paiements', {
        method: 'POST',
        body: JSON.stringify({
          nom_plan: planChoisi,
          cycle_facturation: cycle,
          phone_number: phone.trim(),
          operator,
          pays,
        }),
      });
      setPaiement(resultat);
      setEtape('attente');
      demarrerPolling(resultat.id_paiement);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.plan_upgrade.error_start_payment'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    arreterPolling();
    onClose();
  };

  const handleRevenirGratuit = async () => {
    if (!window.confirm(t('modals.plan_upgrade.confirm_downgrade'))) return;
    setIsSubmittingGestion(true);
    setError(null);
    try {
      await api.request('/abonnement/changer-plan', { method: 'POST', body: JSON.stringify({ nom_plan: 'GRATUIT' }) });
      onSuccess?.();
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.plan_upgrade.error_change_plan'));
    } finally {
      setIsSubmittingGestion(false);
    }
  };

  const handleAnnulerRenouvellement = async () => {
    setIsSubmittingGestion(true);
    setError(null);
    setGestionMessage(null);
    try {
      await api.request('/abonnement/annuler-renouvellement', { method: 'POST' });
      setGestionMessage(t('modals.plan_upgrade.renewal_cancelled'));
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('common.error_action'));
    } finally {
      setIsSubmittingGestion(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight flex items-center gap-2">
            <Crown className="h-5 w-5 text-primary" />
            <span>{t('modals.plan_upgrade.title')}</span>
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

          {etape === 'choix' && (
            isLoadingPlans ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                {/* Sélecteur de plan */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {plans.map((p) => (
                    <button
                      key={p.nom}
                      type="button"
                      onClick={() => setPlanChoisi(p.nom as 'ESSENTIEL' | 'PREMIUM')}
                      disabled={planActuel === p.nom}
                      className={`text-left p-4 rounded-2xl border-2 transition-all space-y-2 ${
                        planChoisi === p.nom
                          ? 'border-primary bg-primary/5 shadow-md'
                          : 'border-border hover:border-primary/40'
                      } ${planActuel === p.nom ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-black text-foreground">{LABEL_PLAN_KEY[p.nom] ? t(LABEL_PLAN_KEY[p.nom]) : p.nom}</span>
                        {planActuel === p.nom && (
                          <span className="text-[10px] font-bold uppercase text-muted-foreground">{t('modals.plan_upgrade.current')}</span>
                        )}
                      </div>
                      <p className="text-xl font-black text-primary tabular-nums">
                        {p.prix_mensuel.toLocaleString('fr-FR')} <span className="text-xs text-muted-foreground font-semibold">XAF/{t('modals.plan_upgrade.month_short')}</span>
                      </p>
                      <ul className="space-y-1">
                        {(FEATURES_PAR_PLAN_KEYS[p.nom] ?? []).map((fKey) => (
                          <li key={fKey} className="flex items-start gap-1.5 text-[11px] text-muted-foreground">
                            <Check className="h-3 w-3 text-forest-500 mt-0.5 shrink-0" />
                            <span>{t(fKey)}</span>
                          </li>
                        ))}
                      </ul>
                    </button>
                  ))}
                </div>

                {/* Cycle de facturation */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">{t('modals.plan_upgrade.billing_cycle')}</label>
                  <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
                    <button
                      type="button"
                      onClick={() => setCycle('MENSUEL')}
                      className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                        cycle === 'MENSUEL' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {t('modals.plan_upgrade.monthly')}
                    </button>
                    <button
                      type="button"
                      onClick={() => setCycle('ANNUEL')}
                      className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                        cycle === 'ANNUEL' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {t('modals.plan_upgrade.yearly')}
                    </button>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleContinuer}
                  disabled={planActuel === planChoisi}
                  className="w-full py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 transition-all disabled:opacity-50"
                >
                  {t('modals.plan_upgrade.continue', { montant: montant.toLocaleString('fr-FR'), periode: cycle === 'MENSUEL' ? t('modals.plan_upgrade.month_short') : t('modals.plan_upgrade.year_short') })}
                </button>

                {planActuel && planActuel !== 'GRATUIT' && (
                  <div className="pt-4 mt-1 border-t border-border space-y-2">
                    <p className="text-xs font-semibold text-muted-foreground">{t('modals.plan_upgrade.manage_subscription')}</p>
                    <div className="flex flex-col sm:flex-row gap-2">
                      {abonnement?.renouvellement_auto && abonnement.statut === 'ACTIF' && (
                        <button
                          type="button"
                          onClick={handleAnnulerRenouvellement}
                          disabled={isSubmittingGestion}
                          className="flex-1 py-2.5 px-3 rounded-xl border border-border text-xs font-bold text-foreground hover:bg-muted transition-colors disabled:opacity-50"
                        >
                          {t('modals.plan_upgrade.dont_renew')}{abonnement.date_fin && ` (${t('modals.plan_upgrade.access_until', { date: new Date(abonnement.date_fin).toLocaleDateString('fr-FR') })})`}
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={handleRevenirGratuit}
                        disabled={isSubmittingGestion}
                        className="flex-1 py-2.5 px-3 rounded-xl border border-destructive/30 text-xs font-bold text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
                      >
                        {t('modals.plan_upgrade.back_to_free')}
                      </button>
                    </div>
                    {gestionMessage && <p className="text-xs text-forest-600 dark:text-forest-400 text-center">{gestionMessage}</p>}
                  </div>
                )}
              </>
            )
          )}

          {etape === 'paiement' && (
            <form onSubmit={handleInitierPaiement} className="space-y-4">
              <div className="p-3 rounded-xl bg-muted/40 border border-border text-xs text-muted-foreground">
                {t('modals.plan_upgrade.plan_label')} <strong className="text-foreground">{LABEL_PLAN_KEY[planChoisi] ? t(LABEL_PLAN_KEY[planChoisi]) : planChoisi}</strong> —{' '}
                <strong className="text-foreground">{montantLocal.toLocaleString('fr-FR')} {deviseLocale}</strong> / {cycle === 'MENSUEL' ? t('modals.plan_upgrade.month_short') : t('modals.plan_upgrade.year_short')}
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
                <button
                  type="button"
                  onClick={() => setEtape('choix')}
                  className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted"
                >
                  {t('modals.plan_upgrade.back')}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  <span>{t('modals.plan_upgrade.pay_now')}</span>
                </button>
              </div>
            </form>
          )}

          {etape === 'attente' && (
            <div className="text-center space-y-3 py-6">
              <Loader2 className="h-10 w-10 mx-auto animate-spin text-primary" />
              <p className="text-sm font-bold text-foreground">{t('modals.plan_upgrade.waiting_title')}</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                {t('modals.plan_upgrade.waiting_desc', {
                  montant: (paiement?.montant ?? montantLocal).toLocaleString('fr-FR'),
                  devise: paiement?.devise ?? deviseLocale,
                  phone,
                  operateur: OPERATEUR_LABELS[operator] ?? operator,
                })}
              </p>
              {paiement && (
                <p className="text-[11px] text-muted-foreground">{t('modals.plan_upgrade.reference')} : {paiement.reference_hrpay}</p>
              )}
            </div>
          )}

          {etape === 'succes' && (
            <div className="text-center space-y-3 py-6">
              <CheckCircle2 className="h-10 w-10 mx-auto text-forest-500" />
              <p className="text-sm font-bold text-foreground">{t('modals.plan_upgrade.payment_confirmed')}</p>
              <p className="text-xs text-muted-foreground">
                {t('modals.plan_upgrade.plan_now_active', { plan: LABEL_PLAN_KEY[planChoisi] ? t(LABEL_PLAN_KEY[planChoisi]) : planChoisi })}
              </p>
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
              <p className="text-sm font-bold text-foreground">{t('modals.plan_upgrade.payment_rejected')}</p>
              <p className="text-xs text-muted-foreground">{t('modals.plan_upgrade.no_amount_charged')}</p>
              <button
                type="button"
                onClick={() => setEtape('paiement')}
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
