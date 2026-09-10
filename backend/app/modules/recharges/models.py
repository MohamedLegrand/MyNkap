from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class RechargeCompte(Base):
    """
    Recharge Mobile Money réelle (Cash-In HR-Skills Pay) qui crédite un
    compte financier du client — miroir de plans.models.PaiementAbonnement,
    mais pour alimenter un compte au lieu de souscrire un abonnement. Le
    compte n'est crédité qu'une fois SUCCESS confirmé (voir
    recharges.service.verifier_recharges_en_attente) : `id_transaction`
    reste NULL tant que ce n'est pas le cas.
    """
    __tablename__ = "recharges_compte"

    id_recharge = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_compte = Column(Integer, ForeignKey("comptes_financiers.id_compte"), nullable=False, index=True)
    montant = Column(Numeric(14, 2), nullable=False)
    devise = Column(String, default="XAF", nullable=False)
    # Code pays HR-Skills Pay (ex. "CM", "SN") — même rôle que
    # PaiementAbonnement.pays, traçabilité du rail Mobile Money employé.
    # "CM" fixe pour une recharge carte (rail carte : XAF uniquement).
    pays = Column(String, nullable=False)
    # MOBILE_MONEY (Cash-In SDK hrpay) ou CARTE (API E-NKAP, page hébergée).
    methode = Column(String, nullable=False, default="MOBILE_MONEY", server_default="MOBILE_MONEY")
    # Référence HR-Skills Pay : Transaction.reference (Mobile Money) ou
    # "card_xxxx" (carte). Colonne unique commune aux deux rails.
    reference_hrpay = Column(String, unique=True, nullable=False, index=True)
    # Montant réellement débité sur la carte, commission incluse (gross-up,
    # voir service.initier_recharge_carte). NULL pour le Mobile Money, où le
    # client paie exactement `montant`.
    montant_facture = Column(Numeric(14, 2), nullable=True)
    # URL de la page de paiement hébergée Flocash (carte uniquement). NULL
    # pour le Mobile Money, ou pour une carte gelée en revue anti-fraude.
    checkout_url = Column(String, nullable=True)
    statut = Column(String, default="PENDING", nullable=False)  # PENDING, SUCCESS, FAILED
    id_transaction = Column(Integer, ForeignKey("transactions.id_transaction"), nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_confirmation = Column(DateTime, nullable=True)

    client = relationship("Client")
    compte = relationship("CompteFinancier")
    transaction = relationship("Transaction")
