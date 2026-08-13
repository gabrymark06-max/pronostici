"""I contratti in entrata e in uscita.

REGOLA: NESSUNA ROTTA RESTITUISCE UN MODELLO DEL DATABASE. Esce sempre uno di
questi schemi, e `hash_password` non compare in nessuno. Se un giorno qualcuno
aggiungesse un campo riservato alla tabella, non finirebbe in una risposta per
distrazione: dovrebbe scriverlo qui a mano.

LA PASSWORD HA UN MINIMO DI DODICI CARATTERI E NESSUN OBBLIGO DI SIMBOLI. Le
regole di composizione — «almeno una maiuscola, un numero e un carattere
speciale» — producono `Password1!` e sono state ritirate dalle linee guida
NIST proprio per questo. La lunghezza e' l'unica cosa che conta davvero, e il
massimo di 128 c'e' solo per non far masticare ad Argon2 un megabyte.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegistrazioneIn(BaseModel):
    email: EmailStr
    nome: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalizza(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("nome")
    @classmethod
    def _pulisci(cls, v: str) -> str:
        pulito = " ".join(v.split())
        if not pulito:
            raise ValueError("il nome non puo' essere solo spazi")
        return pulito

    @field_validator("password")
    @classmethod
    def _non_banale(cls, v: str) -> str:
        # Un controllo solo, e utile: una password fatta di un carattere
        # ripetuto passa qualunque regola di lunghezza.
        if len(set(v)) < 5:
            raise ValueError("password troppo ripetitiva")
        return v


class AccessoIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalizza(cls, v: str) -> str:
        return v.strip().lower()


class CambioPasswordIn(BaseModel):
    password_attuale: str = Field(min_length=1, max_length=128)
    password_nuova: str = Field(min_length=12, max_length=128)


class ChiusuraContoIn(BaseModel):
    """Chiudere il conto chiede la password. Non e' un fastidio: e' l'unica
    cosa che impedisce a chi trovasse una sessione aperta di cancellare tutto."""

    password: str = Field(min_length=1, max_length=128)


class UtenteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    nome: str
    email_verificata: bool
    creato: datetime
    ultimo_accesso: datetime | None


class SessioneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    creata: datetime
    scade: datetime
    agente: str | None
    # `True` sulla sessione da cui arriva la richiesta: senza, nella pagina
    # «dove sei collegato» non si capisce quale riga sia il proprio browser.
    corrente: bool = False


class Fatto(BaseModel):
    """Per le rotte che non hanno niente da restituire. Meglio di `204 No
    Content`: il frontend legge sempre un corpo JSON, senza un ramo a parte."""

    fatto: bool = True
