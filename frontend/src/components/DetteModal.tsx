import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { CompteFinancier } from '../types';

interface DetteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  comptes: CompteFinancier[];
}

// Mémorise le dernier compte utilisé (par appareil) pour le présélectionner
// au prochain ajout — même principe que TransactionModal.
const CLE_DERNIER_COMPTE = 'mynkap_dernier_compte_dette';

const MONTANTS_RAPIDES = [5000, 10000, 25000, 50000, 100000];

const formatDateLocale = (d: Date): string => {
  const annee = d.getFullYear();
  const mois = String(d.getMonth() + 1).padStart(2, '0');
  const jour = String(d.getDate()).padStart(2, '0');
  return `${annee}-${mois}-${jour}`;
};

// Décalages courants pour une échéance — évite d'ouvrir le sélecteur de
// date pour le cas le plus fréquent (une échéance approximative plutôt
// qu'un jour précis en tête). Les dates cibles sont calculées une seule
// fois au chargement du module (comme AUJOURDHUI dans TransactionModal),
// jamais pendant le rendu — un composant React doit rester pur.
const MAINTENANT_MS = Date.now();
const ECHEANCES_RAPIDES: { date: string; labelKey: string }[] = [
  { date: formatDateLocale(new Date(MAINTENANT_MS + 7 * 24 * 60 * 60 * 1000)), labelKey: 'modals.dette.due_in_week' },
  { date: formatDateLocale(new Date(MAINTENANT_MS + 30 * 24 * 60 * 60 * 1000)), labelKey: 'modals.dette.due_in_month' },
  { date: formatDateLocale(new Date(MAINTENANT_MS + 90 * 24 * 60 * 60 * 1000)), labelKey: 'modals.dette.due_in_3months' },
];

export const DetteModal: React.FC<DetteModalProps> = ({ isOpen, onClose, onSuccess, comptes }) => {
  const { t } = useTranslation();
  const [type, setType] = useState<'DETTE' | 'CREANCE'>('DETTE');
  const [nom, setNom] = useState('');
  const [montantTotal, setMontantTotal] = useState('');
  const [personneImpliquee, setPersonneImpliquee] = useState('');
  const [dateEcheance, setDateEcheance] = useState('');
  const [idCompte, setIdCompte] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Présélectionne le compte dès qu'il est disponible — la liste des
    // comptes se charge de façon asynchrone après le montage de la modale,
    // donc l'état initial ne peut pas s'y fier directement. Le dernier
    // compte utilisé pour une dette/créance est privilégié s'il existe
    // toujours, sinon on retombe sur le premier.
    if (isOpen && comptes.length > 0 && !idCompte) {
      let dernierCompte: string | null = null;
      try {
        dernierCompte = localStorage.getItem(CLE_DERNIER_COMPTE);
      } catch {
        // Stockage indisponible (navigation privée...) : retombe sur le premier compte.
      }
      const dernierToujoursValide = dernierCompte && comptes.some((c) => String(c.id_compte) === dernierCompte);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIdCompte(dernierToujoursValide ? dernierCompte! : String(comptes[0].id_compte));
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
      try {
        localStorage.setItem(CLE_DERNIER_COMPTE, idCompte);
      } catch {
        // Purement un confort, jamais bloquant.
      }
      setNom('');
      setMontantTotal('');
      setPersonneImpliquee('');
      setDateEcheance('');
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.dette.error_create'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">{t('debts.declare')}</h3>
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
              {t('modals.dette.type_debt')}
            </button>
            <button
              type="button"
              onClick={() => setType('CREANCE')}
              className={`py-2.5 rounded-lg text-xs font-bold transition-all ${
                type === 'CREANCE' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {t('modals.dette.type_claim')}
            </button>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.dette.name_label')}</label>
            <input
              type="text"
              required
              placeholder={t('modals.dette.name_placeholder')}
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.dette.total_amount_label')}</label>
            <input
              type="number"
              required
              min={1}
              placeholder="ex: 50000"
              value={montantTotal}
              onChange={(e) => setMontantTotal(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <div className="flex flex-wrap gap-1.5">
              {MONTANTS_RAPIDES.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMontantTotal(String(m))}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-colors ${
                    montantTotal === String(m)
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'border-border text-muted-foreground hover:border-primary/50 hover:text-foreground'
                  }`}
                >
                  {m.toLocaleString('fr-FR')}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.dette.account_label')}</label>
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
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.dette.person_label')}</label>
            <input
              type="text"
              placeholder="ex: Paul"
              value={personneImpliquee}
              onChange={(e) => setPersonneImpliquee(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.dette.due_date_label')}</label>
            <input
              type="date"
              value={dateEcheance}
              onChange={(e) => setDateEcheance(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <div className="flex flex-wrap gap-1.5">
              {ECHEANCES_RAPIDES.map(({ date: dateCible, labelKey }) => (
                <button
                  key={labelKey}
                  type="button"
                  onClick={() => setDateEcheance(dateCible)}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-colors ${
                    dateEcheance === dateCible
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'border-border text-muted-foreground hover:border-primary/50 hover:text-foreground'
                  }`}
                >
                  {t(labelKey)}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-sm text-destructive text-center">{error}</p>}

          <div className="pt-2 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !idCompte}
              className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>{t('common.save')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
