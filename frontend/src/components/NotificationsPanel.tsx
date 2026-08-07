import React, { useEffect, useState } from 'react';
import { X, Trash2, CheckCheck, Loader2, Bell } from 'lucide-react';
import { api } from '../services/api';
import { formatDateRelative } from '../utils/formatters';
import type { AppNotification } from '../types';

interface NotificationsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  // '/notifications' pour un client, '/admin/notifications' pour l'équipe admin.
  basePath: '/notifications' | '/admin/notifications';
  // Notification à afficher immédiatement dépliée (venant d'un clic sur son
  // titre dans la cloche) — null pour une ouverture "Gérer mes notifications".
  notificationCiblee: number | null;
  // Prévient la cloche qu'un changement a eu lieu (lu/supprimé), pour
  // qu'elle resynchronise son compteur sans attendre le prochain intervalle.
  onChange: () => void;
}

export const NotificationsPanel: React.FC<NotificationsPanelProps> = ({
  isOpen, onClose, basePath, notificationCiblee, onChange,
}) => {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [confirmationSuppressionTout, setConfirmationSuppressionTout] = useState(false);

  const charger = () => {
    setIsLoading(true);
    api
      .request<AppNotification[]>(basePath)
      .then(setNotifications)
      .catch(() => setNotifications([]))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    // Ouverture de la modale : chargement à la demande, et on déplie
    // directement la notification ciblée si on vient d'un clic dans la
    // cloche — pas une synchronisation d'état dérivé d'un rendu précédent.
    if (isOpen) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setExpandedId(notificationCiblee);
      setConfirmationSuppressionTout(false);
      charger();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, notificationCiblee]);

  if (!isOpen) return null;

  const basculerExpansion = async (notification: AppNotification) => {
    setExpandedId((prev) => (prev === notification.id_notification ? null : notification.id_notification));
    if (!notification.est_lue) {
      setNotifications((prev) =>
        prev.map((n) => (n.id_notification === notification.id_notification ? { ...n, est_lue: true } : n))
      );
      try {
        await api.request(`${basePath}/${notification.id_notification}/lire`, { method: 'POST' });
        onChange();
      } catch {
        // Resynchronisé au prochain chargement du panneau.
      }
    }
  };

  const marquerToutLu = async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, est_lue: true })));
    try {
      await api.request(`${basePath}/lire-tout`, { method: 'POST' });
      onChange();
    } catch {
      // idem
    }
  };

  const supprimer = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    setNotifications((prev) => prev.filter((n) => n.id_notification !== id));
    if (expandedId === id) setExpandedId(null);
    try {
      await api.request(`${basePath}/${id}`, { method: 'DELETE' });
      onChange();
    } catch {
      charger(); // resynchronise si la suppression a réellement échoué
    }
  };

  const supprimerTout = async () => {
    if (!confirmationSuppressionTout) {
      setConfirmationSuppressionTout(true);
      return;
    }
    setNotifications([]);
    setConfirmationSuppressionTout(false);
    try {
      await api.request(basePath, { method: 'DELETE' });
      onChange();
    } catch {
      charger();
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 flex flex-col max-h-[85vh]">
        <div className="p-5 border-b border-border flex items-center justify-between bg-muted/40 shrink-0">
          <h3 className="text-lg font-bold tracking-tight flex items-center gap-2">
            <Bell className="h-5 w-5 text-primary" />
            <span>Notifications</span>
          </h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {notifications.length > 0 && (
          <div className="px-5 py-3 border-b border-border flex items-center justify-between shrink-0 bg-card">
            <button
              onClick={marquerToutLu}
              disabled={!notifications.some((n) => !n.est_lue)}
              className="text-xs font-semibold text-primary hover:underline flex items-center gap-1.5 disabled:opacity-40 disabled:no-underline"
            >
              <CheckCheck className="h-3.5 w-3.5" />
              <span>Tout marquer lu</span>
            </button>
            <button
              onClick={supprimerTout}
              className={`text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                confirmationSuppressionTout ? 'text-destructive' : 'text-muted-foreground hover:text-destructive'
              }`}
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>{confirmationSuppressionTout ? 'Confirmer la suppression ?' : 'Tout supprimer'}</span>
            </button>
          </div>
        )}

        <div className="overflow-y-auto flex-1">
          {isLoading ? (
            <div className="flex justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : notifications.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-12">Aucune notification pour le moment.</p>
          ) : (
            <div className="divide-y divide-border">
              {notifications.map((notification) => {
                const estDepliee = expandedId === notification.id_notification;
                return (
                  <div
                    key={notification.id_notification}
                    role="button"
                    tabIndex={0}
                    onClick={() => basculerExpansion(notification)}
                    onKeyDown={(e) => e.key === 'Enter' && basculerExpansion(notification)}
                    className={`w-full text-left p-4 flex items-start gap-3 hover:bg-muted/40 transition-colors cursor-pointer ${
                      notification.est_lue ? '' : 'bg-primary/5'
                    }`}
                  >
                    <span
                      className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${notification.est_lue ? 'bg-transparent' : 'bg-primary'}`}
                    />
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-bold text-foreground">{notification.titre}</p>
                        <span className="text-[10px] text-muted-foreground/70 shrink-0">
                          {formatDateRelative(notification.date_creation)}
                        </span>
                      </div>
                      {estDepliee && (
                        <p className="text-xs text-muted-foreground leading-relaxed animate-in fade-in duration-150">
                          {notification.message}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={(e) => supprimer(e, notification.id_notification)}
                      title="Supprimer cette notification"
                      className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors shrink-0"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
