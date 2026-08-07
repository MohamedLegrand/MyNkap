import React, { useState } from 'react';
import { AppRoutes } from './routes';
import { SplashScreen } from './components/SplashScreen';
import './index.css';

// Distingue une vraie nouvelle visite (URL saisie, lien externe, nouvel
// onglet) d'un simple rechargement de page (F5 / Ctrl+R) via la
// Navigation Timing API — l'écran de démarrage ne doit rejouer que dans
// le premier cas, jamais sur un rafraîchissement.
const estUneNouvelleVisite = (): boolean => {
  try {
    const [entree] = performance.getEntriesByType('navigation') as PerformanceNavigationTiming[];
    return entree?.type !== 'reload';
  } catch {
    // API indisponible (navigateur très ancien) : on affiche quand même,
    // par défaut, plutôt que de risquer de ne jamais l'afficher.
    return true;
  }
};

const App: React.FC = () => {
  // App ne se monte qu'une fois par vrai chargement du site dans le
  // navigateur (jamais lors d'une navigation interne via React Router) —
  // l'écran de démarrage ne se rejoue donc qu'à une vraie nouvelle visite,
  // jamais sur un simple rafraîchissement de page.
  const [splashTermine, setSplashTermine] = useState(() => !estUneNouvelleVisite());

  return (
    <div className="min-h-screen bg-background text-foreground">
      {!splashTermine && <SplashScreen onComplete={() => setSplashTermine(true)} />}
      <AppRoutes />
    </div>
  );
};

export default App;
