import React, { useState } from 'react';
import { X, ArrowDownCircle, ArrowUpCircle, Wallet, Tag, FileText, Loader2 } from 'lucide-react';

interface TransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const TransactionModal: React.FC<TransactionModalProps> = ({ isOpen, onClose }) => {
  const [type, setType] = useState<'DEPENSE' | 'REVENU'>('DEPENSE');
  const [montant, setMontant] = useState('');
  const [compte, setCompte] = useState('1'); // 1 = Orange Money
  const [categorie, setCategorie] = useState('Transport');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Simulation d'enregistrement
    setTimeout(() => {
      setIsSubmitting(false);
      onClose();
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header Modal */}
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">Nouvelle Opération Financière</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Selector Type (DEPENSE / REVENU) */}
          <div className="grid grid-cols-2 gap-3 p-1 bg-muted rounded-xl">
            <button
              type="button"
              onClick={() => setType('DEPENSE')}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition-all ${
                type === 'DEPENSE'
                  ? 'bg-destructive text-destructive-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <ArrowDownCircle className="h-4 w-4" />
              <span>Dépense</span>
            </button>
            <button
              type="button"
              onClick={() => setType('REVENU')}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition-all ${
                type === 'REVENU'
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <ArrowUpCircle className="h-4 w-4" />
              <span>Revenu / Dépôt</span>
            </button>
          </div>

          {/* Montant (XAF) */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Montant (FCFA / XAF)</label>
            <div className="relative">
              <input
                type="number"
                required
                min={100}
                step={50}
                placeholder="ex: 15000"
                value={montant}
                onChange={(e) => setMontant(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-4 py-3 text-lg font-bold focus:outline-none focus:ring-2 focus:ring-primary pr-16"
              />
              <span className="absolute right-4 top-3.5 text-xs font-black text-muted-foreground uppercase">XAF</span>
            </div>
          </div>

          {/* Compte Source */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
              <Wallet className="h-3.5 w-3.5" />
              <span>Compte Financier</span>
            </label>
            <select
              value={compte}
              onChange={(e) => setCompte(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="1">Orange Money (+237 699...)</option>
              <option value="2">MTN Mobile Money (+237 677...)</option>
              <option value="3">Afriland First Bank (Compte Courant)</option>
              <option value="4">Portefeuille Cash / Espèces</option>
            </select>
          </div>

          {/* Catégorie */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
              <Tag className="h-3.5 w-3.5" />
              <span>Catégorie</span>
            </label>
            <select
              value={categorie}
              onChange={(e) => setCategorie(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="Transport">Transport (Taxi, Moto, Essence)</option>
              <option value="Alimentation">Alimentation & Marché</option>
              <option value="Factures">Factures (Eneo, Camwater, Canal+)</option>
              <option value="Loisirs">Loisirs & Restauration</option>
              <option value="Salaire">Salaire & Virement Pro</option>
              <option value="Autre">Autre dépense</option>
            </select>
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              <span>Note / Description (facultatif)</span>
            </label>
            <input
              type="text"
              placeholder="ex: Taxi pour la réunion de 10h"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Action Footer */}
          <div className="pt-2 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>{isSubmitting ? 'Enregistrement...' : 'Valider'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
