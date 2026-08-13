"""Password e gettoni.

LE PASSWORD CON ARGON2, non bcrypt. bcrypt tronca silenziosamente a 72 byte:
una passphrase lunga viene accettata, tagliata, e chi la usa crede di avere una
password lunga mentre ne ha una di 72 byte. Argon2id non tronca, ed e' quello
che oggi si raccomanda.

IL CONFRONTO E' SEMPRE A TEMPO COSTANTE, e si esegue ANCHE quando l'utente non
esiste (vedi `verifica_finta`). Senza, il tempo di risposta racconta a chi
prova quali email sono registrate: 3 millisecondi vuol dire «non esiste», 60
vuol dire «esiste, password sbagliata». E' un'enumerazione di utenti fatta col
cronometro, e non costa niente evitarla.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from .impostazioni import impostazioni

_hasher = PasswordHasher()

# Un hash di comodo, calcolato una volta all'avvio. Serve a bruciare lo stesso
# tempo anche quando l'email non esiste. Vedi la nota in testa al modulo.
_FINTO = _hasher.hash("una password che non e' di nessuno")

Tipo = Literal["accesso", "rinnovo"]


def cifra(password: str) -> str:
    return _hasher.hash(password)


def verifica(hash_salvato: str, password: str) -> bool:
    try:
        _hasher.verify(hash_salvato, password)
        return True
    except (VerifyMismatchError, VerificationError):
        return False


def verifica_finta(password: str) -> None:
    """Brucia il tempo di una verifica vera. Non restituisce niente apposta:
    non c'e' un esito da guardare, c'e' solo un tempo da spendere."""
    with suppress(VerifyMismatchError, VerificationError):
        _hasher.verify(_FINTO, password)


def da_riconiare(hash_salvato: str) -> bool:
    """`True` quando i parametri di Argon2 sono cambiati da quando questo hash
    e' stato calcolato. Si ricalcola al primo accesso riuscito, che e' l'unico
    momento in cui la password in chiaro passa di qui."""
    return _hasher.check_needs_rehash(hash_salvato)


# ------------------------------------------------------------------ #
# Gettoni                                                            #
# ------------------------------------------------------------------ #


def conia(
    utente_id: uuid.UUID,
    tipo: Tipo,
    generazione: int,
    jti: uuid.UUID | None = None,
) -> tuple[str, datetime]:
    """Il gettone e la sua scadenza.

    `tipo` finisce DENTRO il gettone e viene controllato quando si legge: senza,
    un gettone di rinnovo — che dura trenta giorni — varrebbe come gettone
    d'accesso, e i quindici minuti di vita corta non servirebbero a niente.
    """
    imp = impostazioni()
    adesso = datetime.now(UTC)
    scade = adesso + (
        timedelta(minutes=imp.minuti_accesso)
        if tipo == "accesso"
        else timedelta(days=imp.giorni_rinnovo)
    )
    corpo = {
        "sub": str(utente_id),
        "tipo": tipo,
        # La generazione delle credenziali. Vedi `modelli.Utente.generazione`.
        "gen": generazione,
        "iat": int(adesso.timestamp()),
        "exp": int(scade.timestamp()),
        "jti": str(jti or uuid.uuid4()),
    }
    return jwt.encode(corpo, imp.chiave_jwt, algorithm="HS256"), scade


class GettoneNonValido(Exception):
    pass


def leggi(gettone: str, atteso: Tipo) -> dict:
    """Il contenuto del gettone, se la firma torna, non e' scaduto ED e' del
    tipo giusto. Altrimenti alza."""
    try:
        corpo = jwt.decode(gettone, impostazioni().chiave_jwt, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise GettoneNonValido(str(exc)) from exc
    if corpo.get("tipo") != atteso:
        raise GettoneNonValido(f"gettone di tipo {corpo.get('tipo')!r}, atteso {atteso!r}")
    return corpo


# --------------------------------------------------------------------------- #
# I gettoni che viaggiano per posta                                           #
# --------------------------------------------------------------------------- #


def gettone_email() -> tuple[str, str]:
    """`(gettone, impronta)`.

    Il gettone finisce nell'email, l'impronta nel database. Chi legge il
    database non puo' risalire al gettone; chi presenta il gettone si ritrova
    con la stessa impronta e si fa riconoscere.

    `token_urlsafe(32)` sono 256 bit di casualita' da `secrets`, che e' il
    generatore crittografico — non `random`, che e' prevedibile e serve ad
    altro. Quarantatre caratteri stanno in un indirizzo senza codifica.
    """
    grezzo = secrets.token_urlsafe(32)
    return grezzo, impronta_di(grezzo)


def impronta_di(gettone: str) -> str:
    """SHA-256 in esadecimale. Vedi il commento su `modelli.GettoneEmail`:
    qui non serve un hash lento, perche' non c'e' niente da indovinare."""
    return hashlib.sha256(gettone.encode("utf-8")).hexdigest()
