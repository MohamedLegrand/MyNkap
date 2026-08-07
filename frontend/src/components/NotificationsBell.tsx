import React, { useEffect, useRef, useState } from 'react';
import { Bell, Settings2, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import { formatDateRelative } from '../utils/formatters';
import { NotificationsPanel } from './NotificationsPanel';
import type { AppNotification } from '../types';

interface NotificationsBellProps {
  // '/notifications' pour un client, '/admin/notifications' pour l'équipe admin.
  basePath: '/notifications' | '/admin/notifications';
}

export const NotificationsBell: React.FC<NotificationsBellProps> = ({ basePath }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [nonLues, setNonLues] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [panelCible, setPanelCible] = useState<number | null | undefined>(undefined);
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

  return (
    <div className="relative" ref={conteneurRef}>
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label="Notifications"
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
        <div className="absolute right-0 top-full mt-2 w-72 max-w-[90vw] bg-card border border-border rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
          <div className="p-3.5 border-b border-border flex items-center justify-between bg-muted/40">
            <h3 className="text-sm font-bold text-foreground">Notifications</h3>
            <button
              onClick={() => { setPanelCible(null); setIsOpen(false); }}
              title="Gérer mes notifications"
              className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <Settings2 className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="max-h-80 overflow-y-auto divide-y divide-border">
            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : notifications.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8">Aucune notification pour le moment.</p>
            ) : (
              // Titres seulement : le contenu complet ne s'affiche que dans
              // le panneau dédié, ouvert au clic sur une ligne.
              notifications.map((notification) => (
                <button
                  key={notification.id_notification}
                  onClick={() => { setPanelCible(notification.id_notification); setIsOpen(false); }}
                  className={`w-full text-left px-3.5 py-3 flex items-center gap-2.5 hover:bg-muted/40 transition-colors ${
                    notification.est_lue ? '' : 'bg-primary/5'
                  }`}
                >
                  <span
                    className={`h-2 w-2 rounded-full shrink-0 ${notification.est_lue ? 'bg-transparent' : 'bg-primary'}`}
                  />
                  <span className="flex-1 min-w-0 text-xs font-bold text-foreground truncate">{notification.titre}</span>
                  <span className="text-[10px] text-muted-foreground/70 shrink-0">
                    {formatDateRelative(notification.date_creation)}
                  </span>
                </button>
              ))
            )}
          </div>

          {notifications.length > 0 && (
            <button
              onClick={() => { setPanelCible(null); setIsOpen(false); }}
              className="w-full py-2.5 text-xs font-bold text-primary hover:bg-primary/5 transition-colors border-t border-border"
            >
              Gérer mes notifications
            </button>
          )}
        </div>
      )}

      <NotificationsPanel
        isOpen={panelCible !== undefined}
        onClose={() => setPanelCible(undefined)}
        basePath={basePath}
        notificationCiblee={panelCible ?? null}
        onChange={chargerCompteur}
      />
    </div>
  );
};
