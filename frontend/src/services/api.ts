// Service d'appel de l'API REST
import { API_URL } from '../config';
import { useAuthStore } from '../store';

export const api = {
  // Méthode de base pour effectuer des requêtes fetch avec gestion du token JWT
  async request<T = unknown>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const { accessToken } = useAuthStore.getState();

    const headers = new Headers(options.headers);
    headers.set('Content-Type', 'application/json');
    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`);
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

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
