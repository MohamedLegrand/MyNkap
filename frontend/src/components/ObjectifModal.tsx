import React, { useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '../services/api';

interface ObjectifModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const ObjectifModal: React.FC<ObjectifModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [nom, setNom] = useState('');
  const [montantCible, setMontantCible] = useState('');
  const [dateEcheance, setDateEcheance] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Création impossible.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">Créer un objectif d'épargne</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Nom du projet</label>
            <input
              type="text"
              required
              placeholder="ex: Terrain Douala, Voyage..."
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Montant cible (XAF)</label>
            <input
              type="number"
              required
              min={1}
              placeholder="ex: 500000"
              value={montantCible}
              onChange={(e) => setMontantCible(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Échéance (facultatif)</label>
            <input
              type="date"
              value={dateEcheance}
              onChange={(e) => setDateEcheance(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
            {dateEcheance && (
              <p className="text-[11px] text-muted-foreground">
                Une échéance permet d'estimer le montant mensuel à épargner pour l'atteindre.
              </p>
            )}
          </div>

          {error && <p className="text-sm text-destructive text-center">{error}</p>}

          <div className="pt-2 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">
              Annuler
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>Créer l'objectif</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
