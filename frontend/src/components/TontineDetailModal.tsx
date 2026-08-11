import React, { useEffect, useState } from 'react';
import { X, Loader2, Users, CheckCircle2, Circle, Ban, PartyPopper } from 'lucide-react';
import { api } from '../services/api';
import type { TontineDetail } from '../types';

interface TontineDetailModalProps {
  isOpen: boolean;
  idTontine: number | null;
  onClose: () => void;
  onChange?: () => void;
}

const formatXAF = (valeur: number) => `${Number(valeur).toLocaleString('fr-FR')} XAF`;

const STATUT_TONTINE_STYLE: Record<string, string> = {
  ACTIVE: 'bg-primary/10 text-primary',
  TERMINEE: 'bg-forest-500/10 text-forest-600 dark:text-forest-400',
  ANNULEE: 'bg-destructive/10 text-destructive',
};

const STATUT_TOUR_STYLE: Record<string, string> = {
  A_VENIR: 'bg-muted text-muted-foreground',
  EN_COURS: 'bg-primary/10 text-primary',
  TERMINE: 'bg-forest-500/10 text-forest-600 dark:text-forest-400',
};

export const TontineDetailModal: React.FC<TontineDetailModalProps> = ({ isOpen, idTontine, onClose, onChange }) => {
  const [detail, setDetail] = useState<TontineDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const charger = () => {
    if (idTontine === null) return;
    setIsLoading(true);
    setError(null);
    api
      .request<TontineDetail>(`/tontines/${idTontine}`)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : 'Impossible de charger cette tontine.'))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    if (!isOpen || idTontine === null) return;
    // Chargement à l'ouverture — pas une synchronisation d'état dérivé.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDetail(null);
    charger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, idTontine]);

  if (!isOpen || idTontine === null) return null;

  const toggleCotisation = async (idTour: number, idMembre: number, estVersee: boolean) => {
    setBusy(true);
    setError(null);
    try {
      const maj = await api.request<TontineDetail>(
        `/tontines/${idTontine}/tours/${idTour}/membres/${idMembre}/cotisation`,
        { method: 'PATCH', body: JSON.stringify({ est_versee: !estVersee }) }
      );
      setDetail(maj);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action impossible.');
    } finally {
      setBusy(false);
    }
  };

  const cloturerTour = async (idTour: number) => {
    setBusy(true);
    setError(null);
    try {
      const maj = await api.request<TontineDetail>(`/tontines/${idTontine}/tours/${idTour}/cloturer`, {
        method: 'POST',
      });
      setDetail(maj);
      onChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Clôture impossible.');
    } finally {
      setBusy(false);
    }
  };

  const annulerTontine = async () => {
    if (!window.confirm('Annuler définitivement cette tontine ? Les tours et cotisations déjà enregistrés resteront consultables.')) return;
    setBusy(true);
    setError(null);
    try {
      await api.request(`/tontines/${idTontine}/annuler`, { method: 'POST' });
      onChange?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Annulation impossible.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <Users className="h-5 w-5 text-primary shrink-0" />
            <h3 className="text-base font-bold truncate">{detail?.nom ?? 'Tontine'}</h3>
            {detail && (
              <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full shrink-0 ${STATUT_TONTINE_STYLE[detail.statut]}`}>
                {detail.statut}
              </span>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground shrink-0">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {isLoading || !detail ? (
            <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="p-3 rounded-xl border border-border">
                  <p className="text-muted-foreground">Cotisation / membre</p>
                  <p className="font-black text-foreground text-sm">{formatXAF(detail.montant_cotisation)}</p>
                </div>
                <div className="p-3 rounded-xl border border-border">
                  <p className="text-muted-foreground">Cagnotte / tour</p>
                  <p className="font-black text-primary text-sm">{formatXAF(detail.montant_total_par_tour)}</p>
                </div>
                <div className="p-3 rounded-xl border border-border">
                  <p className="text-muted-foreground">Fréquence</p>
                  <p className="font-black text-foreground text-sm">{detail.frequence === 'HEBDOMADAIRE' ? 'Hebdo' : 'Mensuelle'}</p>
                </div>
              </div>

              <div className="space-y-1.5">
                <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Membres ({detail.membres.length})</p>
                <div className="flex flex-wrap gap-1.5">
                  {detail.membres.map((m) => (
                    <span key={m.id_membre} className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-muted text-foreground">
                      {m.ordre}. {m.nom}
                    </span>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Tours de rotation</p>
                {detail.tours.map((t) => (
                  <div
                    key={t.id_tour}
                    className={`p-4 rounded-xl border space-y-3 ${t.statut === 'EN_COURS' ? 'border-primary/40 bg-primary/5' : 'border-border bg-muted/20'}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <h4 className="text-sm font-bold text-foreground truncate">
                          Tour {t.numero} — {t.nom_beneficiaire}
                        </h4>
                        <span className="text-xs text-muted-foreground">
                          {new Date(t.date_prevue).toLocaleDateString('fr-FR')} • {t.nombre_cotisations_versees}/{t.nombre_cotisations_total} versées
                        </span>
                      </div>
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full shrink-0 ${STATUT_TOUR_STYLE[t.statut]}`}>
                        {t.statut}
                      </span>
                    </div>

                    {t.statut === 'EN_COURS' && (
                      <>
                        <div className="space-y-1.5">
                          {t.cotisations.map((c) => (
                            <button
                              key={c.id_cotisation}
                              type="button"
                              disabled={busy || detail.statut !== 'ACTIVE'}
                              onClick={() => toggleCotisation(t.id_tour, c.id_membre, c.est_versee)}
                              className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-muted/50 text-left disabled:opacity-60 transition-colors"
                            >
                              {c.est_versee ? (
                                <CheckCircle2 className="h-4 w-4 text-forest-600 dark:text-forest-400 shrink-0" />
                              ) : (
                                <Circle className="h-4 w-4 text-muted-foreground shrink-0" />
                              )}
                              <span className={`text-xs font-semibold ${c.est_versee ? 'text-foreground' : 'text-muted-foreground'}`}>
                                {c.nom_membre}
                              </span>
                            </button>
                          ))}
                        </div>
                        {detail.statut === 'ACTIVE' && (
                          <button
                            onClick={() => cloturerTour(t.id_tour)}
                            disabled={busy || t.nombre_cotisations_versees < t.nombre_cotisations_total}
                            className="w-full py-2 rounded-lg bg-primary text-primary-foreground text-xs font-bold flex items-center justify-center gap-1.5 disabled:opacity-40"
                          >
                            <PartyPopper className="h-3.5 w-3.5" />
                            <span>Clôturer et remettre la cagnotte</span>
                          </button>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>

              {error && <p className="text-sm text-destructive text-center">{error}</p>}

              {detail.statut === 'ACTIVE' && (
                <button
                  onClick={annulerTontine}
                  disabled={busy}
                  className="w-full py-2.5 rounded-xl bg-destructive/10 hover:bg-destructive/20 text-destructive text-xs font-bold flex items-center justify-center gap-1.5 disabled:opacity-60"
                >
                  <Ban className="h-3.5 w-3.5" />
                  <span>Annuler la tontine</span>
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
