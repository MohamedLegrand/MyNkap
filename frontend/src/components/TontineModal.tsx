import React, { useState } from 'react';
import { X, Loader2, Plus, Trash2 } from 'lucide-react';
import { api } from '../services/api';

interface TontineModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface MembreForm {
  nom: string;
  telephone: string;
}

const MEMBRE_VIDE: MembreForm = { nom: '', telephone: '' };

export const TontineModal: React.FC<TontineModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [nom, setNom] = useState('');
  const [montantCotisation, setMontantCotisation] = useState('');
  const [frequence, setFrequence] = useState<'HEBDOMADAIRE' | 'MENSUELLE'>('MENSUELLE');
  const [dateDebut, setDateDebut] = useState(new Date().toISOString().slice(0, 10));
  const [membres, setMembres] = useState<MembreForm[]>([{ ...MEMBRE_VIDE }, { ...MEMBRE_VIDE }]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const ajouterMembre = () => setMembres((prev) => [...prev, { ...MEMBRE_VIDE }]);
  const retirerMembre = (index: number) => setMembres((prev) => prev.filter((_, i) => i !== index));
  const modifierMembre = (index: number, champ: keyof MembreForm, valeur: string) =>
    setMembres((prev) => prev.map((m, i) => (i === index ? { ...m, [champ]: valeur } : m)));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const membresValides = membres.filter((m) => m.nom.trim());
    if (membresValides.length < 2) {
      setError('Au moins 2 membres sont requis pour former une tontine.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await api.request('/tontines', {
        method: 'POST',
        body: JSON.stringify({
          nom,
          montant_cotisation: Number(montantCotisation),
          devise: 'XAF',
          frequence,
          date_debut: dateDebut,
          membres: membresValides.map((m) => ({ nom: m.nom, telephone: m.telephone || undefined })),
        }),
      });
      setNom('');
      setMontantCotisation('');
      setFrequence('MENSUELLE');
      setDateDebut(new Date().toISOString().slice(0, 10));
      setMembres([{ ...MEMBRE_VIDE }, { ...MEMBRE_VIDE }]);
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Création de la tontine impossible.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden max-h-[90vh] flex flex-col animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40 shrink-0">
          <h3 className="text-lg font-bold tracking-tight">Créer une tontine</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Nom de la tontine</label>
            <input
              type="text"
              required
              placeholder="ex: Tontine du quartier"
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Cotisation par membre (XAF)</label>
              <input
                type="number"
                required
                min={1}
                placeholder="ex: 5000"
                value={montantCotisation}
                onChange={(e) => setMontantCotisation(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Date du 1er tour</label>
              <input
                type="date"
                required
                value={dateDebut}
                onChange={(e) => setDateDebut(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Fréquence des tours</label>
            <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
              <button
                type="button"
                onClick={() => setFrequence('HEBDOMADAIRE')}
                className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                  frequence === 'HEBDOMADAIRE' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Hebdomadaire
              </button>
              <button
                type="button"
                onClick={() => setFrequence('MENSUELLE')}
                className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                  frequence === 'MENSUELLE' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Mensuelle
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-muted-foreground">
                Membres (ordre de réception de la cagnotte)
              </label>
              <button
                type="button"
                onClick={ajouterMembre}
                className="text-[11px] font-bold text-primary hover:underline flex items-center gap-1"
              >
                <Plus className="h-3 w-3" />
                <span>Ajouter</span>
              </button>
            </div>
            <div className="space-y-2">
              {membres.map((m, index) => (
                <div key={index} className="flex items-center gap-2">
                  <span className="text-[11px] font-bold text-muted-foreground w-4 shrink-0">{index + 1}</span>
                  <input
                    type="text"
                    required
                    placeholder="Nom du membre"
                    value={m.nom}
                    onChange={(e) => modifierMembre(index, 'nom', e.target.value)}
                    className="flex-1 bg-background border border-border rounded-lg px-2.5 py-2 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <input
                    type="text"
                    placeholder="Téléphone (facultatif)"
                    value={m.telephone}
                    onChange={(e) => modifierMembre(index, 'telephone', e.target.value)}
                    className="w-32 bg-background border border-border rounded-lg px-2.5 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <button
                    type="button"
                    onClick={() => retirerMembre(index)}
                    disabled={membres.length <= 2}
                    title="Retirer ce membre"
                    className="p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-muted-foreground transition-colors shrink-0"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
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
              <span>Créer la tontine</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
