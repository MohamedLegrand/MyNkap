// Service d'appel de l'API REST
import { API_URL } from '../config';
import { useAuthStore } from '../store';

// Endpoints d'authentification eux-mêmes : jamais de tentative de
// rafraîchissement automatique dessus (un 401 y a un sens propre — ex.
// mauvais mot de passe — et retenter via /auth/refresh boucherait sans fin
// si le refresh token est lui aussi invalide).
const ROUTES_AUTH_SANS_RETRY = ['/auth/login', '/auth/google', '/auth/verify-otp', '/auth/refresh', '/auth/register'];

// Une seule requête de rafraîchissement à la fois, partagée par tous les
// appels qui essuient un 401 en même temps (évite une tempête d'appels
// concurrents à /auth/refresh, qui ferait tourner le refresh token plusieurs
// fois pour un seul jeton expiré).
let rafraichissementEnCours: Promise<string | null> | null = null;

async function rafraichirAccessToken(): Promise<string | null> {
  if (!rafraichissementEnCours) {
    rafraichissementEnCours = (async () => {
      const { refreshToken } = useAuthStore.getState();
      if (!refreshToken) return null;

      try {
        const reponse = await fetch(`${API_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!reponse.ok) return null;

        const donnees = await reponse.json();
        // Le refresh token tourne à chaque appel côté backend (l'ancien est
        // révoqué) : il faut impérativement stocker le nouveau, sous peine
        // de session bloquée au prochain rafraîchissement.
        useAuthStore.getState().setSession(
          { accessToken: donnees.access_token, refreshToken: donnees.refresh_token },
          donnees.user_type === 'administrateur'
        );
        return donnees.access_token as string;
      } catch {
        return null;
      }
    })().finally(() => {
      rafraichissementEnCours = null;
    });
  }
  return rafraichissementEnCours;
}

const executerRequete = async (endpoint: string, options: RequestInit, accessToken: string | null) => {
  const headers = new Headers(options.headers);
  // FormData (envoi de fichier, ex: message vocal JARVIS) : ne jamais fixer
  // Content-Type nous-mêmes, le navigateur doit poser le boundary multipart
  // lui-même — l'écraser en "application/json" casserait l'upload.
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }
  return fetch(`${API_URL}${endpoint}`, { ...options, headers });
};

export const api = {
  // Méthode de base pour effectuer des requêtes fetch avec gestion du token JWT
  async request<T = unknown>(endpoint: string, options: RequestInit = {}): Promise<T> {
    let { accessToken } = useAuthStore.getState();
    let response = await executerRequete(endpoint, options, accessToken);

    // Un access token expire au bout de 30 min (voir ACCESS_TOKEN_EXPIRE_MINUTES) :
    // sans ce rattrapage, toute session active se serait mise à échouer en
    // silence sur son premier appel après expiration. Une seule tentative de
    // rafraîchissement, jamais sur les routes d'auth elles-mêmes.
    const estRouteAuthSansRetry = ROUTES_AUTH_SANS_RETRY.some((route) => endpoint.startsWith(route));
    if (response.status === 401 && !estRouteAuthSansRetry) {
      const nouveauAccessToken = await rafraichirAccessToken();
      if (nouveauAccessToken) {
        accessToken = nouveauAccessToken;
        response = await executerRequete(endpoint, options, accessToken);
      } else {
        // Refresh token lui-même invalide/expiré : la session ne peut plus
        // être récupérée, on la ferme localement (les gardes de route
        // redirigent alors vers /login).
        useAuthStore.getState().logout();
      }
    }

    if (!response.ok) {
      let message = response.statusText;
      try {
        const body = await response.json();
        if (body?.detail) message = body.detail;
      } catch {
        // Le corps de la réponse n'est pas du JSON exploitable, on garde le statusText.
      }
      throw new Error(message);
    }

    if (response.status === 204) {
      return null as T;
    }
    return response.json();
  },
};
