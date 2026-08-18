import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppRoutes } from './index';
import { useAuthStore } from '../store';

describe('LoginPage', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, refreshToken: null, client: null, isAuthenticated: false });
    vi.restoreAllMocks();
  });

  it('affiche une erreur quand les identifiants sont invalides', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      statusText: 'Bad Request',
      status: 400,
      json: async () => ({ detail: 'Adresse e-mail ou mot de passe incorrect.' }),
    } as Response);

    window.history.pushState({}, '', '/login');
    render(<AppRoutes />);

    await userEvent.type(screen.getByLabelText(/adresse e-mail/i), 'jean@example.com');
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'mauvais-mdp');
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    expect(await screen.findByText(/adresse e-mail ou mot de passe incorrect/i)).toBeInTheDocument();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it('connecte directement avec des identifiants valides (plus de double authentification par OTP)', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch');

    // /auth/login renvoie directement les jetons de session.
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => ({
        access_token: 'token-abc',
        refresh_token: 'refresh-abc',
        token_type: 'bearer',
        expires_in: 1800,
        user_type: 'client',
      }),
    } as Response);
    // Puis /auth/me renvoie le profil client.
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => ({
        id_client: 1,
        email: 'jean@example.com',
        first_name: 'Jean',
        last_name: 'Dupont',
        phone: '+237600000000',
      }),
    } as Response);

    window.history.pushState({}, '', '/login');
    render(<AppRoutes />);

    await userEvent.type(screen.getByLabelText(/adresse e-mail/i), 'jean@example.com');
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'motdepasse123');
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(true));
    expect(useAuthStore.getState().accessToken).toBe('token-abc');
  });
});
