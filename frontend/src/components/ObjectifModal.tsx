import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Loader2, TrendingUp } from 'lucide-react';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../services/api';

interface ObjectifModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

// La réponse de /epargne/simuler : les montants (Decimal côté backend)
// arrivent en chaîne de caractères dans le JSON, on les coerce avec Number().
interface SimulationObjectif {
  nombre_mois: number | null;
  montant_mensuel_requis: string | number | null;
  projection: { mois: string; montant_cumule: string | number }[];
}

const AXE_STYLE = { fontSize: 10, fill: 'hsl(var(--muted-foreground))' };
const STYLE_TOOLTIP = {
  contentStyle: {
    background: 'hsl(var(--card))',
    border: '1px solid hsl(var(--border))',
    borderRadius: 12,
    fontSize: 12,
  },
  labelStyle: { color: 'hsl(var(--muted-foreground))' },
};

const formatMontant = (valeur: string | number) => `${Number(valeur).toLocaleString('fr-FR')} XAF`;

export const ObjectifModal: React.FC<ObjectifModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const { t } = useTranslation();
  const [nom, setNom] = useState('');
  const [montantCible, setMontantCible] = useState('');
  const [dateEcheance, setDateEcheance] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [simulation, setSimulation] = useState<SimulationObjectif | null>(null);

  // Simulation en direct : dès qu'une cible ET une échéance sont saisies, on
  // interroge /epargne/simuler (débounce 400 ms pour ne pas appeler à chaque
  // frappe). Aucun effet de bord serveur — la simulation ne crée rien.
  useEffect(() => {
    if (!isOpen) return;
    const cible = Number(montantCible);
    if (!cible || cible <= 0 || !dateEcheance) {
      // Réinitialisation d'un état dérivé d'entrées invalides, pas une
      // synchronisation d'état en cascade.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSimulation(null);
      return;
    }
    const minuteur = setTimeout(() => {
      api
        .request<SimulationObjectif>('/epargne/simuler', {
          method: 'POST',
          body: JSON.stringify({ montant_cible: cible, date_echeance: dateEcheance }),
        })
        .then(setSimulation)
        .catch(() => setSimulation(null));
    }, 400);
    return () => clearTimeout(minuteur);
  }, [isOpen, montantCible, dateEcheance]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await api.request('/epargne', {
        method: 'POST',
        body: JSON.stringify({
          nom,
          montant_cible: Number(montantCible),
          date_echeance: dateEcheance || undefined,
        }),
      });
      setNom('');
      setMontantCible('');
      setDateEcheance('');
      setSimulation(null);
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.objectif.error_create'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const courbe = simulation?.projection.map((p) => ({ mois: p.mois, montant: Number(p.montant_cumule) })) ?? [];

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40 sticky top-0">
          <h3 className="text-lg font-bold tracking-tight">{t('savings.create')}</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.objectif.name_label')}</label>
            <input
              type="text"
              required
              placeholder={t('modals.objectif.name_placeholder')}
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-hidden focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.objectif.target_amount_label')}</label>
            <input
              type="number"
              required
              min={1}
              placeholder="ex: 500000"
              value={montantCible}
              onChange={(e) => setMontantCible(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-hidden focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.objectif.due_date_label')}</label>
            <input
              type="date"
              value={dateEcheance}
              onChange={(e) => setDateEcheance(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-hidden focus:ring-2 focus:ring-primary"
            />
            {dateEcheance && (
              <p className="text-[11px] text-muted-foreground">
                {t('modals.objectif.due_date_hint')}
              </p>
            )}
          </div>

          {/* Simulateur visuel : effort mensuel + courbe d'accumulation,
              recalculés en direct pendant la saisie. */}
          {simulation && simulation.montant_mensuel_requis != null && (
            <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-3 animate-in fade-in duration-200">
              <div className="flex items-center gap-2 text-primary">
                <TrendingUp className="h-4 w-4" />
                <span className="text-xs font-bold uppercase tracking-wide">{t('modals.objectif.simulation_title')}</span>
              </div>
              <p className="text-sm text-foreground">
                {t('modals.objectif.monthly_effort')} :{' '}
                <strong className="text-primary tabular-nums">{formatMontant(simulation.montant_mensuel_requis)}</strong>
                {simulation.nombre_mois != null && (
                  <span className="text-muted-foreground"> · {t('modals.objectif.over_months', { count: simulation.nombre_mois })}</span>
                )}
              </p>
              {courbe.length > 0 && (
                <ResponsiveContainer width="100%" height={140}>
                  <AreaChart data={courbe} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="gradientEpargne" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="mois" tick={AXE_STYLE} interval="preserveStartEnd" minTickGap={24} />
                    <YAxis tick={AXE_STYLE} width={48} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
                    <Tooltip formatter={(value: unknown) => formatMontant(Number(value))} {...STYLE_TOOLTIP} />
                    <Area type="monotone" dataKey="montant" stroke="hsl(var(--primary))" strokeWidth={2} fill="url(#gradientEpargne)" isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
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
              <span>{t('modals.objectif.submit')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
