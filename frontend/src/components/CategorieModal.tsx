import React, { useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '../services/api';

interface CategorieModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const CategorieModal: React.FC<CategorieModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [nom, setNom] = useState('');
  const [type, setType] = useState<'DEPENSE' | 'REVENU'>('DEPENSE');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await api.request('/categories', {
        method: 'POST',
        body: JSON.stringify({ nom, type }),
      });
      setNom('');
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Création de la catégorie impossible.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">Créer catégorie</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Nom de la catégorie</label>
            <input
              type="text"
              required
              placeholder="ex: Transport, Loyer, Salaire..."
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Type de catégorie</label>
            <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
              <button
                type="button"
                onClick={() => setType('DEPENSE')}
                className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                  type === 'DEPENSE' ? 'bg-destructive text-destructive-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Dépense
              </button>
              <button
                type="button"
                onClick={() => setType('REVENU')}
                className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                  type === 'REVENU' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Revenu
              </button>
            </div>
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
              <span>Créer catégorie</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
