import React, { useEffect, useRef, useState } from 'react';
import { X, Crown, Check, Loader2, Smartphone, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store';
import type { Plan, PaiementAbonnement } from '../types';

interface PlanUpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  planActuel?: string;
}

const LABEL_PLAN: Record<string, string> = {
  ESSENTIEL: 'Standard',
  PREMIUM: 'Premium',
};

const FEATURES_PAR_PLAN: Record<string, string[]> = {
  ESSENTIEL: ['Suivi des dettes & créances', 'Objectifs d\'épargne', 'Transactions récurrentes'],
  PREMIUM: [
    'Toutes les fonctionnalités Standard',
    'Assistant financier JARVIS IA',
    'Analyse avancée des dépenses',
    'Modèles de transactions',
  ],
};

type Etape = 'choix' | 'paiement' | 'attente' | 'succes' | 'echec';

export const PlanUpgradeModal: React.FC<PlanUpgradeModalProps> = ({ isOpen, onClose, onSuccess, planActuel }) => {
  const client = useAuthStore((state) => state.client);

  const [etape, setEtape] = useState<Etape>('choix');
  const [plans, setPlans] = useState<Plan[]>([]);
  const [isLoadingPlans, setIsLoadingPlans] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [planChoisi, setPlanChoisi] = useState<'ESSENTIEL' | 'PREMIUM'>('PREMIUM');
  const [cycle, setCycle] = useState<'MENSUEL' | 'ANNUEL'>('MENSUEL');
  const [phone, setPhone] = useState('');
  const [operator, setOperator] = useState<'orange' | 'mtn'>('orange');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [paiement, setPaiement] = useState<PaiementAbonnement | null>(null);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const arreterPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    setEtape('choix');
    setError(null);
    setPaiement(null);
    setPhone(client?.phone ?? '');
    setIsLoadingPlans(true);
    api
      .request<Plan[]>('/plans')
      .then((data) => setPlans(data.filter((p) => p.nom !== 'GRATUIT')))
      .catch((err) => setError(err instanceof Error ? err.message : 'Impossible de charger les plans.'))
      .finally(() => setIsLoadingPlans(false));

    return () => arreterPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  if (!isOpen) return null;

  const planSelectionne = plans.find((p) => p.nom === planChoisi);
  const montant = planSelectionne
    ? (cycle === 'MENSUEL' ? planSelectionne.prix_mensuel : planSelectionne.prix_annuel)
    : 0;

  const handleContinuer = () => {
    setError(null);
    setEtape('paiement');
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
        }),
      });
      setPaiement(resultat);
      setEtape('attente');
      demarrerPolling(resultat.id_paiement);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de démarrer le paiement.');
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
            <Crown className="h-5 w-5 text-primary" />
            <span>Changer de formule</span>
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
                        <span className="text-sm font-black text-foreground">{LABEL_PLAN[p.nom] ?? p.nom}</span>
                        {planActuel === p.nom && (
                          <span className="text-[10px] font-bold uppercase text-muted-foreground">Actuel</span>
                        )}
                      </div>
                      <p className="text-xl font-black text-primary tabular-nums">
                        {p.prix_mensuel.toLocaleString('fr-FR')} <span className="text-xs text-muted-foreground font-semibold">XAF/mois</span>
                      </p>
                      <ul className="space-y-1">
                        {(FEATURES_PAR_PLAN[p.nom] ?? []).map((f) => (
                          <li key={f} className="flex items-start gap-1.5 text-[11px] text-muted-foreground">
                            <Check className="h-3 w-3 text-forest-500 mt-0.5 shrink-0" />
                            <span>{f}</span>
                          </li>
                        ))}
                      </ul>
                    </button>
                  ))}
                </div>

                {/* Cycle de facturation */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Cycle de facturation</label>
                  <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
                    <button
                      type="button"
                      onClick={() => setCycle('MENSUEL')}
                      className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                        cycle === 'MENSUEL' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      Mensuel
                    </button>
                    <button
                      type="button"
                      onClick={() => setCycle('ANNUEL')}
                      className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                        cycle === 'ANNUEL' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      Annuel
                    </button>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleContinuer}
                  disabled={planActuel === planChoisi}
                  className="w-full py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 transition-all disabled:opacity-50"
                >
                  Continuer — {montant.toLocaleString('fr-FR')} XAF / {cycle === 'MENSUEL' ? 'mois' : 'an'}
                </button>
              </>
            )
          )}

          {etape === 'paiement' && (
            <form onSubmit={handleInitierPaiement} className="space-y-4">
              <div className="p-3 rounded-xl bg-muted/40 border border-border text-xs text-muted-foreground">
                Formule <strong className="text-foreground">{LABEL_PLAN[planChoisi] ?? planChoisi}</strong> —{' '}
                <strong className="text-foreground">{montant.toLocaleString('fr-FR')} XAF</strong> / {cycle === 'MENSUEL' ? 'mois' : 'an'}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Opérateur Mobile Money</label>
                <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
                  <button
                    type="button"
                    onClick={() => setOperator('orange')}
                    className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                      operator === 'orange' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Orange Money
                  </button>
                  <button
                    type="button"
                    onClick={() => setOperator('mtn')}
                    className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                      operator === 'mtn' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    MTN MoMo
                  </button>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
                  <Smartphone className="h-3.5 w-3.5" />
                  <span>Numéro Mobile Money</span>
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
                  Retour
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  <span>Payer maintenant</span>
                </button>
              </div>
            </form>
          )}

          {etape === 'attente' && (
            <div className="text-center space-y-3 py-6">
              <Loader2 className="h-10 w-10 mx-auto animate-spin text-primary" />
              <p className="text-sm font-bold text-foreground">Confirmation en attente</p>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Validez la demande de paiement de <strong>{montant.toLocaleString('fr-FR')} XAF</strong> reçue sur votre téléphone
                ({phone}) via {operator === 'orange' ? 'Orange Money' : 'MTN MoMo'}.
              </p>
              {paiement && (
                <p className="text-[11px] text-muted-foreground">Référence : {paiement.reference_hrpay}</p>
              )}
            </div>
          )}

          {etape === 'succes' && (
            <div className="text-center space-y-3 py-6">
              <CheckCircle2 className="h-10 w-10 mx-auto text-forest-500" />
              <p className="text-sm font-bold text-foreground">Paiement confirmé !</p>
              <p className="text-xs text-muted-foreground">
                Votre formule {LABEL_PLAN[planChoisi] ?? planChoisi} est maintenant active.
              </p>
              <button
                type="button"
                onClick={handleClose}
                className="mt-2 py-2.5 px-6 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95"
              >
                Terminer
              </button>
            </div>
          )}

          {etape === 'echec' && (
            <div className="text-center space-y-3 py-6">
              <AlertTriangle className="h-10 w-10 mx-auto text-destructive" />
              <p className="text-sm font-bold text-foreground">Paiement refusé ou expiré</p>
              <p className="text-xs text-muted-foreground">Aucun montant n'a été débité. Vous pouvez réessayer.</p>
              <button
                type="button"
                onClick={() => setEtape('paiement')}
                className="mt-2 py-2.5 px-6 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95"
              >
                Réessayer
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
