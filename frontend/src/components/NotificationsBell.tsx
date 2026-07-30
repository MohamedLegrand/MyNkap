import React, { useEffect, useRef, useState } from 'react';
import { Bell, Check, CheckCheck, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { AppNotification } from '../types';

interface NotificationsBellProps {
  // '/notifications' pour un client, '/admin/notifications' pour l'équipe admin.
  basePath: '/notifications' | '/admin/notifications';
}

const formatDateRelative = (iso: string) => {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "À l'instant";
  if (minutes < 60) return `Il y a ${minutes} min`;
  const heures = Math.floor(minutes / 60);
  if (heures < 24) return `Il y a ${heures} h`;
  const jours = Math.floor(heures / 24);
  if (jours < 7) return `Il y a ${jours} j`;
  return new Date(iso).toLocaleDateString('fr-FR');
};

export const NotificationsBell: React.FC<NotificationsBellProps> = ({ basePath }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [nonLues, setNonLues] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const conteneurRef = useRef<HTMLDivElement | null>(null);

  const chargerCompteur = () => {
    api
      .request<{ non_lues: number }>(`${basePath}/non-lues-count`)
      .then((res) => setNonLues(res.non_lues))
      .catch(() => {});
  };

  const chargerListe = () => {
    setIsLoading(true);
    api
      .request<AppNotification[]>(basePath)
      .then(setNotifications)
      .catch(() => setNotifications([]))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    chargerCompteur();
    // Rafraîchit le badge régulièrement même panneau fermé, pour que
    // l'utilisateur voie apparaître une nouvelle notification sans avoir à
    // rouvrir le panneau (même cadence que le suivi de paiement HR-Skills Pay).
    const interval = setInterval(chargerCompteur, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basePath]);

  useEffect(() => {
    // Chargement à la demande (ouverture du panneau), pas une synchronisation
    // d'état dérivé — chargerListe déclenche volontairement setIsLoading/
    // setNotifications au clic sur la cloche.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (isOpen) chargerListe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (conteneurRef.current && !conteneurRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const marquerLue = async (notification: AppNotification) => {
    if (notification.est_lue) return;
    setNotifications((prev) =>
      prev.map((n) => (n.id_notification === notification.id_notification ? { ...n, est_lue: true } : n))
    );
    setNonLues((prev) => Math.max(0, prev - 1));
    try {
      await api.request(`${basePath}/${notification.id_notification}/lire`, { method: 'POST' });
    } catch {
      // Pas de rollback visuel pour un simple échec réseau ponctuel — le
      // prochain chargement du panneau resynchronisera l'état réel.
    }
  };

  const marquerToutLu = async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, est_lue: true })));
    setNonLues(0);
    try {
      await api.request(`${basePath}/lire-tout`, { method: 'POST' });
    } catch {
      // idem : resynchronisé au prochain chargement.
    }
  };

  return (
    <div className="relative" ref={conteneurRef}>
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 rounded-xl bg-muted hover:bg-accent text-foreground transition-colors border border-border"
      >
        <Bell className="h-4 w-4 text-muted-foreground" />
        {nonLues > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-primary text-primary-foreground text-[9px] font-bold flex items-center justify-center">
            {nonLues > 9 ? '9+' : nonLues}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-80 max-w-[90vw] bg-card border border-border rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
          <div className="p-3.5 border-b border-border flex items-center justify-between bg-muted/40">
            <h3 className="text-sm font-bold text-foreground">Notifications</h3>
            {notifications.some((n) => !n.est_lue) && (
              <button
                onClick={marquerToutLu}
                className="text-[11px] font-semibold text-primary hover:underline flex items-center gap-1"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                <span>Tout marquer lu</span>
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto divide-y divide-border">
            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : notifications.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8">Aucune notification pour le moment.</p>
            ) : (
              notifications.map((notification) => (
                <button
                  key={notification.id_notification}
                  onClick={() => marquerLue(notification)}
                  className={`w-full text-left p-3.5 flex items-start gap-2.5 hover:bg-muted/40 transition-colors ${
                    notification.est_lue ? '' : 'bg-primary/5'
                  }`}
                >
                  <span
                    className={`mt-1 h-2 w-2 rounded-full shrink-0 ${
                      notification.est_lue ? 'bg-transparent' : 'bg-primary'
                    }`}
                  />
                  <div className="flex-1 min-w-0 space-y-0.5">
                    <p className="text-xs font-bold text-foreground">{notification.titre}</p>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">{notification.message}</p>
                    <p className="text-[10px] text-muted-foreground/70">{formatDateRelative(notification.date_creation)}</p>
                  </div>
                  {notification.est_lue && <Check className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-1" />}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
