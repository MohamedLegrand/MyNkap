from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NotificationOut(BaseModel):
    id_notification: int
    type: str
    titre: str
    message: str
    lien: Optional[str]
    est_lue: bool
    date_creation: datetime

    class Config:
        from_attributes = True


class NonLuesCountOut(BaseModel):
    non_lues: int


class MarquerLuesOut(BaseModel):
    nb_marquees: int
