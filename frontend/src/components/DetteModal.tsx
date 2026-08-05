import React, { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { CompteFinancier } from '../types';

interface DetteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  comptes: CompteFinancier[];
}

export const DetteModal: React.FC<DetteModalProps> = ({ isOpen, onClose, onSuccess, comptes }) => {
  const [type, setType] = useState<'DETTE' | 'CREANCE'>('DETTE');
  const [nom, setNom] = useState('');
  const [montantTotal, setMontantTotal] = useState('');
  const [personneImpliquee, setPersonneImpliquee] = useState('');
  const [dateEcheance, setDateEcheance] = useState('');
  const [idCompte, setIdCompte] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Présélectionne le premier compte dès qu'il est disponible — la liste
    // des comptes se charge de façon asynchrone après le montage de la
    // modale, donc l'état initial ne peut pas s'y fier directement.
    if (isOpen && comptes.length > 0 && !idCompte) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIdCompte(String(comptes[0].id_compte));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, comptes]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idCompte) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await api.request('/dettes', {
        method: 'POST',
        body: JSON.stringify({
          id_compte: Number(idCompte),
          type,
          nom,
          montant_total: Number(montantTotal),
          personne_impliquee: personneImpliquee || undefined,
          date_echeance: dateEcheance || undefined,
        }),
      });
      setNom('');
      setMontantTotal('');
      setPersonneImpliquee('');
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
          <h3 className="text-lg font-bold tracking-tight">Déclarer une dette / créance</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
            <button
              type="button"
              onClick={() => setType('DETTE')}
              className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                type === 'DETTE' ? 'bg-destructive text-destructive-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Dette (je dois)
            </button>
            <button
              type="button"
              onClick={() => setType('CREANCE')}
              className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                type === 'CREANCE' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Créance (on me doit)
            </button>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Nom / motif</label>
            <input
              type="text"
              required
              placeholder="ex: Prêt voiture, Avance à Paul..."
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Montant total (XAF)</label>
            <input
              type="number"
              required
              min={1}
              placeholder="ex: 50000"
              value={montantTotal}
              onChange={(e) => setMontantTotal(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Compte concerné</label>
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

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Personne concernée (facultatif)</label>
            <input
              type="text"
              placeholder="ex: Paul"
              value={personneImpliquee}
              onChange={(e) => setPersonneImpliquee(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
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
              <span>Enregistrer</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
