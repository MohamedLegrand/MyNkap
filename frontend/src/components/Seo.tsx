import React from 'react';
import { Helmet } from 'react-helmet-async';
import { useTranslation } from 'react-i18next';

interface SeoProps {
  title: string;
  description: string;
  // Chemin de la route (ex: '/', '/a-propos') — sert à construire l'URL
  // absolue exigée par og:url et le lien canonique.
  path: string;
}

const SITE_URL = 'https://my-nkap.com';
// Logo utilisé comme image de partage par défaut (Open Graph/Twitter Card) :
// pas encore de bannière dédiée 1200x630, à remplacer si une est créée.
const OG_IMAGE = `${SITE_URL}/logo.jpg`;

// Titre + description + Open Graph/Twitter Card par page (SEO) — remplace le
// <title>/<meta description> statiques et identiques sur toutes les routes
// qui vivaient dans index.html.
export const Seo: React.FC<SeoProps> = ({ title, description, path }) => {
  const { i18n } = useTranslation();
  const url = `${SITE_URL}${path}`;
  const locale = i18n.language === 'en' ? 'en_US' : 'fr_FR';
  const localeAlternate = i18n.language === 'en' ? 'fr_FR' : 'en_US';

  return (
    <Helmet>
      <title>{title}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={url} />

      <meta property="og:type" content="website" />
      <meta property="og:site_name" content="MyNkap" />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:url" content={url} />
      <meta property="og:image" content={OG_IMAGE} />
      <meta property="og:locale" content={locale} />
      <meta property="og:locale:alternate" content={localeAlternate} />

      {/* "summary" plutôt que "summary_large_image" : le logo actuel (450x360)
          n'a pas le ratio ~1.91:1 attendu pour une image pleine largeur. */}
      <meta name="twitter:card" content="summary" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={OG_IMAGE} />
    </Helmet>
  );
};
