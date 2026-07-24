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
    await userEvent.type(screen.getByLabelText(/mot de passe/i), 'mauvais-mdp');
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    expect(await screen.findByText(/adresse e-mail ou mot de passe incorrect/i)).toBeInTheDocument();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it('stocke la session et redirige vers le tableau de bord en cas de succès', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => ({
        access_token: 'token-abc',
        refresh_token: 'refresh-abc',
        token_type: 'bearer',
        expires_in: 3600,
      }),
    } as Response);

    window.history.pushState({}, '', '/login');
    render(<AppRoutes />);

    await userEvent.type(screen.getByLabelText(/adresse e-mail/i), 'jean@example.com');
    await userEvent.type(screen.getByLabelText(/mot de passe/i), 'motdepasse123');
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(true));
    expect(useAuthStore.getState().accessToken).toBe('token-abc');
  });
});
