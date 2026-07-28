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

  it('demande un code OTP apres des identifiants valides, puis stocke la session apres verification', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch');

    // Étape 1 : /auth/login renvoie une demande d'OTP, jamais de jetons directement.
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => ({ otp_requis: true, message: 'Un code a été envoyé.', expires_in: 300 }),
    } as Response);

    window.history.pushState({}, '', '/login');
    render(<AppRoutes />);

    await userEvent.type(screen.getByLabelText(/adresse e-mail/i), 'jean@example.com');
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'motdepasse123');
    await userEvent.click(screen.getByRole('button', { name: /se connecter/i }));

    expect(await screen.findByText(/double authentification/i)).toBeInTheDocument();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);

    // Étape 2 : /auth/verify-otp renvoie les vrais jetons, puis /auth/me le profil client.
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

    const digitInputs = screen.getAllByRole('textbox');
    expect(digitInputs).toHaveLength(6);
    for (let i = 0; i < 6; i++) {
      await userEvent.type(digitInputs[i], String(i + 1));
    }

    await userEvent.click(screen.getByRole('button', { name: /valider et accéder au dashboard/i }));

    await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(true));
    expect(useAuthStore.getState().accessToken).toBe('token-abc');
  });
});
