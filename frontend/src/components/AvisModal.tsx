import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Loader2, Star, MessageSquareHeart, Clock, CheckCircle2, XCircle } from 'lucide-react';
import { api } from '../services/api';
import type { Avis } from '../types';

interface AvisModalProps {
  isOpen: boolean;
  onClose: () => void;
  // Notifie le parent une fois qu'un avis existe (publié ou non) — permet
  // de masquer la bannière d'invitation après une première soumission.
  onSubmitted?: () => void;
}

export const AvisModal: React.FC<AvisModalProps> = ({ isOpen, onClose, onSubmitted }) => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [monAvis, setMonAvis] = useState<Avis | null>(null);
  const [note, setNote] = useState(0);
  const [noteSurvolee, setNoteSurvolee] = useState(0);
  const [commentaire, setCommentaire] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsLoading(true);
    setError(null);
    api
      .request<Avis | null>('/avis/moi')
      .then(setMonAvis)
      .catch((err) => setError(err instanceof Error ? err.message : t('modals.avis.error_load')))
      .finally(() => setIsLoading(false));
  }, [isOpen, t]);

  if (!isOpen) return null;

  const handleClose = () => {
    // "Plus tard" implicite : fermer sans avoir soumis d'avis reporte la
    // prochaine invitation active de 7 jours (voir avis.service.
    // reporter_avis). Fire-and-forget — la fermeture ne doit jamais
    // attendre la réponse réseau, et un échec réseau ici n'a pas besoin
    // d'être signalé au client (au pire, il sera redemandé un peu plus tôt).
    if (monAvis === null && !isLoading) {
      api.request('/avis/reporter', { method: 'POST' }).catch(() => {});
    }
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (note === 0 || !commentaire.trim()) return;

    setError(null);
    setIsSubmitting(true);
    try {
      const avis = await api.request<Avis>('/avis', {
        method: 'POST',
        body: JSON.stringify({ note, commentaire: commentaire.trim() }),
      });
      setMonAvis(avis);
      onSubmitted?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.avis.error_submit'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const STATUT_INFO: Record<Avis['statut'], { icon: React.ElementType; label: string; className: string }> = {
    EN_ATTENTE: { icon: Clock, label: t('modals.avis.status_pending'), className: 'text-amber-600 bg-amber-500/10' },
    PUBLIE: { icon: CheckCircle2, label: t('modals.avis.status_published'), className: 'text-forest-600 bg-forest-500/10' },
    REJETE: { icon: XCircle, label: t('modals.avis.status_rejected'), className: 'text-muted-foreground bg-muted' },
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight flex items-center gap-2">
            <MessageSquareHeart className="h-5 w-5 text-primary" />
            <span>{t('modals.avis.title')}</span>
          </h3>
          <button onClick={handleClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6">
          {isLoading ? (
            <div className="flex justify-center py-14">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : monAvis ? (
            (() => {
              const info = STATUT_INFO[monAvis.statut];
              const StatutIcon = info.icon;
              return (
                <div className="text-center space-y-4 py-4">
                  <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold ${info.className}`}>
                    <StatutIcon className="h-3.5 w-3.5" />
                    <span>{info.label}</span>
                  </div>
                  <div className="flex justify-center gap-1">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <Star key={n} className={`h-5 w-5 ${n <= monAvis.note ? 'fill-secondary text-secondary' : 'text-muted-foreground/30'}`} />
                    ))}
                  </div>
                  <p className="text-sm text-muted-foreground italic">"{monAvis.commentaire}"</p>
                  <p className="text-xs text-muted-foreground">{t('modals.avis.already_submitted')}</p>
                </div>
              );
            })()
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <p className="text-sm text-muted-foreground text-center">{t('modals.avis.prompt')}</p>

              <div className="flex justify-center gap-1.5">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setNote(n)}
                    onMouseEnter={() => setNoteSurvolee(n)}
                    onMouseLeave={() => setNoteSurvolee(0)}
                    aria-label={t('modals.avis.star_label', { n })}
                    className="p-0.5"
                  >
                    <Star className={`h-8 w-8 transition-colors ${n <= (noteSurvolee || note) ? 'fill-secondary text-secondary' : 'text-muted-foreground/30'}`} />
                  </button>
                ))}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">{t('modals.avis.comment_label')}</label>
                <textarea
                  required
                  rows={4}
                  maxLength={1000}
                  value={commentaire}
                  onChange={(e) => setCommentaire(e.target.value)}
                  placeholder={t('modals.avis.comment_placeholder')}
                  className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              {error && <p className="text-sm text-destructive text-center">{error}</p>}

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleClose}
                  className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted"
                >
                  {t('modals.avis.later')}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || note === 0 || !commentaire.trim()}
                  className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  <span>{t('modals.avis.submit')}</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
