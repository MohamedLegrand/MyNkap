// Store d'authentification global (zustand + persistance localStorage)
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Client } from '../types';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  client: Client | null;
  isAuthenticated: boolean;
  setSession: (tokens: { accessToken: string; refreshToken: string }) => void;
  setClient: (client: Client) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      client: null,
      isAuthenticated: false,
      setSession: ({ accessToken, refreshToken }) =>
        set({ accessToken, refreshToken, isAuthenticated: true }),
      setClient: (client) => set({ client }),
      logout: () =>
        set({ accessToken: null, refreshToken: null, client: null, isAuthenticated: false }),
    }),
    { name: 'mynkap-auth' }
  )
);
