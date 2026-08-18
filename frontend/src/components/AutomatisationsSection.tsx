import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Repeat, FileStack, Plus, Loader2, MoreVertical, Pencil, Power, PowerOff, Play,
} from 'lucide-react';
import { api } from '../services/api';
import { TransactionRecurrenteModal } from './TransactionRecurrenteModal';
import { TemplateTransactionModal } from './TemplateTransactionModal';
import { LockedFeatureBanner } from './LockedFeatureBanner';
import type { Categorie, CompteFinancier, TemplateTransaction, TransactionRecurrente } from '../types';

interface AutomatisationsSectionProps {
  comptesActifs: CompteFinancier[];
  categories: Categorie[];
  accesRecurrentes: boolean;
  accesTemplates: boolean;
  // Nombre d'éléments déjà enregistrés (voir GET /abonnement/donnees-verrouillees)
  // affiché dans la bannière quand le forfait actuel ne couvre plus l'accès.
  nombreRecurrentesVerrouillees?: number;
  nombreTemplatesVerrouilles?: number;
  onOpenUpgradeModal?: () => void;
  nomCompte: (idCompte: number) => string;
  nomCategorie: (idCategorie: number | null) => string;
  onDataChange: () => void;
}

const FREQUENCE_LABEL_KEY: Record<TransactionRecurrente['frequence'], string> = {
  HEBDOMADAIRE: 'modals.transaction_recurrente.freq_weekly',
  MENSUELLE: 'modals.transaction_recurrente.freq_monthly',
  TRIMESTRIELLE: 'modals.transaction_recurrente.freq_quarterly',
  ANNUELLE: 'modals.transaction_recurrente.freq_yearly',
};

interface ActionMenuItem {
  label: string;
  icon: React.ElementType;
  onClick: () => void;
  tone?: 'default' | 'destructive' | 'positive';
}

const MenuActions: React.FC<{ items: ActionMenuItem[]; ariaLabel?: string }> = ({ items, ariaLabel = 'Actions' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setIsOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative shrink-0" ref={ref}>
      <button onClick={() => setIsOpen((p) => !p)} aria-label={ariaLabel} className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
        <MoreVertical className="h-4 w-4" />
      </button>
      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-52 bg-card border border-border rounded-xl shadow-xl z-20 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.label}
                onClick={() => { setIsOpen(false); item.onClick(); }}
                className={`w-full flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold transition-colors text-left ${
                  item.tone === 'destructive' ? 'text-destructive hover:bg-destructive/10'
                  : item.tone === 'positive' ? 'text-forest-600 dark:text-forest-400 hover:bg-forest-500/10'
                  : 'text-foreground hover:bg-muted'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export const AutomatisationsSection: React.FC<AutomatisationsSectionProps> = ({
  comptesActifs, categories, accesRecurrentes, accesTemplates,
  nombreRecurrentesVerrouillees, nombreTemplatesVerrouilles, onOpenUpgradeModal,
  nomCompte, nomCategorie, onDataChange,
}) => {
  const { t } = useTranslation();
  const [mode, setMode] = useState<'recurrentes' | 'templates'>(accesRecurrentes ? 'recurrentes' : 'templates');
  const [recurrentes, setRecurrentes] = useState<TransactionRecurrente[]>([]);
  const [templates, setTemplates] = useState<TemplateTransaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isRecurrenceModalOpen, setIsRecurrenceModalOpen] = useState(false);
  const [recurrenceEnEdition, setRecurrenceEnEdition] = useState<TransactionRecurrente | null>(null);
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [templateEnEdition, setTemplateEnEdition] = useState<TemplateTransaction | null>(null);
  const [rejouerEnCours, setRejouerEnCours] = useState<number | null>(null);
  const [messageRejoue, setMessageRejoue] = useState<string | null>(null);

  const charger = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (mode === 'recurrentes' && accesRecurrentes) {
        setRecurrentes(await api.request<TransactionRecurrente[]>('/transactions-recurrentes?include_inactifs=true'));
      } else if (mode === 'templates' && accesTemplates) {
        setTemplates(await api.request<TemplateTransaction[]>('/templates?include_inactifs=true'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('automations.error_load'));
    } finally {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, accesRecurrentes, accesTemplates]);

  useEffect(() => {
    // Chargement à chaque changement d'onglet — pas une synchronisation
    // d'état dérivé d'un rendu précédent.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    charger();
  }, [charger]);

  const toggleActifRecurrence = async (r: TransactionRecurrente) => {
    try {
      if (r.est_active) {
        await api.request(`/transactions-recurrentes/${r.id_transaction_recurrente}`, { method: 'DELETE' });
      } else {
        await api.request(`/transactions-recurrentes/${r.id_transaction_recurrente}/reactiver`, { method: 'POST' });
      }
      charger();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('common.error_action'));
    }
  };

  const toggleActifTemplate = async (tpl: TemplateTransaction) => {
    try {
      if (tpl.est_actif) {
        await api.request(`/templates/${tpl.id_template}`, { method: 'DELETE' });
      } else {
        await api.request(`/templates/${tpl.id_template}/reactiver`, { method: 'POST' });
      }
      charger();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('common.error_action'));
    }
  };

  const rejouerTemplate = async (tpl: TemplateTransaction) => {
    setRejouerEnCours(tpl.id_template);
    setMessageRejoue(null);
    setError(null);
    try {
      await api.request(`/templates/${tpl.id_template}/rejouer`, { method: 'POST' });
      setMessageRejoue(t('automations.replayed', { nom: tpl.nom }));
      charger();
      onDataChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('automations.error_replay'));
    } finally {
      setRejouerEnCours(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="inline-flex rounded-xl bg-muted p-1 gap-1">
        <button
          onClick={() => setMode('recurrentes')}
          className={`flex items-center gap-1.5 text-xs font-bold px-4 py-2 rounded-lg transition-colors ${mode === 'recurrentes' ? 'bg-card text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
        >
          <Repeat className="h-3.5 w-3.5" />
          <span>{t('automations.recurring_tab')}</span>
        </button>
        <button
          onClick={() => setMode('templates')}
          className={`flex items-center gap-1.5 text-xs font-bold px-4 py-2 rounded-lg transition-colors ${mode === 'templates' ? 'bg-card text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
        >
          <FileStack className="h-3.5 w-3.5" />
          <span>{t('automations.templates_tab')}</span>
        </button>
      </div>

      {mode === 'recurrentes' ? (
        !accesRecurrentes ? (
          <LockedFeatureBanner
            titre={t('automations.recurring_title')}
            count={nombreRecurrentesVerrouillees}
            onUpgrade={onOpenUpgradeModal}
          />
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <Repeat className="h-5 w-5 text-primary" />
                <span>{t('automations.recurring_title')}</span>
              </h3>
              <button
                onClick={() => setIsRecurrenceModalOpen(true)}
                disabled={comptesActifs.length === 0}
                className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center gap-2 disabled:opacity-50"
              >
                <Plus className="h-4 w-4" />
                <span>{t('modals.transaction_recurrente.submit')}</span>
              </button>
            </div>

            {error && <p className="text-sm text-destructive text-center">{error}</p>}

            {isLoading ? (
              <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
            ) : recurrentes.length === 0 ? (
              <div className="p-8 rounded-2xl border border-dashed border-border text-center">
                <p className="text-sm text-muted-foreground">{t('automations.none_recurring')}</p>
              </div>
            ) : (
              <div className="bg-card rounded-2xl border border-border shadow-sm divide-y divide-border">
                {recurrentes.map((r) => (
                  <div key={r.id_transaction_recurrente} className={`p-4 flex items-center justify-between gap-3 ${!r.est_active ? 'opacity-60' : ''}`}>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-bold text-foreground truncate">
                          {r.description || nomCategorie(r.id_categorie)}
                        </h4>
                        <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded shrink-0 ${r.type === 'DEPENSE' ? 'bg-destructive/10 text-destructive' : 'bg-forest-500/10 text-forest-600'}`}>
                          {r.type}
                        </span>
                        {!r.est_active && <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-muted text-muted-foreground shrink-0">{t('common.disabled_fem')}</span>}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {nomCompte(r.id_compte)} • {t(FREQUENCE_LABEL_KEY[r.frequence])} • {t('automations.next_on', { date: new Date(r.prochaine_execution).toLocaleDateString('fr-FR') })}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-sm font-black text-foreground tabular-nums">{Number(r.montant).toLocaleString('fr-FR')} XAF</span>
                      <MenuActions
                        ariaLabel={t('automations.recurring_actions_aria')}
                        items={[
                          { label: t('common.edit'), icon: Pencil, onClick: () => setRecurrenceEnEdition(r) },
                          {
                            label: r.est_active ? t('common.disable') : t('common.reactivate'),
                            icon: r.est_active ? PowerOff : Power,
                            onClick: () => toggleActifRecurrence(r),
                            tone: r.est_active ? 'destructive' : 'positive',
                          },
                        ]}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      ) : !accesTemplates ? (
        <LockedFeatureBanner
          titre={t('automations.templates_title')}
          count={nombreTemplatesVerrouilles}
          onUpgrade={onOpenUpgradeModal}
        />
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <FileStack className="h-5 w-5 text-primary" />
              <span>{t('automations.templates_title')}</span>
            </h3>
            <button
              onClick={() => setIsTemplateModalOpen(true)}
              disabled={comptesActifs.length === 0}
              className="bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs py-2.5 px-4 rounded-xl shadow-md transition-all flex items-center gap-2 disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              <span>{t('automations.create_template')}</span>
            </button>
          </div>

          {messageRejoue && <p className="text-sm text-forest-600 dark:text-forest-400 text-center font-semibold">{messageRejoue}</p>}
          {error && <p className="text-sm text-destructive text-center">{error}</p>}

          {isLoading ? (
            <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : templates.length === 0 ? (
            <div className="p-8 rounded-2xl border border-dashed border-border text-center">
              <p className="text-sm text-muted-foreground">{t('automations.none_templates')}</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {templates.map((tpl) => (
                <div key={tpl.id_template} className={`p-4 rounded-2xl border bg-card shadow-sm space-y-2.5 ${!tpl.est_actif ? 'opacity-60' : ''}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h4 className="text-sm font-bold text-foreground truncate">{tpl.nom}</h4>
                      <span className="text-xs text-muted-foreground">{nomCompte(tpl.id_compte)} • {nomCategorie(tpl.id_categorie)}</span>
                    </div>
                    <MenuActions
                      ariaLabel={t('automations.template_actions_aria', { nom: tpl.nom })}
                      items={[
                        { label: t('common.edit'), icon: Pencil, onClick: () => setTemplateEnEdition(tpl) },
                        {
                          label: tpl.est_actif ? t('common.disable') : t('common.reactivate'),
                          icon: tpl.est_actif ? PowerOff : Power,
                          onClick: () => toggleActifTemplate(tpl),
                          tone: tpl.est_actif ? 'destructive' : 'positive',
                        },
                      ]}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className={`font-bold ${tpl.type === 'DEPENSE' ? 'text-destructive' : 'text-forest-600 dark:text-forest-400'}`}>
                      {Number(tpl.montant).toLocaleString('fr-FR')} XAF
                    </span>
                    <span className="text-muted-foreground">{t('automations.usage_count', { count: tpl.nombre_utilisations })}</span>
                  </div>
                  {tpl.est_actif && (
                    <button
                      onClick={() => rejouerTemplate(tpl)}
                      disabled={rejouerEnCours === tpl.id_template}
                      className="w-full py-2 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary text-xs font-bold transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                    >
                      {rejouerEnCours === tpl.id_template ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                      <span>{t('automations.replay_now')}</span>
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <TransactionRecurrenteModal
        isOpen={isRecurrenceModalOpen || recurrenceEnEdition !== null}
        onClose={() => { setIsRecurrenceModalOpen(false); setRecurrenceEnEdition(null); }}
        onSuccess={charger}
        comptes={comptesActifs}
        categories={categories}
        recurrence={recurrenceEnEdition}
      />

      <TemplateTransactionModal
        isOpen={isTemplateModalOpen || templateEnEdition !== null}
        onClose={() => { setIsTemplateModalOpen(false); setTemplateEnEdition(null); }}
        onSuccess={charger}
        comptes={comptesActifs}
        categories={categories}
        template={templateEnEdition}
      />
    </div>
  );
};
