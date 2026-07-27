// Store d'authentification global (zustand + persistance localStorage)
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Client } from '../types';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  client: Client | null;
  isAdmin: boolean;
  isAuthenticated: boolean;
  setSession: (tokens: { accessToken: string; refreshToken: string }, isAdmin?: boolean) => void;
  setClient: (client: Client) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      client: null,
      isAdmin: false,
      isAuthenticated: false,
      setSession: ({ accessToken, refreshToken }, isAdmin = false) =>
        set({ accessToken, refreshToken, isAuthenticated: true, isAdmin }),
      setClient: (client) => set({ client }),
      logout: () =>
        set({ accessToken: null, refreshToken: null, client: null, isAdmin: false, isAuthenticated: false }),
    }),
    { name: 'mynkap-auth' }
  )
);
