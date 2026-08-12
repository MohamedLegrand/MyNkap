import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Loader2, User } from 'lucide-react';
import { api } from '../services/api';

interface ProfileSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ClientAvecProfil {
  first_name: string;
  last_name: string;
  email: string;
  profile: { devise: string; langue: string; avatar: string | null } | null;
}

const DEVISES = ['XAF', 'EUR', 'USD'];
const LANGUES: { valeur: string; label: string }[] = [
  { valeur: 'fr', label: 'Français' },
  { valeur: 'en', label: 'English' },
];

export const ProfileSettingsModal: React.FC<ProfileSettingsModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [succes, setSucces] = useState(false);
  const [identite, setIdentite] = useState<{ nom: string; email: string } | null>(null);
  const [devise, setDevise] = useState('XAF');
  const [langue, setLangue] = useState('fr');
  const [avatar, setAvatar] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    // Chargement à l'ouverture — pas une synchronisation d'état dérivé.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsLoading(true);
    setError(null);
    setSucces(false);
    api
      .request<ClientAvecProfil>('/auth/me')
      .then((data) => {
        setIdentite({ nom: `${data.first_name} ${data.last_name}`, email: data.email });
        if (data.profile) {
          setDevise(data.profile.devise);
          setLangue(data.profile.langue);
          setAvatar(data.profile.avatar ?? '');
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : t('modals.profile.error_load')))
      .finally(() => setIsLoading(false));
  }, [isOpen, t]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSucces(false);
    setIsSubmitting(true);
    try {
      await api.request('/auth/profile', {
        method: 'PUT',
        body: JSON.stringify({ devise, langue, avatar: avatar || null }),
      });
      setSucces(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.profile.error_save'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-sm rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight flex items-center gap-2">
            <User className="h-5 w-5 text-primary" />
            <span>{t('dashboard.my_profile')}</span>
          </h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-14">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {identite && (
              <div className="p-3 rounded-xl bg-muted/40 border border-border text-xs">
                <p className="font-bold text-foreground">{identite.nom}</p>
                <p className="text-muted-foreground">{identite.email}</p>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('modals.profile.currency_label')}</label>
              <select value={devise} onChange={(e) => setDevise(e.target.value)} className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary">
                {DEVISES.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('modals.profile.language_label')}</label>
              <select value={langue} onChange={(e) => setLangue(e.target.value)} className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary">
                {LANGUES.map((l) => <option key={l.valeur} value={l.valeur}>{l.label}</option>)}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('modals.profile.avatar_label')}</label>
              <input type="text" value={avatar} onChange={(e) => setAvatar(e.target.value)} placeholder="https://..." className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>

            {error && <p className="text-sm text-destructive text-center">{error}</p>}
            {succes && <p className="text-sm text-forest-600 dark:text-forest-400 text-center font-semibold">{t('modals.profile.updated')}</p>}

            <div className="pt-2 flex gap-3">
              <button type="button" onClick={onClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">{t('common.close')}</button>
              <button type="submit" disabled={isSubmitting} className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50">
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>{t('common.save')}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
