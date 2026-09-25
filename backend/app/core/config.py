from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "MyNkap Backend"
    API_V1_STR: str = "/api/v1"

    # "development" ou "production" — contrôle l'exposition de la
    # documentation interactive (Swagger/ReDoc, voir main.py) : inutile de
    # publier tout le plan de l'API (routes admin incluses) à quiconque en
    # production, alors que ça reste pratique en développement.
    ENVIRONMENT: str = "development"

    # Base de données
    DATABASE_URL: str = "postgresql://postgres:123@localhost:5432/mynkap"

    @property
    def sync_database_url(self) -> str:
        # Gère les cas où les bases de données (comme Supabase/Render) utilisent le protocole postgres://
        if self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return self.DATABASE_URL

    # Sécurité
    # Pas de valeur par défaut : doit être fournie via .env (voir .env.example).
    # Génération : python -c "import secrets; print(secrets.token_urlsafe(64))"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS : origines autorisées à appeler l'API (séparées par des virgules dans .env)
    # 5175 est le port fixe du frontend MyNkap, voir frontend/vite.config.ts.
    CORS_ORIGINS: str = "http://localhost:5175"

    # IP directes (séparées par des virgules) depuis lesquelles X-Forwarded-For
    # est considéré fiable — typiquement le reverse-proxy local (Nginx sur le
    # même VPS, voir core/ip_client.py). Toute requête arrivant d'une IP hors
    # de cette liste voit son X-Forwarded-For ignoré : sans ce filtre,
    # n'importe quel client peut usurper l'en-tête pour se faire passer pour
    # une IP différente à chaque appel et contourner la limite de débit par
    # IP (confirmé exploitable en audit : register/login/forgot-password/OTP
    # illimités avec une IP usurpée différente à chaque requête).
    TRUSTED_PROXY_IPS: str = "127.0.0.1,::1"

    # Broker/backend Celery (tâches de fond : transactions récurrentes...)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Fournisseurs IA (module JARVIS, à venir) — optionnelles : rien ne les
    # consomme encore, un clone du dépôt sans ces clés doit rester capable
    # de lancer l'app et les tests.
    GROQ_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    # Paiement Mobile Money (module Plans/Abonnement) — optionnelles, même
    # raison que ci-dessus.
    HRPAY_PUBLIC_KEY: str | None = None
    HRPAY_SECRET_KEY: str | None = None

    # --- Paiement par carte bancaire (E-NKAP via HR-Skills Pay) ---
    # API REST distincte du SDK Mobile Money (hrpay ne la couvre pas) : page
    # de paiement hébergée chez Flocash, le client est redirigé puis revient
    # sur return_url/cancel_url, le statut réel se lit via l'API (polling,
    # comme le Mobile Money). Réutilise les mêmes clés HRPAY_* (mêmes
    # identifiants marchand). Voir app/core/hrpay_card.py.
    HRPAY_CARD_BASE_URL: str = "https://api.hrskills-pay.com"
    # true → préfixe /sandbox sur chaque route + clés de test hrsk_*_test_
    # (aucun appel réel à E-NKAP). Passer à false en production.
    HRPAY_SANDBOX: bool = True
    # Commission carte : plancher strict de 3,5 % côté plateforme
    # (fee = amount × taux). Sert au « gross-up » : le client règle le
    # montant voulu + les frais, le compte/abonnement est crédité du montant
    # voulu (voir recharges.service.initier_recharge_carte).
    HRPAY_CARD_TAUX_COMMISSION: float = 0.035
    # Secret de signature des webhooks carte (en-tête X-Hub-Signature).
    # Laissé vide pour l'instant : la confirmation passe par la relecture du
    # statut (polling). À renseigner le jour où le webhook sera activé.
    HRPAY_WEBHOOK_SECRET: str | None = None

    # Envoi d'e-mails transactionnels (mot de passe oublié...) via l'API
    # REST Brevo — optionnelle, même raison que ci-dessus (sans clé, on
    # retombe sur une simulation console, cf. auth.services).
    BREVO_API_KEY: str | None = None
    MAIL_FROM_EMAIL: str = "no-reply@mynkap.com"
    MAIL_FROM_NAME: str = "MyNkap"

    # Base du frontend, utilisée pour construire les liens envoyés par e-mail
    # (ex: /reset-password?token=...).
    FRONTEND_URL: str = "http://localhost:5175"

    # OAuth Google (Se connecter avec Google) — optionnelles, même raison
    # que les autres clés fournisseur ci-dessus. GOOGLE_CLIENT_SECRET n'est
    # pas utilisé par la vérification du jeton d'identité (audience seule
    # via GOOGLE_CLIENT_ID, voir auth.services._verifier_id_token_google) ;
    # conservé pour un futur flux d'échange de code côté serveur.
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    # Dossier de stockage des rapports PDF générés (module Rapports).
    # Chemin local pour l'instant — un stockage cloud (S3/Supabase) sera
    # nécessaire en production, sans changer l'API du module.
    RAPPORTS_DOSSIER: str = "rapports_generes"

    # Dossier de stockage des photos de profil (module Auth/Profile) — même
    # limitation que RAPPORTS_DOSSIER ci-dessus (stockage local, cloud à
    # prévoir en production). Servi via StaticFiles, voir main.py.
    AVATARS_DOSSIER: str = "avatars_uploads"

    # Base publique du backend, utilisée pour construire l'URL absolue des
    # photos de profil hébergées localement (même principe que FRONTEND_URL
    # pour les liens envoyés par e-mail).
    BACKEND_URL: str = "http://localhost:8000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def trusted_proxy_ips_list(self) -> list[str]:
        return [ip.strip() for ip in self.TRUSTED_PROXY_IPS.split(",") if ip.strip()]

    @property
    def hrpay_card_api_base(self) -> str:
        """
        URL de base des routes carte, préfixe /sandbox inclus en mode
        sandbox (doc E-NKAP : même host, pas d'URL séparée — c'est le
        préfixe de chemin qui bascule sur l'environnement de test).
        """
        base = self.HRPAY_CARD_BASE_URL.rstrip("/")
        return f"{base}/sandbox" if self.HRPAY_SANDBOX else base

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
