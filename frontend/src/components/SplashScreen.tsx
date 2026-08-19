import React, { useEffect, useState } from 'react';

interface SplashScreenProps {
  onComplete: () => void;
}

const TEXTE = 'MyNkap';

// Écran de démarrage affiché à chaque chargement de l'application dans le
// navigateur (voir App.tsx — au montage, donc à chaque fois qu'on saisit
// l'URL et qu'on charge le site, jamais rejoué sur une simple navigation
// interne via React Router) : le logo apparaît, puis "MyNkap" s'écrit
// lettre par lettre, assez lentement pour que l'effet soit bien visible.
export const SplashScreen: React.FC<SplashScreenProps> = ({ onComplete }) => {
  const [logoVisible, setLogoVisible] = useState(false);
  const [texteAffiche, setTexteAffiche] = useState('');
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    let annule = false;
    const attendre = (ms: number) =>
      new Promise<void>((resolve) => {
        setTimeout(resolve, ms);
      });

    const jouer = async () => {
      await attendre(200);
      if (annule) return;
      setLogoVisible(true);

      // Laisse la chute + le petit rebond à l'atterrissage se terminer
      // avant de commencer à écrire (voir la transition du logo ci-dessous).
      await attendre(900);
      if (annule) return;
      for (let i = 1; i <= TEXTE.length; i++) {
        if (annule) return;
        setTexteAffiche(TEXTE.slice(0, i));
        await attendre(220);
      }

      await attendre(800);
      if (annule) return;
      setVisible(false);

      await attendre(450);
      if (annule) return;
      onComplete();
    };

    jouer();
    return () => {
      annule = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const termine = texteAffiche.length === TEXTE.length;

  return (
    <div
      className={`fixed inset-0 z-[100] flex flex-col items-center justify-center bg-background transition-opacity duration-400 ${
        visible ? 'opacity-100' : 'opacity-0 pointer-events-none'
      }`}
    >
      <div
        className={`transition-all duration-700 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${
          logoVisible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-40'
        }`}
      >
        <img
          src="/logo.jpg"
          alt="MyNkap"
          className="h-24 w-24 rounded-2xl object-cover shadow-xl border border-border"
        />
      </div>
      <h1 className="mt-6 text-3xl sm:text-4xl font-black tracking-tight text-primary min-h-[2.75rem]">
        {texteAffiche}
        {!termine && texteAffiche.length > 0 && <span className="text-primary animate-pulse">▌</span>}
      </h1>
    </div>
  );
};
