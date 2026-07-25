from datetime import date as dt_date, datetime
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
    date: Optional[dt_date] = None


class TransactionOut(BaseModel):
    id_transaction: int
    id_compte: int
    id_categorie: Optional[int]
    montant: Decimal
    type: str
    description: Optional[str]
    date: dt_date
    est_recurrente: bool
    est_suspecte: bool
    id_transaction_annulee: Optional[int]
    date_creation: datetime

    class Config:
        from_attributes = True


FrequenceRecurrence = Literal["HEBDOMADAIRE", "MENSUELLE", "TRIMESTRIELLE", "ANNUELLE"]


class TransactionRecurrenteCreate(BaseModel):
    id_compte: int
    id_categorie: int
    montant: Decimal = Field(..., gt=0)
    type: TypeTransactionCreable
    description: Optional[str] = None
    frequence: FrequenceRecurrence
    prochaine_execution: dt_date
    date_fin: Optional[dt_date] = None


class TransactionRecurrenteUpdate(BaseModel):
    # Le compte, la catégorie et le type ne sont volontairement pas
    # modifiables ici : changer le compte source d'un prélèvement
    # automatique est une nouvelle récurrence, pas une modification.
    montant: Optional[Decimal] = Field(default=None, gt=0)
    description: Optional[str] = None
    frequence: Optional[FrequenceRecurrence] = None
    prochaine_execution: Optional[dt_date] = None
    date_fin: Optional[dt_date] = None


class TransactionRecurrenteOut(BaseModel):
    id_transaction_recurrente: int
    id_compte: int
    id_categorie: int
    montant: Decimal
    type: str
    description: Optional[str]
    frequence: str
    prochaine_execution: dt_date
    date_fin: Optional[dt_date]
    est_active: bool
    date_creation: datetime

    class Config:
        from_attributes = True


class TemplateTransactionCreate(BaseModel):
    id_compte: int
    id_categorie: int
    nom: str = Field(..., min_length=1, max_length=100)
    montant: Decimal = Field(..., gt=0)
    type: TypeTransactionCreable
    description: Optional[str] = None


class TemplateTransactionUpdate(BaseModel):
    id_compte: Optional[int] = None
    id_categorie: Optional[int] = None
    nom: Optional[str] = Field(default=None, min_length=1, max_length=100)
    montant: Optional[Decimal] = Field(default=None, gt=0)
    type: Optional[TypeTransactionCreable] = None
    description: Optional[str] = None


class TemplateTransactionOut(BaseModel):
    id_template: int
    id_compte: int
    id_categorie: int
    nom: str
    montant: Decimal
    type: str
    description: Optional[str]
    nombre_utilisations: int
    est_actif: bool
    date_creation: datetime
    date_modification: datetime

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
    date: dt_date
    date_creation: datetime

    class Config:
        from_attributes = True
