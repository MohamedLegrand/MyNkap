import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Camera, Trash2, Loader2, KeyRound, Palette, Crown, Moon, Sun, UserCircle2, Sparkles, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store';
import { Avatar } from './Avatar';
import { useDarkMode } from '../hooks/useDarkMode';
import type { Plan, Abonnement } from '../types';

interface SettingsSectionProps {
  plan?: Plan | null;
  abonnement?: Abonnement | null;
  onOpenUpgradeModal: () => void;
}

interface ClientAvecProfil {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  profile: { devise: string; langue: string; avatar: string | null } | null;
}

const DEVISES = ['XAF', 'EUR', 'USD'];
const LANGUES: { valeur: string; label: string }[] = [
  { valeur: 'fr', label: 'Français' },
  { valeur: 'en', label: 'English' },
];
const TYPES_PHOTO_ACCEPTES = ['image/jpeg', 'image/png', 'image/webp'];
const TAILLE_MAX_PHOTO = 3 * 1024 * 1024; // 3 Mo, même limite que le backend

const CARD = 'bg-card p-6 rounded-2xl border border-border shadow-sm space-y-4';
const INPUT = 'w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary';
const LABEL = 'text-xs font-semibold text-muted-foreground';
const BTN_PRIMARY = 'py-2.5 px-5 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50';

// Même principe que DashboardLayout.joursRestants : fonction de module
// séparée (pas un appel Date.now() direct dans le corps du composant) pour
// rester une lecture pure au sens du linter react-hooks/purity.
const joursRestantsAbonnement = (dateFin: string): number =>
  Math.max(0, Math.ceil((new Date(dateFin).getTime() - Date.now()) / 86_400_000));

// Page complète (pas une modale) : mêmes sections qu'un centre de
// paramètres classique — photo, identité, préférences, sécurité,
// abonnement — chacune avec son propre enregistrement indépendant.
export const SettingsSection: React.FC<SettingsSectionProps> = ({ plan, abonnement, onOpenUpgradeModal }) => {
  const { t } = useTranslation();
  const { theme, toggleTheme } = useDarkMode();
  const client = useAuthStore((state) => state.client);
  const setClient = useAuthStore((state) => state.setClient);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [devise, setDevise] = useState('XAF');
  const [langue, setLangue] = useState('fr');
  const [avatar, setAvatar] = useState<string | null>(null);

  const [isPhotoBusy, setIsPhotoBusy] = useState(false);
  const [photoError, setPhotoError] = useState<string | null>(null);

  const [isInfoSaving, setIsInfoSaving] = useState(false);
  const [infoSuccess, setInfoSuccess] = useState(false);
  const [infoError, setInfoError] = useState<string | null>(null);

  const [isPrefsSaving, setIsPrefsSaving] = useState(false);
  const [prefsSuccess, setPrefsSuccess] = useState(false);
  const [prefsError, setPrefsError] = useState<string | null>(null);

  const [motDePasseActuel, setMotDePasseActuel] = useState('');
  const [nouveauMotDePasse, setNouveauMotDePasse] = useState('');
  const [confirmNouveauMotDePasse, setConfirmNouveauMotDePasse] = useState('');
  const [isPasswordSaving, setIsPasswordSaving] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  useEffect(() => {
    // Chargement au montage — pas une synchronisation d'état dérivé.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsLoading(true);
    setLoadError(null);
    api
      .request<ClientAvecProfil>('/auth/me')
      .then((data) => {
        setEmail(data.email);
        setFirstName(data.first_name);
        setLastName(data.last_name);
        setPhone(data.phone);
        if (data.profile) {
          setDevise(data.profile.devise);
          setLangue(data.profile.langue);
          setAvatar(data.profile.avatar ?? null);
        }
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : t('modals.profile.error_load')))
      .finally(() => setIsLoading(false));
  }, [t]);

  const handleChoisirPhoto = () => fileInputRef.current?.click();

  const handleFichierChoisi = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fichier = e.target.files?.[0];
    e.target.value = '';
    if (!fichier) return;

    setPhotoError(null);
    if (!TYPES_PHOTO_ACCEPTES.includes(fichier.type)) {
      setPhotoError(t('modals.profile.photo_error_type'));
      return;
    }
    if (fichier.size > TAILLE_MAX_PHOTO) {
      setPhotoError(t('modals.profile.photo_error_size'));
      return;
    }

    setIsPhotoBusy(true);
    try {
      const formData = new FormData();
      formData.append('photo', fichier);
      const profil = await api.request<{ avatar: string | null; devise: string; langue: string }>('/auth/profile/photo', {
        method: 'POST',
        body: formData,
      });
      setAvatar(profil.avatar);
      if (client) setClient({ ...client, profile: profil });
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : t('modals.profile.error_save'));
    } finally {
      setIsPhotoBusy(false);
    }
  };

  const handleSupprimerPhoto = async () => {
    setPhotoError(null);
    setIsPhotoBusy(true);
    try {
      const profil = await api.request<{ avatar: string | null; devise: string; langue: string }>('/auth/profile/photo', {
        method: 'DELETE',
      });
      setAvatar(null);
      if (client) setClient({ ...client, profile: profil });
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : t('modals.profile.error_save'));
    } finally {
      setIsPhotoBusy(false);
    }
  };

  const handleSubmitInfo = async (e: React.FormEvent) => {
    e.preventDefault();
    setInfoError(null);
    setInfoSuccess(false);
    setIsInfoSaving(true);
    try {
      await api.request('/auth/me', {
        method: 'PUT',
        body: JSON.stringify({ first_name: firstName, last_name: lastName, phone }),
      });
      if (client) setClient({ ...client, first_name: firstName, last_name: lastName, phone });
      setInfoSuccess(true);
    } catch (err) {
      setInfoError(err instanceof Error ? err.message : t('modals.profile.error_save'));
    } finally {
      setIsInfoSaving(false);
    }
  };

  const handleSubmitPrefs = async (e: React.FormEvent) => {
    e.preventDefault();
    setPrefsError(null);
    setPrefsSuccess(false);
    setIsPrefsSaving(true);
    try {
      await api.request('/auth/profile', {
        method: 'PUT',
        body: JSON.stringify({ devise, langue }),
      });
      if (client) setClient({ ...client, profile: { devise, langue, avatar } });
      setPrefsSuccess(true);
    } catch (err) {
      setPrefsError(err instanceof Error ? err.message : t('modals.profile.error_save'));
    } finally {
      setIsPrefsSaving(false);
    }
  };

  const handleSubmitPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(false);
    if (nouveauMotDePasse !== confirmNouveauMotDePasse) {
      setPasswordError(t('dashboard.settings.password_mismatch'));
      return;
    }
    setIsPasswordSaving(true);
    try {
      await api.request('/auth/change-password', {
        method: 'PUT',
        body: JSON.stringify({ mot_de_passe_actuel: motDePasseActuel, nouveau_mot_de_passe: nouveauMotDePasse }),
      });
      setPasswordSuccess(true);
      setMotDePasseActuel('');
      setNouveauMotDePasse('');
      setConfirmNouveauMotDePasse('');
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : t('modals.profile.error_save'));
    } finally {
      setIsPasswordSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const LABEL_PLAN: Record<string, string> = {
    GRATUIT: t('dashboard.plan_free'),
    ESSENTIEL: t('dashboard.plan_standard'),
    PREMIUM: t('dashboard.plan_premium'),
  };
  const nomPlan = plan?.nom ?? 'GRATUIT';
  const estEnEssai = abonnement?.statut === 'ESSAI' && !!abonnement.date_fin;
  const joursRestants = abonnement?.date_fin ? joursRestantsAbonnement(abonnement.date_fin) : 0;
  const dejaAuMaximum = nomPlan === 'PREMIUM' && !estEnEssai;

  return (
    <div className="space-y-6 max-w-3xl">
      {loadError && (
        <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm">{loadError}</div>
      )}

      {/* Photo de profil */}
      <div className={CARD}>
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <UserCircle2 className="h-5 w-5 text-primary" />
          <span>{t('dashboard.settings.photo_title')}</span>
        </h3>
        <div className="flex items-center gap-5">
          <div className="relative shrink-0">
            <Avatar src={avatar} nom={firstName} className="h-20 w-20 text-2xl" />
            {isPhotoBusy && (
              <div className="absolute inset-0 rounded-xl bg-background/70 flex items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
            )}
          </div>
          <div className="space-y-2">
            <input
              ref={fileInputRef}
              type="file"
              accept={TYPES_PHOTO_ACCEPTES.join(',')}
              onChange={handleFichierChoisi}
              className="hidden"
            />
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleChoisirPhoto}
                disabled={isPhotoBusy}
                className="flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline disabled:opacity-50"
              >
                <Camera className="h-3.5 w-3.5" />
                {t('modals.profile.change_photo')}
              </button>
              {avatar && (
                <button
                  type="button"
                  onClick={handleSupprimerPhoto}
                  disabled={isPhotoBusy}
                  className="flex items-center gap-1.5 text-xs font-semibold text-destructive hover:underline disabled:opacity-50"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  {t('modals.profile.remove_photo')}
                </button>
              )}
            </div>
            {photoError && <p className="text-xs text-destructive">{photoError}</p>}
          </div>
        </div>
      </div>

      {/* Informations personnelles */}
      <form onSubmit={handleSubmitInfo} className={CARD}>
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <UserCircle2 className="h-5 w-5 text-primary" />
          <span>{t('dashboard.settings.info_title')}</span>
        </h3>
        <p className="text-xs text-muted-foreground">{email}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className={LABEL}>{t('modals.profile.firstname_label')}</label>
            <input type="text" value={firstName} onChange={(e) => setFirstName(e.target.value)} required className={INPUT} />
          </div>
          <div className="space-y-1.5">
            <label className={LABEL}>{t('modals.profile.lastname_label')}</label>
            <input type="text" value={lastName} onChange={(e) => setLastName(e.target.value)} required className={INPUT} />
          </div>
        </div>
        <div className="space-y-1.5">
          <label className={LABEL}>{t('modals.profile.phone_label')}</label>
          <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} required className={INPUT} />
        </div>
        {infoError && <p className="text-sm text-destructive">{infoError}</p>}
        {infoSuccess && <p className="text-sm text-forest-600 dark:text-forest-400 font-semibold">{t('modals.profile.updated')}</p>}
        <button type="submit" disabled={isInfoSaving} className={BTN_PRIMARY}>
          {isInfoSaving && <Loader2 className="h-4 w-4 animate-spin" />}
          <span>{t('common.save')}</span>
        </button>
      </form>

      {/* Préférences */}
      <form onSubmit={handleSubmitPrefs} className={CARD}>
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <Palette className="h-5 w-5 text-primary" />
          <span>{t('dashboard.settings.preferences_title')}</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className={LABEL}>{t('modals.profile.currency_label')}</label>
            <select value={devise} onChange={(e) => setDevise(e.target.value)} className={INPUT}>
              {DEVISES.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className={LABEL}>{t('modals.profile.language_label')}</label>
            <select value={langue} onChange={(e) => setLangue(e.target.value)} className={INPUT}>
              {LANGUES.map((l) => <option key={l.valeur} value={l.valeur}>{l.label}</option>)}
            </select>
          </div>
        </div>
        <div className="space-y-1.5">
          <label className={LABEL}>{t('dashboard.settings.appearance_label')}</label>
          <button
            type="button"
            onClick={toggleTheme}
            className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl border border-border bg-background text-sm font-semibold hover:bg-muted transition-colors"
          >
            <span className="flex items-center gap-2">
              {theme === 'light' ? <Sun className="h-4 w-4 text-secondary" /> : <Moon className="h-4 w-4 text-secondary" />}
              {theme === 'light' ? t('dashboard.settings.theme_light') : t('dashboard.settings.theme_dark')}
            </span>
            <span className="text-xs font-bold text-primary">{t('dashboard.settings.theme_toggle')}</span>
          </button>
        </div>
        {prefsError && <p className="text-sm text-destructive">{prefsError}</p>}
        {prefsSuccess && <p className="text-sm text-forest-600 dark:text-forest-400 font-semibold">{t('modals.profile.updated')}</p>}
        <button type="submit" disabled={isPrefsSaving} className={BTN_PRIMARY}>
          {isPrefsSaving && <Loader2 className="h-4 w-4 animate-spin" />}
          <span>{t('common.save')}</span>
        </button>
      </form>

      {/* Sécurité */}
      <form onSubmit={handleSubmitPassword} className={CARD}>
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-primary" />
          <span>{t('dashboard.settings.security_title')}</span>
        </h3>
        <div className="space-y-1.5">
          <label className={LABEL}>{t('dashboard.settings.current_password_label')}</label>
          <input type="password" value={motDePasseActuel} onChange={(e) => setMotDePasseActuel(e.target.value)} required autoComplete="current-password" className={INPUT} />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className={LABEL}>{t('dashboard.settings.new_password_label')}</label>
            <input type="password" value={nouveauMotDePasse} onChange={(e) => setNouveauMotDePasse(e.target.value)} required minLength={8} autoComplete="new-password" className={INPUT} />
          </div>
          <div className="space-y-1.5">
            <label className={LABEL}>{t('dashboard.settings.confirm_new_password_label')}</label>
            <input type="password" value={confirmNouveauMotDePasse} onChange={(e) => setConfirmNouveauMotDePasse(e.target.value)} required minLength={8} autoComplete="new-password" className={INPUT} />
          </div>
        </div>
        {passwordError && <p className="text-sm text-destructive">{passwordError}</p>}
        {passwordSuccess && <p className="text-sm text-forest-600 dark:text-forest-400 font-semibold">{t('dashboard.settings.password_updated')}</p>}
        <button type="submit" disabled={isPasswordSaving} className={BTN_PRIMARY}>
          {isPasswordSaving && <Loader2 className="h-4 w-4 animate-spin" />}
          <span>{t('dashboard.settings.change_password_button')}</span>
        </button>
      </form>

      {/* Abonnement */}
      <div className={CARD}>
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <Crown className="h-5 w-5 text-primary" />
          <span>{t('dashboard.settings.subscription_title')}</span>
        </h3>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <span className="inline-flex items-center gap-1 text-sm font-bold text-primary bg-primary/10 px-3 py-1 rounded-full border border-primary/20">
              <Crown className="h-4 w-4" />
              <span>{LABEL_PLAN[nomPlan] ?? nomPlan}</span>
            </span>
            {estEnEssai && abonnement?.date_fin && (
              <p className="text-xs text-muted-foreground mt-2">
                {t('dashboard.trial_prefix')}{' '}
                <strong className="text-foreground">{t('dashboard.days_count', { count: joursRestants })}</strong>.
              </p>
            )}
          </div>
          {dejaAuMaximum ? (
            <p className="text-sm font-semibold text-forest-600 dark:text-forest-400 flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4" />
              <span>{t('dashboard.all_unlocked')}</span>
            </p>
          ) : (
            <button
              onClick={onOpenUpgradeModal}
              className="text-sm font-semibold py-2 px-4 rounded-xl bg-primary/10 hover:bg-primary/20 text-primary transition-colors flex items-center gap-1.5"
            >
              <Sparkles className="h-4 w-4 text-primary" />
              <span>{estEnEssai ? t('dashboard.keep_access') : t('dashboard.upgrade')}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
