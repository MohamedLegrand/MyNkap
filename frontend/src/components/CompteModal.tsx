import React, { useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '../services/api';

interface CompteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const CompteModal: React.FC<CompteModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [nom, setNom] = useState('');
  const [type, setType] = useState<'MOBILE_MONEY' | 'BANCAIRE' | 'ESPECES'>('MOBILE_MONEY');
  const [soldeInitial, setSoldeInitial] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await api.request('/comptes', {
        method: 'POST',
        body: JSON.stringify({
          nom,
          type,
          solde_initial: soldeInitial ? Number(soldeInitial) : 0,
        }),
      });
      setNom('');
      setSoldeInitial('');
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Création du compte impossible.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">Créer compte</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Nom du compte</label>
            <input
              type="text"
              required
              placeholder="ex: Orange Money"
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Type de compte</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as 'MOBILE_MONEY' | 'BANCAIRE' | 'ESPECES')}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="MOBILE_MONEY">Mobile Money (Orange, MTN...)</option>
              <option value="BANCAIRE">Compte bancaire</option>
              <option value="ESPECES">Espèces / Cash</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Solde de départ (facultatif)</label>
            <input
              type="number"
              min={0}
              placeholder="0"
              value={soldeInitial}
              onChange={(e) => setSoldeInitial(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
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
              <span>Créer compte</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
