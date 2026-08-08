import React, { useEffect, useState } from 'react';
import { X, Loader2, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import type { CompteFinancier, ObjectifEpargne } from '../types';

interface ObjectifOperationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  objectif: ObjectifEpargne | null;
  operation: 'alimenter' | 'retirer' | 'abandonner';
  comptes: CompteFinancier[];
}

// Alimenter (verser vers l'épargne), retirer (reprendre de l'épargne) ou
// abandonner (vider et verrouiller définitivement) : même formulaire de
// base, seul l'endpoint et les champs affichés changent selon l'opération.
export const ObjectifOperationModal: React.FC<ObjectifOperationModalProps> = ({
  isOpen, onClose, onSuccess, objectif, operation, comptes,
}) => {
  const [montant, setMontant] = useState('');
  const [idCompte, setIdCompte] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [objectifFrais, setObjectifFrais] = useState<ObjectifEpargne | null>(null);

  useEffect(() => {
    if (isOpen && comptes.length > 0 && !idCompte) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIdCompte(String(comptes[0].id_compte));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, comptes]);

  useEffect(() => {
    // Relit l'objectif depuis le serveur à l'ouverture plutôt que de se fier
    // à la liste locale (potentiellement périmée) — pas une synchronisation
    // d'état dérivé.
    if (isOpen && objectif) {
      api.request<ObjectifEpargne>(`/epargne/${objectif.id_objectif}`).then(setObjectifFrais).catch(() => {});
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setObjectifFrais(null);
    }
  }, [isOpen, objectif]);

  if (!isOpen || !objectif) return null;

  const objectifAffiche = objectifFrais ?? objectif;
  const estAlimentation = operation === 'alimenter';
  const estAbandon = operation === 'abandonner';
  const endpoint = `/epargne/${objectifAffiche.id_objectif}/${operation}`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idCompte) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const body = estAbandon
        ? { id_compte_destination: Number(idCompte) }
        : { montant: Number(montant), [estAlimentation ? 'id_compte_source' : 'id_compte_destination']: Number(idCompte) };
      await api.request(endpoint, { method: 'POST', body: JSON.stringify(body) });
      setMontant('');
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Opération impossible.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const titre = estAlimentation ? 'Alimenter' : estAbandon ? 'Abandonner' : 'Retirer';

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-sm rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">{titre} — {objectifAffiche.nom}</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {estAbandon ? (
            <div className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 flex items-start gap-2.5">
              <AlertTriangle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
              <p className="text-xs text-destructive leading-relaxed">
                Cette action verrouille définitivement l'objectif et transfère la totalité du solde épargné
                (<strong>{Number(objectifAffiche.montant_actuel).toLocaleString('fr-FR')} XAF</strong>) vers le compte choisi ci-dessous.
              </p>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              {estAlimentation ? 'Actuellement épargné' : 'Disponible pour retrait'} : <strong className="text-foreground">{Number(objectifAffiche.montant_actuel).toLocaleString('fr-FR')} XAF</strong>
            </p>
          )}

          {!estAbandon && (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Montant (XAF)</label>
              <input
                type="number"
                required
                min={1}
                max={estAlimentation ? undefined : objectifAffiche.montant_actuel}
                placeholder="ex: 20000"
                value={montant}
                onChange={(e) => setMontant(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          )}

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
              className={`flex-1 py-3 px-4 rounded-xl text-sm font-bold shadow-md flex items-center justify-center gap-2 disabled:opacity-50 ${
                estAbandon ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90' : 'bg-primary text-primary-foreground hover:bg-primary/95'
              }`}
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>{estAbandon ? 'Confirmer l\'abandon' : 'Confirmer'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
