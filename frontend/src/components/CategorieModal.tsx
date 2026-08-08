import React, { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { Categorie } from '../types';
import { ICONES_CATEGORIE } from '../utils/categorieIcons';
import { COULEURS_CATEGORIE, COULEUR_CATEGORIE_PAR_DEFAUT } from '../utils/categorieColors';

const ICONE_PAR_DEFAUT = 'more-horizontal';

interface CategorieModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  // Présent = mode édition (PUT sur cette catégorie) ; absent/null = création.
  categorie?: Categorie | null;
}

export const CategorieModal: React.FC<CategorieModalProps> = ({ isOpen, onClose, onSuccess, categorie = null }) => {
  const modeEdition = categorie !== null;

  const [nom, setNom] = useState('');
  const [type, setType] = useState<'DEPENSE' | 'REVENU'>('DEPENSE');
  const [icone, setIcone] = useState(ICONE_PAR_DEFAUT);
  const [couleur, setCouleur] = useState(COULEUR_CATEGORIE_PAR_DEFAUT);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Relit la catégorie depuis le serveur à l'ouverture plutôt que de se
    // fier à la liste locale (potentiellement périmée) — pas une
    // synchronisation d'état dérivé d'un rendu précédent.
    if (isOpen && categorie) {
      api
        .request<Categorie>(`/categories/${categorie.id_categorie}`)
        .then((fraiche) => {
          setNom(fraiche.nom);
          setType(fraiche.type);
          setIcone(fraiche.icone || ICONE_PAR_DEFAUT);
          setCouleur(fraiche.couleur || COULEUR_CATEGORIE_PAR_DEFAUT);
        })
        .catch(() => {
          setNom(categorie.nom);
          setType(categorie.type);
          setIcone(categorie.icone || ICONE_PAR_DEFAUT);
          setCouleur(categorie.couleur || COULEUR_CATEGORIE_PAR_DEFAUT);
        });
    } else if (isOpen) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setNom('');
      setType('DEPENSE');
      setIcone(ICONE_PAR_DEFAUT);
      setCouleur(COULEUR_CATEGORIE_PAR_DEFAUT);
    }
  }, [isOpen, categorie]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      if (modeEdition && categorie) {
        await api.request(`/categories/${categorie.id_categorie}`, { method: 'PUT', body: JSON.stringify({ nom, icone, couleur }) });
      } else {
        await api.request('/categories', { method: 'POST', body: JSON.stringify({ nom, type, icone, couleur }) });
      }
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : `${modeEdition ? 'Modification' : 'Création'} de la catégorie impossible.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">{modeEdition ? 'Modifier catégorie' : 'Créer catégorie'}</h3>
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
            <label className="text-xs font-semibold text-muted-foreground">
              Type de catégorie{modeEdition && ' (non modifiable)'}
            </label>
            <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
              <button
                type="button"
                disabled={modeEdition}
                onClick={() => setType('DEPENSE')}
                className={`py-2.5 rounded-lg text-xs font-bold transition-all disabled:opacity-60 disabled:cursor-not-allowed ${
                  type === 'DEPENSE' ? 'bg-destructive text-destructive-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Dépense
              </button>
              <button
                type="button"
                disabled={modeEdition}
                onClick={() => setType('REVENU')}
                className={`py-2.5 rounded-lg text-xs font-bold transition-all disabled:opacity-60 disabled:cursor-not-allowed ${
                  type === 'REVENU' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Revenu
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Icône</label>
            <div className="grid grid-cols-7 gap-2 max-h-40 overflow-y-auto p-1">
              {Object.entries(ICONES_CATEGORIE).map(([slug, Icon]) => (
                <button
                  key={slug}
                  type="button"
                  title={slug}
                  onClick={() => setIcone(slug)}
                  className={`aspect-square rounded-xl flex items-center justify-center border transition-all ${
                    icone === slug
                      ? 'border-primary bg-primary/10 text-primary ring-2 ring-primary/40'
                      : 'border-border text-muted-foreground hover:bg-muted hover:text-foreground'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Couleur</label>
            <div className="flex flex-wrap gap-2 p-1">
              {COULEURS_CATEGORIE.map((c) => (
                <button
                  key={c.valeur}
                  type="button"
                  title={c.label}
                  onClick={() => setCouleur(c.valeur)}
                  className={`h-8 w-8 rounded-full transition-all ${
                    couleur === c.valeur ? 'ring-2 ring-offset-2 ring-offset-card ring-foreground' : 'hover:scale-110'
                  }`}
                  style={{ backgroundColor: c.valeur }}
                />
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
              <span>{modeEdition ? 'Enregistrer' : 'Créer catégorie'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
