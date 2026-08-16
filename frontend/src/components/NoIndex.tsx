import React from 'react';
import { Helmet } from 'react-helmet-async';

// Empêche l'indexation des zones authentifiées (dashboard client, admin) —
// en complément de robots.txt, qui bloque le crawl mais ne garantit pas
// à lui seul qu'une page déjà liée ailleurs reste hors des résultats.
export const NoIndex: React.FC = () => (
  <Helmet>
    <meta name="robots" content="noindex, nofollow" />
  </Helmet>
);
