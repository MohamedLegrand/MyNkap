import React, { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { Categorie, CompteFinancier, TemplateTransaction } from '../types';

interface TemplateTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  comptes: CompteFinancier[];
  categories: Categorie[];
  // Présent = mode édition (PUT) ; absent/null = création.
  template?: TemplateTransaction | null;
}

export const TemplateTransactionModal: React.FC<TemplateTransactionModalProps> = ({
  isOpen, onClose, onSuccess, comptes, categories, template = null,
}) => {
  const modeEdition = template !== null;

  const [nom, setNom] = useState('');
  const [type, setType] = useState<'DEPENSE' | 'REVENU'>('DEPENSE');
  const [idCompte, setIdCompte] = useState('');
  const [idCategorie, setIdCategorie] = useState('');
  const [montant, setMontant] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const categoriesFiltrees = categories.filter((c) => c.type === type && c.est_actif);

  useEffect(() => {
    if (!isOpen) return;
    if (template) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsLoadingDetail(true);
      setError(null);
      api
        .request<TemplateTransaction>(`/templates/${template.id_template}`)
        .then((frais) => {
          setNom(frais.nom);
          setType(frais.type);
          setIdCompte(String(frais.id_compte));
          setIdCategorie(String(frais.id_categorie));
          setMontant(String(frais.montant));
          setDescription(frais.description ?? '');
        })
        .catch((err) => setError(err instanceof Error ? err.message : 'Impossible de charger ce modèle.'))
        .finally(() => setIsLoadingDetail(false));
    } else {
      setNom('');
      setType('DEPENSE');
      setMontant('');
      setDescription('');
      if (comptes.length > 0) setIdCompte(String(comptes[0].id_compte));
    }
  }, [isOpen, template, comptes]);

  useEffect(() => {
    // Resynchronise la catégorie si le type change et que la catégorie
    // actuelle ne correspond plus — dépend d'une action utilisateur, pas
    // une synchronisation d'état dérivé d'un rendu précédent.
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
      if (modeEdition && template) {
        await api.request(`/templates/${template.id_template}`, {
          method: 'PUT',
          body: JSON.stringify({
            id_compte: Number(idCompte),
            id_categorie: Number(idCategorie),
            nom,
            montant: Number(montant),
            type,
            description: description || null,
          }),
        });
      } else {
        await api.request('/templates', {
          method: 'POST',
          body: JSON.stringify({
            id_compte: Number(idCompte),
            id_categorie: Number(idCategorie),
            nom,
            montant: Number(montant),
            type,
            description: description || null,
          }),
        });
      }
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : `${modeEdition ? 'Modification' : 'Création'} du modèle impossible.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">{modeEdition ? 'Modifier le modèle' : 'Créer un modèle de transaction'}</h3>
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
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Nom du modèle</label>
              <input type="text" required placeholder="ex: Course marché du samedi" value={nom} onChange={(e) => setNom(e.target.value)} className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>

            <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
              <button type="button" onClick={() => setType('DEPENSE')} className={`py-2.5 rounded-lg text-xs font-bold transition-all ${type === 'DEPENSE' ? 'bg-destructive text-destructive-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}>
                Dépense
              </button>
              <button type="button" onClick={() => setType('REVENU')} className={`py-2.5 rounded-lg text-xs font-bold transition-all ${type === 'REVENU' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}>
                Revenu
              </button>
            </div>

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

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Montant (XAF)</label>
              <input type="number" required min={1} value={montant} onChange={(e) => setMontant(e.target.value)} placeholder="ex: 8000" className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Description (facultatif)</label>
              <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>

            {error && <p className="text-sm text-destructive text-center">{error}</p>}

            <div className="pt-2 flex gap-3">
              <button type="button" onClick={onClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">Annuler</button>
              <button type="submit" disabled={isSubmitting || !idCompte || !idCategorie} className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50">
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>{modeEdition ? 'Enregistrer' : 'Créer le modèle'}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
