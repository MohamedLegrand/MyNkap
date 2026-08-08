import React, { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { Categorie, CompteFinancier, TransactionRecurrente } from '../types';

interface TransactionRecurrenteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  comptes: CompteFinancier[];
  categories: Categorie[];
  // Présent = mode édition (PUT) ; absent/null = création.
  recurrence?: TransactionRecurrente | null;
}

const FREQUENCES: { valeur: TransactionRecurrente['frequence']; label: string }[] = [
  { valeur: 'HEBDOMADAIRE', label: 'Chaque semaine' },
  { valeur: 'MENSUELLE', label: 'Chaque mois' },
  { valeur: 'TRIMESTRIELLE', label: 'Chaque trimestre' },
  { valeur: 'ANNUELLE', label: 'Chaque année' },
];

export const TransactionRecurrenteModal: React.FC<TransactionRecurrenteModalProps> = ({
  isOpen, onClose, onSuccess, comptes, categories, recurrence = null,
}) => {
  const modeEdition = recurrence !== null;

  const [type, setType] = useState<'DEPENSE' | 'REVENU'>('DEPENSE');
  const [idCompte, setIdCompte] = useState('');
  const [idCategorie, setIdCategorie] = useState('');
  const [montant, setMontant] = useState('');
  const [description, setDescription] = useState('');
  const [frequence, setFrequence] = useState<TransactionRecurrente['frequence']>('MENSUELLE');
  const [prochaineExecution, setProchaineExecution] = useState(() => new Date().toISOString().slice(0, 10));
  const [dateFin, setDateFin] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const categoriesFiltrees = categories.filter((c) => c.type === type && c.est_actif);

  useEffect(() => {
    if (!isOpen) return;
    if (recurrence) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsLoadingDetail(true);
      setError(null);
      api
        .request<TransactionRecurrente>(`/transactions-recurrentes/${recurrence.id_transaction_recurrente}`)
        .then((fraiche) => {
          setType(fraiche.type);
          setIdCompte(String(fraiche.id_compte));
          setIdCategorie(String(fraiche.id_categorie));
          setMontant(String(fraiche.montant));
          setDescription(fraiche.description ?? '');
          setFrequence(fraiche.frequence);
          setProchaineExecution(fraiche.prochaine_execution.slice(0, 10));
          setDateFin(fraiche.date_fin ? fraiche.date_fin.slice(0, 10) : '');
        })
        .catch((err) => setError(err instanceof Error ? err.message : 'Impossible de charger cette récurrence.'))
        .finally(() => setIsLoadingDetail(false));
    } else {
      setType('DEPENSE');
      setMontant('');
      setDescription('');
      setDateFin('');
      if (comptes.length > 0) setIdCompte(String(comptes[0].id_compte));
    }
  }, [isOpen, recurrence, comptes]);

  useEffect(() => {
    // Resynchronise la catégorie si le type change et que la catégorie
    // actuelle ne correspond plus — pas une synchronisation d'état dérivé
    // d'un rendu précédent (dépend d'une action utilisateur : changer `type`).
    if (isOpen && categoriesFiltrees.length > 0 && !categoriesFiltrees.some((c) => String(c.id_categorie) === idCategorie)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIdCategorie(String(categoriesFiltrees[0].id_categorie));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, type, categories]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idCompte || !idCategorie) return;
    setError(null);
    setIsSubmitting(true);
    try {
      if (modeEdition && recurrence) {
        await api.request(`/transactions-recurrentes/${recurrence.id_transaction_recurrente}`, {
          method: 'PUT',
          body: JSON.stringify({
            montant: Number(montant),
            description: description || null,
            frequence,
            prochaine_execution: prochaineExecution,
            date_fin: dateFin || null,
          }),
        });
      } else {
        await api.request('/transactions-recurrentes', {
          method: 'POST',
          body: JSON.stringify({
            id_compte: Number(idCompte),
            id_categorie: Number(idCategorie),
            montant: Number(montant),
            type,
            description: description || null,
            frequence,
            prochaine_execution: prochaineExecution,
            date_fin: dateFin || null,
          }),
        });
      }
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : `${modeEdition ? 'Modification' : 'Création'} de la récurrence impossible.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">{modeEdition ? 'Modifier la récurrence' : 'Planifier une transaction récurrente'}</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {isLoadingDetail ? (
          <div className="flex justify-center py-14">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {!modeEdition && (
              <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
                <button type="button" onClick={() => setType('DEPENSE')} className={`py-2.5 rounded-lg text-xs font-bold transition-all ${type === 'DEPENSE' ? 'bg-destructive text-destructive-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}>
                  Dépense
                </button>
                <button type="button" onClick={() => setType('REVENU')} className={`py-2.5 rounded-lg text-xs font-bold transition-all ${type === 'REVENU' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}>
                  Revenu
                </button>
              </div>
            )}

            {!modeEdition && (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Compte</label>
                  <select value={idCompte} onChange={(e) => setIdCompte(e.target.value)} className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary">
                    {comptes.map((c) => <option key={c.id_compte} value={c.id_compte}>{c.nom}</option>)}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Catégorie</label>
                  <select value={idCategorie} onChange={(e) => setIdCategorie(e.target.value)} className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary">
                    {categoriesFiltrees.map((c) => <option key={c.id_categorie} value={c.id_categorie}>{c.nom}</option>)}
                  </select>
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Montant (XAF)</label>
              <input type="number" required min={1} value={montant} onChange={(e) => setMontant(e.target.value)} placeholder="ex: 15000" className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Description (facultatif)</label>
              <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="ex: Abonnement Netflix" className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Fréquence</label>
              <select value={frequence} onChange={(e) => setFrequence(e.target.value as TransactionRecurrente['frequence'])} className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary">
                {FREQUENCES.map((f) => <option key={f.valeur} value={f.valeur}>{f.label}</option>)}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Prochaine exécution</label>
                <input type="date" required value={prochaineExecution} onChange={(e) => setProchaineExecution(e.target.value)} className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Fin (facultatif)</label>
                <input type="date" value={dateFin} min={prochaineExecution} onChange={(e) => setDateFin(e.target.value)} className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
            </div>

            {error && <p className="text-sm text-destructive text-center">{error}</p>}

            <div className="pt-2 flex gap-3">
              <button type="button" onClick={onClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">Annuler</button>
              <button type="submit" disabled={isSubmitting || !idCompte || !idCategorie} className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50">
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>{modeEdition ? 'Enregistrer' : 'Planifier'}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
