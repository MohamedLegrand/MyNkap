import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Loader2, Upload, Ban } from 'lucide-react';
import { api } from '../services/api';
import type { CompteFinancier } from '../types';
import { LOGOS_PREDEFINIS, TAILLE_MAX_LOGO_OCTETS, TYPES_LOGO_IMPORTE, obtenirLogoCompte } from '../utils/logosComptes';

interface CompteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  // Présent = mode édition (PATCH sur ce compte) ; absent/null = création.
  compte?: CompteFinancier | null;
}

export const CompteModal: React.FC<CompteModalProps> = ({ isOpen, onClose, onSuccess, compte = null }) => {
  const { t } = useTranslation();
  const modeEdition = compte !== null;

  const [nom, setNom] = useState('');
  const [type, setType] = useState<'MOBILE_MONEY' | 'BANCAIRE' | 'ESPECES'>('MOBILE_MONEY');
  const [soldeInitial, setSoldeInitial] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Logo : le client choisit un logo prédéfini OU importe le sien ; sans
  // choix, le logo par défaut du type s'applique (mobile money, espèces) ou
  // le logo reste vide. `logoModifie` distingue « inchangé » (mode édition)
  // de « retiré » pour n'envoyer `logo` au serveur que si nécessaire.
  const [logoPredefini, setLogoPredefini] = useState<string | null>(null);
  const [fichierLogo, setFichierLogo] = useState<File | null>(null);
  const [apercuFichier, setApercuFichier] = useState<string | null>(null);
  const [logoActuel, setLogoActuel] = useState<string | null>(null);
  const [logoModifie, setLogoModifie] = useState(false);
  // Compte déjà créé dont l'import du logo a échoué : le prochain envoi ne
  // refait que l'import, sans recréer un doublon du compte.
  const [idCompteCree, setIdCompteCree] = useState<number | null>(null);
  const inputFichierRef = useRef<HTMLInputElement | null>(null);

  const reinitialiserLogo = (logoServeur: string | null = null) => {
    setLogoPredefini(null);
    setFichierLogo(null);
    setApercuFichier(null);
    setLogoActuel(logoServeur);
    setLogoModifie(false);
    setIdCompteCree(null);
  };

  // Libère l'URL d'aperçu du fichier importé quand elle change ou au démontage.
  useEffect(() => {
    return () => {
      if (apercuFichier) URL.revokeObjectURL(apercuFichier);
    };
  }, [apercuFichier]);

  useEffect(() => {
    // Ouverture en mode édition : on relit le compte depuis le serveur
    // plutôt que de préremplir avec la donnée locale (potentiellement
    // périmée) — pas une synchronisation d'état dérivé d'un rendu précédent.
    if (isOpen && compte) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsLoadingDetail(true);
      setError(null);
      api
        .request<CompteFinancier>(`/comptes/${compte.id_compte}`)
        .then((frais) => {
          setNom(frais.nom);
          setType(frais.type as 'MOBILE_MONEY' | 'BANCAIRE' | 'ESPECES');
          reinitialiserLogo(frais.logo ?? null);
        })
        .catch((err) => setError(err instanceof Error ? err.message : t('modals.compte.error_load')))
        .finally(() => setIsLoadingDetail(false));
    } else if (isOpen) {
      setNom('');
      setType('MOBILE_MONEY');
      setSoldeInitial('');
      setError(null);
      reinitialiserLogo();
    }
  }, [isOpen, compte, t]);

  const choisirLogoPredefini = (src: string) => {
    setLogoPredefini(src);
    setFichierLogo(null);
    setApercuFichier(null);
    setLogoModifie(true);
    setError(null);
  };

  const retirerLogo = () => {
    setLogoPredefini(null);
    setFichierLogo(null);
    setApercuFichier(null);
    setLogoModifie(true);
    setError(null);
  };

  const choisirFichier = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fichier = e.target.files?.[0];
    e.target.value = ''; // permet de re-sélectionner le même fichier
    if (!fichier) return;
    if (!TYPES_LOGO_IMPORTE.includes(fichier.type)) {
      setError(t('modals.compte.logo_error_type'));
      return;
    }
    if (fichier.size > TAILLE_MAX_LOGO_OCTETS) {
      setError(t('modals.compte.logo_error_size'));
      return;
    }
    setError(null);
    setLogoPredefini(null);
    setFichierLogo(fichier);
    setApercuFichier(URL.createObjectURL(fichier));
    setLogoModifie(true);
  };

  // Logo actuellement sélectionné : import > prédéfini > logo du serveur
  // (inchangé), sinon aucun ; l'affichage retombe alors sur le défaut du type.
  const logoSelectionne = apercuFichier ?? logoPredefini ?? (logoModifie ? null : logoActuel);
  const logoAffiche = logoSelectionne ?? obtenirLogoCompte({ type, nom, logo: null });

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const importerLogo = async (idCompte: number) => {
        if (!fichierLogo) return;
        const formData = new FormData();
        formData.append('logo', fichierLogo);
        try {
          await api.request(`/comptes/${idCompte}/logo`, { method: 'POST', body: formData });
        } catch (err) {
          // Le compte existe déjà : on mémorise son id pour ne retenter que
          // l'import du logo au prochain envoi (jamais un second compte).
          if (!modeEdition) setIdCompteCree(idCompte);
          onSuccess?.();
          throw new Error(err instanceof Error ? err.message : t('modals.compte.logo_upload_failed'), { cause: err });
        }
      };

      if (modeEdition && compte) {
        // `logo` n'est envoyé que si le client l'a modifié sans importer de
        // fichier : null = retirer le logo, sinon le prédéfini choisi.
        const corps: Record<string, unknown> = { nom, type };
        if (logoModifie && !fichierLogo) corps.logo = logoPredefini;
        await api.request(`/comptes/${compte.id_compte}`, { method: 'PATCH', body: JSON.stringify(corps) });
        await importerLogo(compte.id_compte);
      } else if (idCompteCree !== null) {
        await importerLogo(idCompteCree);
      } else {
        const creation = await api.request<CompteFinancier>('/comptes', {
          method: 'POST',
          body: JSON.stringify({
            nom,
            type,
            solde_initial: soldeInitial ? Number(soldeInitial) : 0,
            ...(logoPredefini ? { logo: logoPredefini } : {}),
          }),
        });
        await importerLogo(creation.id_compte);
      }
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : (modeEdition ? t('modals.compte.error_edit') : t('modals.compte.error_create')));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 max-h-[90vh] flex flex-col">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <h3 className="text-lg font-bold tracking-tight">{modeEdition ? t('modals.compte.title_edit') : t('modals.compte.title_create')}</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {isLoadingDetail ? (
          <div className="flex justify-center py-14">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('modals.compte.name_label')}</label>
              <input
                type="text"
                required
                placeholder={t('modals.compte.name_placeholder')}
                value={nom}
                onChange={(e) => setNom(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">{t('modals.compte.type_label')}</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as 'MOBILE_MONEY' | 'BANCAIRE' | 'ESPECES')}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="MOBILE_MONEY">{t('modals.compte.type_mobile_money')}</option>
                <option value="BANCAIRE">{t('modals.compte.type_bank')}</option>
                <option value="ESPECES">{t('modals.compte.type_cash')}</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-muted-foreground">{t('modals.compte.logo_label')}</label>
              <div className="flex items-center gap-3">
                <div className="h-14 w-14 rounded-xl border border-border bg-muted/40 flex items-center justify-center overflow-hidden shrink-0">
                  {logoAffiche ? (
                    <img src={logoAffiche} alt={t('modals.compte.logo_preview_alt')} className="h-full w-full object-cover" />
                  ) : (
                    <span className="text-[10px] text-muted-foreground">—</span>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => inputFichierRef.current?.click()}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-border text-xs font-semibold hover:bg-muted"
                  >
                    <Upload className="h-3.5 w-3.5" />
                    <span>{t('modals.compte.logo_import')}</span>
                  </button>
                  <button
                    type="button"
                    onClick={retirerLogo}
                    disabled={!logoSelectionne}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-border text-xs font-semibold hover:bg-muted disabled:opacity-40"
                  >
                    <Ban className="h-3.5 w-3.5" />
                    <span>{t('modals.compte.logo_none')}</span>
                  </button>
                </div>
                <input
                  ref={inputFichierRef}
                  type="file"
                  accept={TYPES_LOGO_IMPORTE.join(',')}
                  onChange={choisirFichier}
                  className="hidden"
                />
              </div>
              <div className="grid grid-cols-5 gap-2">
                {LOGOS_PREDEFINIS.map((logo) => (
                  <button
                    key={logo.id}
                    type="button"
                    title={logo.label}
                    onClick={() => choisirLogoPredefini(logo.src)}
                    className={`rounded-lg overflow-hidden border-2 transition-all ${
                      logoPredefini === logo.src ? 'border-primary ring-2 ring-primary/30' : 'border-transparent hover:border-border'
                    }`}
                  >
                    <img src={logo.src} alt={logo.label} loading="lazy" className="h-10 w-full object-cover" />
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground leading-snug">{t('modals.compte.logo_hint')}</p>
            </div>

            {!modeEdition && (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">{t('modals.compte.initial_balance_label')}</label>
                <input
                  type="number"
                  min={0}
                  placeholder="0"
                  value={soldeInitial}
                  onChange={(e) => setSoldeInitial(e.target.value)}
                  className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            )}

            {error && <p className="text-sm text-destructive text-center">{error}</p>}

            <div className="pt-2 flex gap-3">
              <button type="button" onClick={onClose} className="flex-1 py-3 px-4 rounded-xl border border-border text-sm font-semibold hover:bg-muted">
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 py-3 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-bold shadow-md hover:bg-primary/95 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>{modeEdition ? t('common.save') : t('modals.compte.title_create')}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
