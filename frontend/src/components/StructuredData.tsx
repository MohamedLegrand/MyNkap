import React from 'react';
import { Helmet } from 'react-helmet-async';
import { useTranslation } from 'react-i18next';

const SITE_URL = 'https://my-nkap.com';
const LOGO_URL = `${SITE_URL}/logo.jpg`;

// Données structurées JSON-LD (schema.org), rendues une seule fois sur la
// landing page — suffisant aux yeux de Google, pas besoin de les dupliquer
// sur chaque route. Pas d'aggregateRating : aucun avis réel n'existe
// encore, en inventer un violerait les consignes Google sur les données
// structurées (et exposerait à une pénalité manuelle).
export const StructuredData: React.FC = () => {
  const { t } = useTranslation();
  const description = t('seo.landing_description');

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        name: 'MyNkap',
        url: SITE_URL,
        logo: LOGO_URL,
        description,
        email: 'support@mynkap.com',
        areaServed: 'Afrique Centrale (zone CEMAC)',
      },
      {
        '@type': 'SoftwareApplication',
        name: 'MyNkap',
        applicationCategory: 'FinanceApplication',
        operatingSystem: 'Web',
        url: SITE_URL,
        description,
        offers: [
          { '@type': 'Offer', name: 'Gratuit', price: '0', priceCurrency: 'XAF' },
          { '@type': 'Offer', name: 'Essentiel', price: '1000', priceCurrency: 'XAF' },
          { '@type': 'Offer', name: 'Premium', price: '2500', priceCurrency: 'XAF' },
        ],
      },
    ],
  };

  return (
    <Helmet>
      <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
    </Helmet>
  );
};
