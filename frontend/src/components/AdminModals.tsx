import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, ShieldCheck, Key, Sliders, CheckCircle2, FileCode, Loader2, UserCog, Crown, AlertOctagon, ArrowDownToLine, AlertTriangle, Wand2 } from 'lucide-react';
import { api } from '../services/api';
import { PasswordInput } from './PasswordInput';
import { genererMotDePasse } from '../utils/genererMotDePasse';
import type { AdminClientDetail, AdminTransactionSuspecteDetail, Plan, PaysOperateur } from '../types';

// Libellés d'affichage des opérateurs Mobile Money couverts par HR-Skills
// Pay — même table que PlanUpgradeModal (côté client, autre point d'entrée
// du même catalogue pays/opérateurs).
const OPERATEUR_LABELS: Record<string, string> = {
  ORANGE: 'Orange Money', MTN: 'MTN MoMo', MOOV: 'Moov Money', AIRTEL: 'Airtel Money',
  MPESA: 'M-Pesa', WAVE: 'Wave', FREE: 'Free Money', TMONEY: 'TMoney', AFRIMONEY: 'AfriMoney',
  CAMTEL: 'Camtel Money', NEXTTEL: 'Nexttel', CORIS: 'Coris Money', EXPRESSO: 'Expresso',
  FLOOZ: 'Flooz', QMONEY: 'QMoney',
};

// --- 1. Modal Créer un Administrateur ---
interface CreateAdminModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { username: string; email: string; mot_de_passe: string; niveau_acces: number }) => void;
}

export const CreateAdminModal: React.FC<CreateAdminModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const { t } = useTranslation();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [motDePasse, setMotDePasse] = useState('');
  const [niveauAcces, setNiveauAcces] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      onSubmit({ username, email, mot_de_passe: motDePasse, niveau_acces: niveauAcces });
      setIsSubmitting(false);
      onClose();
    }, 500);
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <h3 className="text-base font-bold">{t('admin.modals.create_admin.title')}</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">{t('admin.modals.create_admin.username_label')}</label>
            <input
              type="text"
              required
              placeholder={t('admin.modals.create_admin.username_placeholder')}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">{t('auth.email')}</label>
            <input
              type="email"
              required
              placeholder={t('admin.modals.create_admin.email_placeholder')}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-muted-foreground">{t('admin.modals.create_admin.password_label')}</label>
              <button
                type="button"
                onClick={() => setMotDePasse(genererMotDePasse())}
                className="inline-flex items-center gap-1 text-[11px] font-bold text-primary hover:underline"
              >
                <Wand2 className="h-3 w-3" />
                <span>{t('admin.modals.create_admin.generate_password')}</span>
              </button>
            </div>
            <PasswordInput
              required
              minLength={6}
              placeholder="••••••••"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              showLockIcon={false}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">{t('admin.modals.create_admin.access_level_label')}</label>
            <select
              value={niveauAcces}
              onChange={(e) => setNiveauAcces(Number(e.target.value))}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value={1}>{t('admin.modals.create_admin.access_level_1')}</option>
              <option value={2}>{t('admin.modals.create_admin.access_level_2')}</option>
              <option value={3}>{t('admin.modals.create_admin.access_level_3')}</option>
            </select>
          </div>

          <div className="pt-2 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-xs font-semibold hover:bg-muted">
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-bold shadow-md hover:bg-primary/90 flex items-center justify-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>{t('admin.modals.create_admin.submit')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// --- 2. Modal Réinitialiser Mot de Passe Client ---
interface ResetClientPasswordModalProps {
  isOpen: boolean;
  clientName: string;
  onClose: () => void;
  onConfirm: () => void;
  tempPasswordResult?: string | null;
}

export const ResetClientPasswordModal: React.FC<ResetClientPasswordModalProps> = ({
  isOpen,
  clientName,
  onClose,
  onConfirm,
  tempPasswordResult,
}) => {
  const { t } = useTranslation();
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <div className="flex items-center gap-2">
            <Key className="h-5 w-5 text-primary" />
            <h3 className="text-base font-bold">{t('admin.modals.reset_password.title')}</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 text-center">
          {!tempPasswordResult ? (
            <>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {t('admin.modals.reset_password.confirm_part1')}{' '}
                <strong className="text-foreground">{clientName}</strong>
                {' '}{t('admin.modals.reset_password.confirm_part2')}
              </p>
              <div className="pt-2 flex gap-3">
                <button onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-xs font-semibold hover:bg-muted">
                  {t('common.cancel')}
                </button>
                <button
                  onClick={onConfirm}
                  className="flex-1 py-2.5 rounded-xl bg-destructive text-destructive-foreground text-xs font-bold shadow-md hover:bg-destructive/90"
                >
                  {t('admin.modals.reset_password.generate')}
                </button>
              </div>
            </>
          ) : (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-forest-500/10 border border-forest-500/20 text-forest-600 dark:text-forest-400 space-y-2">
                <CheckCircle2 className="h-8 w-8 mx-auto" />
                <h4 className="text-sm font-bold">{t('admin.modals.reset_password.generated_title')}</h4>
                <div className="bg-background px-4 py-2 rounded-lg border border-border font-mono text-base font-black text-foreground select-all">
                  {tempPasswordResult}
                </div>
              </div>
              <p className="text-[11px] text-muted-foreground">
                {t('admin.modals.reset_password.transmit_hint')}
              </p>
              <button onClick={onClose} className="w-full py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-bold">
                {t('common.close')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// --- 3. Modal Configuration Système à Chaud ---
interface EditConfigModalProps {
  isOpen: boolean;
  configKey: string;
  initialValue: string;
  typeDonnee: string;
  onClose: () => void;
  onSubmit: (valeur: string) => void;
}

export const EditConfigModal: React.FC<EditConfigModalProps> = ({
  isOpen,
  configKey,
  initialValue,
  typeDonnee,
  onClose,
  onSubmit,
}) => {
  const { t } = useTranslation();
  const [valeur, setValeur] = useState(initialValue);

  useEffect(() => {
    // Resynchronise avec la valeur fraîchement chargée à chaque ouverture —
    // ce composant reste monté en arrière-plan (isOpen ne fait que masquer
    // son rendu), donc l'état initial de useState ne se remet pas à jour
    // tout seul quand une nouvelle clé est ouverte.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (isOpen) setValeur(initialValue);
  }, [isOpen, initialValue]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <div className="flex items-center gap-2">
            <Sliders className="h-5 w-5 text-primary" />
            <h3 className="text-base font-bold">{t('admin.modals.edit_config.title')}</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); onSubmit(valeur); onClose(); }} className="p-6 space-y-4">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-muted-foreground">{t('admin.modals.edit_config.system_key_label')}</span>
            <div className="bg-muted px-3 py-2 rounded-xl text-xs font-mono font-bold text-foreground">
              {configKey} ({typeDonnee})
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">{t('admin.modals.edit_config.new_value_label')}</label>
            <textarea
              rows={3}
              required
              value={valeur}
              onChange={(e) => setValeur(e.target.value)}
              className="w-full bg-background border border-border rounded-xl p-3 text-xs font-mono focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>

          <div className="pt-2 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-xs font-semibold hover:bg-muted">
              {t('common.cancel')}
            </button>
            <button type="submit" className="flex-1 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-bold shadow-md hover:bg-primary/90">
              {t('admin.modals.edit_config.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// --- 4. Modal Visualiseur d'Audit JSON ---
interface AuditItemDetail {
  id_log: number;
  utilisateur_email: string | null;
  id_utilisateur: number;
  action: string;
  ressource: string;
  id_ressource: number | null;
  date_action: string;
  donnees_avant: Record<string, unknown> | null;
  donnees_apres: Record<string, unknown> | null;
}

interface ViewAuditDetailModalProps {
  isOpen: boolean;
  auditItem: AuditItemDetail | null;
  onClose: () => void;
}

export const ViewAuditDetailModal: React.FC<ViewAuditDetailModalProps> = ({ isOpen, auditItem, onClose }) => {
  const { t } = useTranslation();
  if (!isOpen || !auditItem) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden max-h-[85vh] flex flex-col">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40 shrink-0">
          <div className="flex items-center gap-2">
            <FileCode className="h-5 w-5 text-primary" />
            <h3 className="text-base font-bold">{t('admin.modals.audit_detail.title', { id: auditItem.id_log })}</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto flex-1 text-xs">
          <div className="grid grid-cols-2 gap-4 bg-muted/30 p-4 rounded-xl border border-border">
            <div>
              <span className="text-muted-foreground font-semibold">{t('admin.modals.audit_detail.user_label')}</span>{' '}
              <strong className="text-foreground">{auditItem.utilisateur_email || `ID ${auditItem.id_utilisateur}`}</strong>
            </div>
            <div>
              <span className="text-muted-foreground font-semibold">{t('admin.modals.audit_detail.action_label')}</span>{' '}
              <span className="bg-primary/10 text-primary font-bold px-2 py-0.5 rounded">{auditItem.action}</span>
            </div>
            <div>
              <span className="text-muted-foreground font-semibold">{t('admin.modals.audit_detail.resource_label')}</span>{' '}
              <strong className="text-foreground">{auditItem.ressource} (ID {auditItem.id_ressource})</strong>
            </div>
            <div>
              <span className="text-muted-foreground font-semibold">{t('admin.modals.audit_detail.timestamp_label')}</span>{' '}
              <span className="text-foreground">{auditItem.date_action}</span>
            </div>
          </div>

          {/* JSON Donnees Avant */}
          <div className="space-y-1">
            <span className="font-bold text-muted-foreground uppercase text-[10px]">{t('admin.modals.audit_detail.data_before')}</span>
            <pre className="bg-slate-950 text-slate-200 p-3 rounded-xl overflow-x-auto text-[11px] font-mono border border-slate-800">
              {auditItem.donnees_avant ? JSON.stringify(auditItem.donnees_avant, null, 2) : 'null'}
            </pre>
          </div>

          {/* JSON Donnees Apres */}
          <div className="space-y-1">
            <span className="font-bold text-muted-foreground uppercase text-[10px]">{t('admin.modals.audit_detail.data_after')}</span>
            <pre className="bg-slate-950 text-forest-400 p-3 rounded-xl overflow-x-auto text-[11px] font-mono border border-slate-800">
              {auditItem.donnees_apres ? JSON.stringify(auditItem.donnees_apres, null, 2) : 'null'}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};

// --- 5. Modal Détail Client + Forcer un plan d'abonnement ---
interface ClientDetailModalProps {
  isOpen: boolean;
  idClient: number | null;
  onClose: () => void;
  onForced: () => void;
}

const formatXAF2 = (valeur: number) => `${Number(valeur).toLocaleString('fr-FR')} XAF`;

export const ClientDetailModal: React.FC<ClientDetailModalProps> = ({ isOpen, idClient, onClose, onForced }) => {
  const { t } = useTranslation();
  const [detail, setDetail] = useState<AdminClientDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [plans, setPlans] = useState<Plan[]>([]);
  const [idPlan, setIdPlan] = useState('');
  const [statutForce, setStatutForce] = useState<'ESSAI' | 'ACTIF' | 'EXPIRE' | 'ANNULE'>('ACTIF');
  const [dureeJours, setDureeJours] = useState('30');
  const [isForcing, setIsForcing] = useState(false);
  const [messageForcage, setMessageForcage] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || idClient === null) return;
    // Chargement à l'ouverture — pas une synchronisation d'état dérivé.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsLoading(true);
    setError(null);
    setMessageForcage(null);
    Promise.all([
      api.request<AdminClientDetail>(`/admin/clients/${idClient}`),
      api.request<Plan[]>('/plans'),
    ])
      .then(([d, p]) => {
        setDetail(d);
        setPlans(p);
        if (p.length > 0) setIdPlan(String(p[0].id_plan));
      })
      .catch((err) => setError(err instanceof Error ? err.message : t('admin.modals.client_detail.error_load')))
      .finally(() => setIsLoading(false));
  }, [isOpen, idClient, t]);

  if (!isOpen || idClient === null) return null;

  const handleForcer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idPlan) return;
    setIsForcing(true);
    setError(null);
    setMessageForcage(null);
    try {
      await api.request(`/admin/clients/${idClient}/abonnement/forcer`, {
        method: 'POST',
        body: JSON.stringify({
          id_plan: Number(idPlan),
          statut: statutForce,
          duree_jours: dureeJours ? Number(dureeJours) : undefined,
        }),
      });
      setMessageForcage(t('admin.modals.client_detail.plan_assigned_success'));
      onForced();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.modals.client_detail.error_assign'));
    } finally {
      setIsForcing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40 shrink-0">
          <div className="flex items-center gap-2">
            <UserCog className="h-5 w-5 text-primary" />
            <h3 className="text-base font-bold">{t('admin.modals.client_detail.title')}</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {isLoading ? (
            <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : !detail ? (
            <p className="text-sm text-destructive text-center">{error ?? t('admin.modals.client_detail.not_found')}</p>
          ) : (
            <>
              <div className="p-4 rounded-xl bg-muted/30 border border-border space-y-1 text-xs">
                <p className="font-bold text-foreground text-sm">{detail.first_name} {detail.last_name}</p>
                <p className="text-muted-foreground">{detail.email} • {detail.phone}</p>
                <p className="text-muted-foreground">{t('admin.modals.client_detail.client_since', { date: new Date(detail.date_creation).toLocaleDateString('fr-FR') })}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl border border-border">
                  <p className="text-muted-foreground">{t('admin.modals.client_detail.main_balance')}</p>
                  <p className="font-black text-foreground text-sm">{formatXAF2(detail.solde_compte_principal)}</p>
                </div>
                <div className="p-3 rounded-xl border border-border">
                  <p className="text-muted-foreground">{t('admin.modals.client_detail.current_plan')}</p>
                  <p className="font-black text-primary text-sm">{detail.plan_abonnement}</p>
                </div>
                <div className="p-3 rounded-xl border border-border">
                  <p className="text-muted-foreground">{t('admin.modals.client_detail.financial_accounts')}</p>
                  <p className="font-black text-foreground text-sm">{detail.nombre_comptes_financiers}</p>
                </div>
                <div className="p-3 rounded-xl border border-border">
                  <p className="text-muted-foreground">{t('dashboard.nav.transactions')}</p>
                  <p className="font-black text-foreground text-sm">{detail.nombre_transactions}</p>
                </div>
                <div className="p-3 rounded-xl border border-border col-span-2">
                  <p className="text-muted-foreground">{t('admin.modals.client_detail.active_debts_claims')}</p>
                  <p className="font-black text-foreground text-sm">{detail.nombre_dettes_actives}</p>
                </div>
              </div>

              <form onSubmit={handleForcer} className="p-4 rounded-xl border border-primary/20 bg-primary/5 space-y-3">
                <p className="text-xs font-bold text-foreground flex items-center gap-1.5">
                  <Crown className="h-3.5 w-3.5 text-primary" />
                  <span>{t('admin.modals.client_detail.force_plan_title')}</span>
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <select value={idPlan} onChange={(e) => setIdPlan(e.target.value)} className="bg-background border border-border rounded-lg px-2.5 py-2 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-primary">
                    {plans.map((p) => <option key={p.id_plan} value={p.id_plan}>{p.nom}</option>)}
                  </select>
                  <select value={statutForce} onChange={(e) => setStatutForce(e.target.value as typeof statutForce)} className="bg-background border border-border rounded-lg px-2.5 py-2 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-primary">
                    <option value="ESSAI">ESSAI</option>
                    <option value="ACTIF">ACTIF</option>
                    <option value="EXPIRE">EXPIRE</option>
                    <option value="ANNULE">ANNULE</option>
                  </select>
                </div>
                <input
                  type="number"
                  min={1}
                  value={dureeJours}
                  onChange={(e) => setDureeJours(e.target.value)}
                  placeholder={t('admin.modals.client_detail.duration_placeholder')}
                  className="w-full bg-background border border-border rounded-lg px-2.5 py-2 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                />
                {messageForcage && <p className="text-xs font-semibold text-forest-600 dark:text-forest-400">{messageForcage}</p>}
                <button type="submit" disabled={isForcing} className="w-full py-2 rounded-lg bg-primary text-primary-foreground text-xs font-bold flex items-center justify-center gap-1.5 disabled:opacity-50">
                  {isForcing && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  <span>{t('admin.modals.client_detail.assign_plan')}</span>
                </button>
              </form>

              {error && <p className="text-sm text-destructive text-center">{error}</p>}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

// --- 6bis. Modal Créer/Modifier un Plan Tarifaire ---
interface PlanFormData {
  nom: string;
  prix_mensuel: number;
  prix_annuel: number;
  devise: string;
  acces_dettes: boolean;
  acces_epargne: boolean;
  acces_recurrentes: boolean;
  acces_templates: boolean;
  acces_analyse: boolean;
  acces_jarvis: boolean;
  acces_rapport: boolean;
  acces_tontine: boolean;
}

interface PlanModalProps {
  isOpen: boolean;
  plan: Plan | null; // null = création d'un nouveau plan
  onClose: () => void;
  onSubmit: (data: PlanFormData) => Promise<void>;
}

// Ces 3 noms sont figés côté backend (inscription, essai gratuit, retour au
// gratuit, souscription payante) : les renommer casserait ces flux — voir
// admin.service.PLANS_SYSTEME.
const PLANS_SYSTEME = ['GRATUIT', 'ESSENTIEL', 'PREMIUM'];

const ACCES_VIDES = {
  acces_dettes: false,
  acces_epargne: false,
  acces_recurrentes: false,
  acces_templates: false,
  acces_analyse: false,
  acces_jarvis: false,
  acces_rapport: false,
  acces_tontine: false,
};

const ACCES_OPTIONS: { key: keyof typeof ACCES_VIDES; labelKey: string }[] = [
  { key: 'acces_dettes', labelKey: 'dashboard.nav.debts' },
  { key: 'acces_epargne', labelKey: 'dashboard.nav.savings' },
  { key: 'acces_recurrentes', labelKey: 'automations.recurring_title' },
  { key: 'acces_templates', labelKey: 'automations.templates_title' },
  { key: 'acces_analyse', labelKey: 'dashboard.nav.analyse' },
  { key: 'acces_jarvis', labelKey: 'dashboard.nav.jarvis' },
  { key: 'acces_rapport', labelKey: 'dashboard.nav.reports' },
  { key: 'acces_tontine', labelKey: 'admin.modals.plan.feature_tontines' },
];

export const PlanModal: React.FC<PlanModalProps> = ({ isOpen, plan, onClose, onSubmit }) => {
  const { t } = useTranslation();
  const [nom, setNom] = useState('');
  const [prixMensuel, setPrixMensuel] = useState('0');
  const [prixAnnuel, setPrixAnnuel] = useState('0');
  const [devise, setDevise] = useState('XAF');
  const [acces, setAcces] = useState(ACCES_VIDES);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    // Resynchronise à chaque ouverture — ce composant reste monté en
    // arrière-plan entre deux ouvertures (voir EditConfigModal ci-dessus).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setError(null);
    if (plan) {
      setNom(plan.nom);
      setPrixMensuel(String(plan.prix_mensuel));
      setPrixAnnuel(String(plan.prix_annuel));
      setDevise(plan.devise);
      setAcces({
        acces_dettes: plan.acces_dettes,
        acces_epargne: plan.acces_epargne,
        acces_recurrentes: plan.acces_recurrentes,
        acces_templates: plan.acces_templates,
        acces_analyse: plan.acces_analyse,
        acces_jarvis: plan.acces_jarvis,
        acces_rapport: plan.acces_rapport,
        acces_tontine: plan.acces_tontine,
      });
    } else {
      setNom('');
      setPrixMensuel('0');
      setPrixAnnuel('0');
      setDevise('XAF');
      setAcces(ACCES_VIDES);
    }
  }, [isOpen, plan]);

  if (!isOpen) return null;

  const estPlanSysteme = plan ? PLANS_SYSTEME.includes(plan.nom) : false;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        nom,
        prix_mensuel: Number(prixMensuel) || 0,
        prix_annuel: Number(prixAnnuel) || 0,
        devise,
        ...acces,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.dette_operation.error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40 shrink-0">
          <div className="flex items-center gap-2">
            <Crown className="h-5 w-5 text-primary" />
            <h3 className="text-base font-bold">{plan ? t('admin.modals.plan.title_edit') : t('admin.modals.plan.title_create')}</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">{t('admin.modals.plan.name_label')}</label>
            <input
              type="text"
              required
              disabled={estPlanSysteme}
              value={nom}
              onChange={(e) => setNom(e.target.value.toUpperCase())}
              placeholder={t('admin.modals.plan.name_placeholder')}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-primary focus:outline-none disabled:opacity-60"
            />
            {estPlanSysteme && (
              <p className="text-[10px] text-muted-foreground">{t('admin.modals.plan.system_plan_hint')}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-muted-foreground">{t('admin.modals.plan.monthly_price_label')}</label>
              <input
                type="number"
                min={0}
                step="0.01"
                required
                value={prixMensuel}
                onChange={(e) => setPrixMensuel(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-primary focus:outline-none"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-muted-foreground">{t('admin.modals.plan.yearly_price_label')}</label>
              <input
                type="number"
                min={0}
                step="0.01"
                required
                value={prixAnnuel}
                onChange={(e) => setPrixAnnuel(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-primary focus:outline-none"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">{t('admin.modals.plan.currency_label')}</label>
            <input
              type="text"
              required
              value={devise}
              onChange={(e) => setDevise(e.target.value.toUpperCase())}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>

          <div className="space-y-2">
            <span className="text-xs font-semibold text-muted-foreground">{t('admin.modals.plan.features_label')}</span>
            <div className="grid grid-cols-2 gap-2">
              {ACCES_OPTIONS.map((opt) => (
                <label key={opt.key} className="flex items-center gap-2 text-xs font-medium p-2 rounded-lg border border-border cursor-pointer hover:bg-muted/50">
                  <input
                    type="checkbox"
                    checked={acces[opt.key]}
                    onChange={(e) => setAcces((prev) => ({ ...prev, [opt.key]: e.target.checked }))}
                    className="accent-primary"
                  />
                  <span>{t(opt.labelKey)}</span>
                </label>
              ))}
            </div>
          </div>

          {error && <p className="text-xs text-destructive">{error}</p>}

          <div className="pt-2 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-xs font-semibold hover:bg-muted">
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-bold shadow-md hover:bg-primary/90 flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>{plan ? t('common.save') : t('admin.modals.plan.submit_create')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// --- 6. Modal Détail d'une transaction suspecte (fiche d'investigation) ---
interface TransactionSuspecteDetailModalProps {
  isOpen: boolean;
  idTransaction: number | null;
  onClose: () => void;
}

export const TransactionSuspecteDetailModal: React.FC<TransactionSuspecteDetailModalProps> = ({ isOpen, idTransaction, onClose }) => {
  const { t } = useTranslation();
  const [detail, setDetail] = useState<AdminTransactionSuspecteDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || idTransaction === null) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsLoading(true);
    setError(null);
    api
      .request<AdminTransactionSuspecteDetail>(`/admin/fraude/transactions/${idTransaction}`)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : t('modals.transaction_detail.error_load')))
      .finally(() => setIsLoading(false));
  }, [isOpen, idTransaction, t]);

  if (!isOpen || idTransaction === null) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-destructive/30 shadow-2xl overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between bg-destructive/10 shrink-0">
          <div className="flex items-center gap-2">
            <AlertOctagon className="h-5 w-5 text-destructive" />
            <h3 className="text-base font-bold text-destructive">{t('admin.modals.transaction_suspecte.title')}</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-3 text-xs">
          {isLoading ? (
            <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : !detail ? (
            <p className="text-sm text-destructive text-center">{error ?? t('modals.transaction_detail.not_found')}</p>
          ) : (
            <>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('admin.modals.transaction_suspecte.client_label')}</span><strong className="text-foreground">{detail.nom_client} ({detail.email_client})</strong></div>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('modals.transaction_detail.account')}</span><strong className="text-foreground">{detail.nom_compte}</strong></div>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('modals.transaction_detail.category')}</span><strong className="text-foreground">{detail.nom_categorie ?? '—'}</strong></div>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('transfers.amount')}</span><strong className="text-destructive">{formatXAF2(detail.montant)}</strong></div>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('modals.transaction_detail.type')}</span><strong className="text-foreground">{detail.type}</strong></div>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('common.date')}</span><strong className="text-foreground">{new Date(detail.date).toLocaleDateString('fr-FR')}</strong></div>
              <div className="pt-2 mt-2 border-t border-border flex justify-between"><span className="text-muted-foreground">{t('admin.modals.transaction_suspecte.main_balance_label')}</span><strong className="text-foreground">{formatXAF2(detail.solde_compte_principal)}</strong></div>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('admin.modals.transaction_suspecte.total_transactions_label')}</span><strong className="text-foreground">{detail.nombre_total_transactions_client}</strong></div>
              <div className="flex justify-between"><span className="text-muted-foreground">{t('admin.modals.transaction_suspecte.suspicious_count_label')}</span><strong className="text-destructive">{detail.nombre_transactions_suspectes_client}</strong></div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

// --- 7. Modal Nouveau Retrait (Cash-Out HR-Skills Pay) ---
export interface CreateRetraitData {
  montant: number;
  devise: string;
  pays: string;
  operator: string;
  phone_number: string;
  raison: string;
}

interface CreateRetraitModalProps {
  isOpen: boolean;
  soldeDisponible: number | null;
  soldeDevise: string;
  onClose: () => void;
  // Rejette en cas d'échec (solde insuffisant, pays/opérateur refusés...) —
  // la modale reste ouverte et affiche l'erreur au lieu de se refermer
  // optimistiquement, contrairement aux autres modales admin : un retrait
  // déplace de l'argent réel, une erreur silencieuse coûterait cher.
  onSubmit: (data: CreateRetraitData) => Promise<void>;
}

export const CreateRetraitModal: React.FC<CreateRetraitModalProps> = ({
  isOpen, soldeDisponible, soldeDevise, onClose, onSubmit,
}) => {
  const { t } = useTranslation();
  const [paysDisponibles, setPaysDisponibles] = useState<PaysOperateur[]>([]);
  const [pays, setPays] = useState('CM');
  const [operator, setOperator] = useState('ORANGE');
  const [montant, setMontant] = useState('');
  const [phone, setPhone] = useState('');
  const [raison, setRaison] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setError(null);
    setMontant('');
    setPhone('');
    setRaison('');
    setPays('CM');
    setOperator('ORANGE');
    api.request<PaysOperateur[]>('/abonnement/pays-disponibles').then(setPaysDisponibles).catch(() => {});
  }, [isOpen]);

  if (!isOpen) return null;

  const paysActuel = paysDisponibles.find((p) => p.pays === pays);
  const operateursDuPays = paysActuel?.operateurs ?? ['ORANGE', 'MTN'];
  const deviseDuPays = paysActuel?.devise ?? 'XAF';

  const handleChangerPays = (nouveauPays: string) => {
    setPays(nouveauPays);
    const operateurs = paysDisponibles.find((p) => p.pays === nouveauPays)?.operateurs;
    if (operateurs && operateurs.length > 0) setOperator(operateurs[0]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const montantNombre = Number(montant);
    if (!montantNombre || montantNombre <= 0 || !phone.trim()) return;

    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({
        montant: montantNombre, devise: deviseDuPays, pays, operator,
        phone_number: phone.trim(), raison: raison.trim(),
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.modals.retrait.error_generic'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <div className="flex items-center gap-2">
            <ArrowDownToLine className="h-5 w-5 text-primary" />
            <h3 className="text-base font-bold">{t('admin.modals.retrait.title')}</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {soldeDisponible !== null && (
            <p className="text-xs text-muted-foreground">
              {t('admin.modals.retrait.available_balance')} <strong className="text-foreground">{soldeDisponible.toLocaleString('fr-FR')} {soldeDevise}</strong>
            </p>
          )}

          {error && (
            <p className="text-xs text-destructive flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              <span>{error}</span>
            </p>
          )}

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">{t('admin.modals.retrait.amount_label')}</label>
            <input
              type="number"
              required
              min={1}
              value={montant}
              onChange={(e) => setMontant(e.target.value)}
              placeholder="50000"
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.plan_upgrade.country_label')}</label>
            <select
              value={pays}
              onChange={(e) => handleChangerPays(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-primary focus:outline-none"
            >
              {(paysDisponibles.length > 0 ? paysDisponibles : [{ pays: 'CM', nom: 'Cameroun', devise: 'XAF', operateurs: [] }]).map((p) => (
                <option key={p.pays} value={p.pays}>{p.nom}</option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.plan_upgrade.operator_label')}</label>
            <div className="grid grid-cols-2 gap-2 p-1 bg-muted rounded-xl">
              {operateursDuPays.map((op) => (
                <button
                  key={op}
                  type="button"
                  onClick={() => setOperator(op)}
                  className={`py-2 rounded-lg text-xs font-bold transition-all ${
                    operator === op ? 'bg-card text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {OPERATEUR_LABELS[op] ?? op}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">{t('modals.plan_upgrade.phone_label')}</label>
            <input
              type="tel"
              required
              placeholder="ex: 237690000000"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">{t('admin.modals.retrait.reason_label')}</label>
            <textarea
              rows={2}
              value={raison}
              onChange={(e) => setRaison(e.target.value)}
              placeholder={t('admin.modals.retrait.reason_placeholder')}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm resize-none focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>

          <div className="pt-2 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-xs font-semibold hover:bg-muted">
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-bold shadow-md hover:bg-primary/90 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>{t('admin.modals.retrait.submit')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
