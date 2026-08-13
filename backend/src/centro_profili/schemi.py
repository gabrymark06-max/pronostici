"""I contratti in entrata e in uscita.

REGOLA: NESSUNA ROTTA RESTITUISCE UN MODELLO DEL DATABASE. Esce sempre uno di
questi schemi, e `hash_password` non compare in nessuno. Se un giorno qualcuno
aggiungesse un campo riservato alla tabella, non finirebbe in una risposta per
distrazione: dovrebbe scriverlo qui a mano.

LA PASSWORD HA UN MINIMO DI DIECI CARATTERI E NESSUN OBBLIGO DI SIMBOLI. Le
regole di composizione — «almeno una maiuscola, un numero e un carattere
speciale» — producono `Password1!` e sono state ritirate dalle linee guida
NIST proprio per questo. La lunghezza e' l'unica cosa che conta davvero, e il
massimo di 128 c'e' solo per non far masticare ad Argon2 un megabyte.

Il minimo sta in `MINIMO_PASSWORD` e non ripetuto in ogni schema: e' lo stesso
numero in tre posti — registrazione, cambio password, recupero — e tre copie
sono tre occasioni di cambiarne due.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

MINIMO_PASSWORD = 10
MASSIMO_PASSWORD = 128


def _controlla_password(v: str) -> str:
    """Un controllo solo, e utile: una password fatta di pochi caratteri
    ripetuti passa qualunque regola di lunghezza."""
    if len(set(v)) < 5:
        raise ValueError("password troppo ripetitiva")
    return v


# UN TIPO SOLO PER TUTTE E TRE LE PASSWORD NUOVE.
#
# Le password nuove si scelgono in tre punti — registrazione, cambio password,
# recupero — e le regole devono essere le stesse. Non lo erano: il validatore
# stava solo sulla registrazione, e dal recupero si poteva scegliere una
# password che la registrazione rifiuta. Trovato da una prova, non a occhio.
#
# Con un tipo annotato la regola sta in un posto e viaggia con il campo: una
# quarta rotta che chieda una password nuova la eredita per forza, invece di
# doversi ricordare di ripetere il validatore.
PasswordNuova = Annotated[
    str,
    Field(min_length=MINIMO_PASSWORD, max_length=MASSIMO_PASSWORD),
    AfterValidator(_controlla_password),
]

# Quella che si presenta per farsi riconoscere non ha regole: e' gia' stata
# accettata quando e' stata scelta, e imporgliele adesso significherebbe
# chiudere fuori chi ha un profilo piu' vecchio delle regole di oggi.
PasswordEsistente = Annotated[str, Field(min_length=1, max_length=MASSIMO_PASSWORD)]


class RegistrazioneIn(BaseModel):
    email: EmailStr
    nome: str = Field(min_length=2, max_length=60)
    password: PasswordNuova

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

class AccessoIn(BaseModel):
    email: EmailStr
    password: PasswordEsistente

    @field_validator("email")
    @classmethod
    def _normalizza(cls, v: str) -> str:
        return v.strip().lower()


class CambioPasswordIn(BaseModel):
    password_attuale: PasswordEsistente
    password_nuova: PasswordNuova


class ChiusuraProfiloIn(BaseModel):
    """Chiudere il profilo chiede la password. Non e' un fastidio: e' l'unica
    cosa che impedisce a chi trovasse una sessione aperta di cancellare tutto."""

    password: PasswordEsistente


class RecuperoIn(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _normalizza(cls, v: str) -> str:
        return v.strip().lower()


class ConfermaRecuperoIn(BaseModel):
    gettone: str = Field(min_length=16, max_length=128)
    password_nuova: PasswordNuova


class ConfermaVerificaIn(BaseModel):
    gettone: str = Field(min_length=16, max_length=128)


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
