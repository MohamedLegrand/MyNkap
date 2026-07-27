import React, { useState } from 'react';
import { X, ShieldCheck, Key, Sliders, CheckCircle2, FileCode, Loader2 } from 'lucide-react';

// --- 1. Modal Créer un Administrateur ---
interface CreateAdminModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { username: string; email: string; mot_de_passe: string; niveau_acces: number }) => void;
}

export const CreateAdminModal: React.FC<CreateAdminModalProps> = ({ isOpen, onClose, onSubmit }) => {
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
            <ShieldCheck className="h-5 w-5 text-amber-500" />
            <h3 className="text-base font-bold">Créer un Administrateur</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">Nom d'utilisateur (Username)</label>
            <input
              type="text"
              required
              placeholder="ex: admin_support"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">Adresse e-mail</label>
            <input
              type="email"
              required
              placeholder="admin@mynkap.cm"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">Mot de passe temporaire</label>
            <input
              type="password"
              required
              minLength={6}
              placeholder="••••••••"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">Niveau d'Accès</label>
            <select
              value={niveauAcces}
              onChange={(e) => setNiveauAcces(Number(e.target.value))}
              className="w-full bg-background border border-border rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-amber-500 focus:outline-none"
            >
              <option value={1}>Niveau 1 : Support & Consultation</option>
              <option value={2}>Niveau 2 : Modérateur (Config & Fraude)</option>
              <option value={3}>Niveau 3 : Superadmin (Gestion Équipe & Droits)</option>
            </select>
          </div>

          <div className="pt-2 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-xs font-semibold hover:bg-muted">
              Annuler
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 py-2.5 rounded-xl bg-amber-500 text-slate-950 text-xs font-bold shadow-md hover:bg-amber-400 flex items-center justify-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>Créer l'Admin</span>
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
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <div className="flex items-center gap-2">
            <Key className="h-5 w-5 text-amber-500" />
            <h3 className="text-base font-bold">Réinitialisation de Mot de Passe</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 text-center">
          {!tempPasswordResult ? (
            <>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Êtes-vous sûr de vouloir réinitialiser le mot de passe du client <strong className="text-foreground">{clientName}</strong> ? Ses sessions actives seront révoquées.
              </p>
              <div className="pt-2 flex gap-3">
                <button onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-xs font-semibold hover:bg-muted">
                  Annuler
                </button>
                <button
                  onClick={onConfirm}
                  className="flex-1 py-2.5 rounded-xl bg-destructive text-destructive-foreground text-xs font-bold shadow-md hover:bg-destructive/90"
                >
                  Générer mot de passe
                </button>
              </div>
            </>
          ) : (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 space-y-2">
                <CheckCircle2 className="h-8 w-8 mx-auto" />
                <h4 className="text-sm font-bold">Mot de passe temporaire généré !</h4>
                <div className="bg-background px-4 py-2 rounded-lg border border-border font-mono text-base font-black text-foreground select-all">
                  {tempPasswordResult}
                </div>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Transmettez ce mot de passe temporaire au client. Il sera invité à le modifier lors de sa prochaine connexion.
              </p>
              <button onClick={onClose} className="w-full py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-bold">
                Fermer
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
  const [valeur, setValeur] = useState(initialValue);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40">
          <div className="flex items-center gap-2">
            <Sliders className="h-5 w-5 text-amber-500" />
            <h3 className="text-base font-bold">Modifier la Configuration Système</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); onSubmit(valeur); onClose(); }} className="p-6 space-y-4">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-muted-foreground">Clé Système</span>
            <div className="bg-muted px-3 py-2 rounded-xl text-xs font-mono font-bold text-foreground">
              {configKey} ({typeDonnee})
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-muted-foreground">Nouvelle Valeur à chaud</label>
            <textarea
              rows={3}
              required
              value={valeur}
              onChange={(e) => setValeur(e.target.value)}
              className="w-full bg-background border border-border rounded-xl p-3 text-xs font-mono focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="pt-2 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-xs font-semibold hover:bg-muted">
              Annuler
            </button>
            <button type="submit" className="flex-1 py-2.5 rounded-xl bg-amber-500 text-slate-950 text-xs font-bold shadow-md hover:bg-amber-400">
              Appliquer à chaud
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// --- 4. Modal Visualiseur d'Audit JSON ---
interface ViewAuditDetailModalProps {
  isOpen: boolean;
  auditItem: any;
  onClose: () => void;
}

export const ViewAuditDetailModal: React.FC<ViewAuditDetailModalProps> = ({ isOpen, auditItem, onClose }) => {
  if (!isOpen || !auditItem) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden max-h-[85vh] flex flex-col">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40 shrink-0">
          <div className="flex items-center gap-2">
            <FileCode className="h-5 w-5 text-amber-500" />
            <h3 className="text-base font-bold">Détail d'Événement d'Audit #{auditItem.id_log}</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto flex-1 text-xs">
          <div className="grid grid-cols-2 gap-4 bg-muted/30 p-4 rounded-xl border border-border">
            <div>
              <span className="text-muted-foreground font-semibold">Utilisateur :</span>{' '}
              <strong className="text-foreground">{auditItem.utilisateur_email || `ID ${auditItem.id_utilisateur}`}</strong>
            </div>
            <div>
              <span className="text-muted-foreground font-semibold">Action :</span>{' '}
              <span className="bg-primary/10 text-primary font-bold px-2 py-0.5 rounded">{auditItem.action}</span>
            </div>
            <div>
              <span className="text-muted-foreground font-semibold">Ressource :</span>{' '}
              <strong className="text-foreground">{auditItem.ressource} (ID {auditItem.id_ressource})</strong>
            </div>
            <div>
              <span className="text-muted-foreground font-semibold">Horodatage :</span>{' '}
              <span className="text-foreground">{auditItem.date_action}</span>
            </div>
          </div>

          {/* JSON Donnees Avant */}
          <div className="space-y-1">
            <span className="font-bold text-muted-foreground uppercase text-[10px]">Données Avant (JSON)</span>
            <pre className="bg-slate-950 text-slate-200 p-3 rounded-xl overflow-x-auto text-[11px] font-mono border border-slate-800">
              {auditItem.donnees_avant ? JSON.stringify(auditItem.donnees_avant, null, 2) : 'null'}
            </pre>
          </div>

          {/* JSON Donnees Apres */}
          <div className="space-y-1">
            <span className="font-bold text-muted-foreground uppercase text-[10px]">Données Après (JSON)</span>
            <pre className="bg-slate-950 text-emerald-400 p-3 rounded-xl overflow-x-auto text-[11px] font-mono border border-slate-800">
              {auditItem.donnees_apres ? JSON.stringify(auditItem.donnees_apres, null, 2) : 'null'}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
