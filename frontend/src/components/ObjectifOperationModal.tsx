import React, { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { CompteFinancier, ObjectifEpargne } from '../types';

interface ObjectifOperationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  objectif: ObjectifEpargne | null;
  operation: 'alimenter' | 'retirer';
  comptes: CompteFinancier[];
}

// Alimenter (verser vers l'épargne) ou retirer (reprendre de l'épargne) :
// même formulaire, seul l'endpoint et le libellé du compte changent.
export const ObjectifOperationModal: React.FC<ObjectifOperationModalProps> = ({
  isOpen, onClose, onSuccess, objectif, operation, comptes,
}) => {
  const [montant, setMontant] = useState('');
  const [idCompte, setIdCompte] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && comptes.length > 0 && !idCompte) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIdCompte(String(comptes[0].id_compte));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, comptes]);

  if (!isOpen || !objectif) return null;

  const estAlimentation = operation === 'alimenter';
  const endpoint = `/epargne/${objectif.id_objectif}/${operation}`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idCompte) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const cle = estAlimentation ? 'id_compte_source' : 'id_compte_destination';
      await api.request(endpoint, {
        method: 'POST',
        body: JSON.stringify({ montant: Number(montant), [cle]: Number(idCompte) }),
      });
      setMontant('');
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Opération impossible.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-sm rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">{estAlimentation ? 'Alimenter' : 'Retirer'} — {objectif.nom}</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <p className="text-xs text-muted-foreground">
            {estAlimentation ? 'Actuellement épargné' : 'Disponible pour retrait'} : <strong className="text-foreground">{Number(objectif.montant_actuel).toLocaleString('fr-FR')} XAF</strong>
          </p>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Montant (XAF)</label>
            <input
              type="number"
              required
              min={1}
              max={estAlimentation ? undefined : objectif.montant_actuel}
              placeholder="ex: 20000"
              value={montant}
              onChange={(e) => setMontant(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">
              {estAlimentation ? 'Compte source' : 'Compte de destination'}
            </label>
            <select
              value={idCompte}
              onChange={(e) => setIdCompte(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {comptes.map((c) => (
                <option key={c.id_compte} value={c.id_compte}>{c.nom}</option>
              ))}
            </select>
          </div>

          {error && <p className="text-sm text-destructive text-center">{error}</p>}

          <div className="pt-2 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">
              Annuler
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !idCompte}
              className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>Confirmer</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
