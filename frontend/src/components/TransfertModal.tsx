import React, { useEffect, useState } from 'react';
import { X, Loader2, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import type { CompteFinancier } from '../types';

interface TransfertModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  comptes: CompteFinancier[];
}

export const TransfertModal: React.FC<TransfertModalProps> = ({ isOpen, onClose, onSuccess, comptes }) => {
  const [idCompteSource, setIdCompteSource] = useState('');
  const [idCompteDestination, setIdCompteDestination] = useState('');
  const [montant, setMontant] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Présélectionne source/destination dès que les comptes sont
    // disponibles — chargés de façon asynchrone après le montage de la
    // modale, l'état initial ne peut donc pas s'y fier directement.
    if (isOpen && comptes.length >= 2 && !idCompteSource) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIdCompteSource(String(comptes[0].id_compte));
      setIdCompteDestination(String(comptes[1].id_compte));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, comptes]);

  if (!isOpen) return null;

  const comptesDestinationDisponibles = comptes.filter((c) => String(c.id_compte) !== idCompteSource);
  const soldeSource = comptes.find((c) => String(c.id_compte) === idCompteSource)?.solde;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idCompteSource || !idCompteDestination) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await api.request('/transferts', {
        method: 'POST',
        body: JSON.stringify({
          id_compte_source: Number(idCompteSource),
          id_compte_destination: Number(idCompteDestination),
          montant: Number(montant),
          description: description || undefined,
        }),
      });
      setMontant('');
      setDescription('');
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Transfert impossible.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">Transférer entre comptes</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-[1fr_auto_1fr] items-end gap-2">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Depuis</label>
              <select
                value={idCompteSource}
                onChange={(e) => {
                  const nouvelleSource = e.target.value;
                  setIdCompteSource(nouvelleSource);
                  // Si la destination actuelle devient identique à la
                  // nouvelle source, elle disparaît de la liste "Vers" —
                  // il faut la resynchroniser explicitement avec le nouveau
                  // premier choix restant, sinon le <select> affiche cette
                  // option (comportement natif du navigateur) alors que
                  // l'état React, lui, reste vide (bouton bloqué à tort).
                  if (nouvelleSource === idCompteDestination) {
                    const prochaine = comptes.find((c) => String(c.id_compte) !== nouvelleSource);
                    setIdCompteDestination(prochaine ? String(prochaine.id_compte) : '');
                  }
                }}
                className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {comptes.map((c) => (
                  <option key={c.id_compte} value={c.id_compte}>{c.nom}</option>
                ))}
              </select>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground mb-3" />
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Vers</label>
              <select
                value={idCompteDestination}
                onChange={(e) => setIdCompteDestination(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {comptesDestinationDisponibles.map((c) => (
                  <option key={c.id_compte} value={c.id_compte}>{c.nom}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Montant (XAF)</label>
            <input
              type="number"
              required
              min={1}
              max={soldeSource !== undefined ? Number(soldeSource) : undefined}
              placeholder="ex: 10000"
              value={montant}
              onChange={(e) => setMontant(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
            {soldeSource !== undefined && (
              <p className="text-[11px] text-muted-foreground">
                Solde disponible : {Number(soldeSource).toLocaleString('fr-FR')} XAF
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Note / Description (facultatif)</label>
            <input
              type="text"
              placeholder="ex: Réserve d'épargne du mois"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {error && <p className="text-sm text-destructive text-center">{error}</p>}

          <div className="pt-2 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">
              Annuler
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !idCompteSource || !idCompteDestination}
              className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>Transférer</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
