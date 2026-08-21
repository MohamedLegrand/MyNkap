import React, { useState } from 'react';

interface AvatarProps {
  src?: string | null;
  nom: string;
  className?: string;
}

// Photo réelle si configurée, sinon un badge coloré avec l'initiale — même
// convention visuelle que le badge déjà utilisé dans DashboardLayout pour
// l'utilisateur connecté, réutilisée ici partout où une photo de profil
// peut manquer (avis publics, paramètres de profil).
export const Avatar: React.FC<AvatarProps> = ({ src, nom, className = 'h-9 w-9' }) => {
  // Si l'URL enregistrée ne charge plus (fichier supprimé, backend sur un
  // autre hôte que celui qui a généré l'URL), on retombe sur l'initiale
  // plutôt que de laisser un cadre d'image cassée à l'écran.
  const [enErreur, setEnErreur] = useState(false);

  if (src && !enErreur) {
    return (
      <img
        src={src}
        alt=""
        onError={() => setEnErreur(true)}
        className={`${className} rounded-xl object-cover shrink-0 border border-border`}
      />
    );
  }
  return (
    <div className={`${className} rounded-xl bg-primary text-primary-foreground font-bold flex items-center justify-center shadow-sm shrink-0`}>
      {nom ? nom[0].toUpperCase() : '?'}
    </div>
  );
};
