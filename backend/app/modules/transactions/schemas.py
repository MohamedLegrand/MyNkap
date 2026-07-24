from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field

# Seules DEPENSE/REVENU sont créables directement par le client. Les autres
# types (DEPOT_INITIAL, ANNULATION, REMBOURSEMENT_DETTE, ENCAISSEMENT_CREANCE)
# sont des écritures système générées par d'autres flux (création de compte,
# annulation, module Dettes).
TypeTransactionCreable = Literal["DEPENSE", "REVENU"]


class TransactionCreate(BaseModel):
    id_compte: int
    id_categorie: int
    montant: Decimal = Field(..., gt=0)
    type: TypeTransactionCreable
    description: Optional[str] = None
    date: Optional[date] = None


class TransactionOut(BaseModel):
    id_transaction: int
    id_compte: int
    id_categorie: Optional[int]
    montant: Decimal
    type: str
    description: Optional[str]
    date: date
    est_recurrente: bool
    est_suspecte: bool
    id_transaction_annulee: Optional[int]
    date_creation: datetime

    class Config:
        from_attributes = True


class TransfertCreate(BaseModel):
    id_compte_source: int
    id_compte_destination: int
    montant: Decimal = Field(..., gt=0)
    description: Optional[str] = None


class TransfertOut(BaseModel):
    id_transfert: int
    id_compte_source: int
    id_compte_destination: int
    montant: Decimal
    description: Optional[str]
    date: date
    date_creation: datetime

    class Config:
        from_attributes = True
