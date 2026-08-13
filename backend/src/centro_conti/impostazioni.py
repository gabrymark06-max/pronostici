"""Le impostazioni, tutte da variabili d'ambiente e in un posto solo.

REGOLA DURA DEL PROGETTO: nessun segreto letterale nel codice. Il repository e'
pubblico, e una chiave scritta in un sorgente e' compromessa nel momento in cui
viene committata — anche se la togli dopo, resta nella storia.

Qui dentro non ci sono valori predefiniti per le cose segrete: se manca
`CHIAVE_JWT` o `DATABASE_URL` l'applicazione NON PARTE, e dice quale variabile
manca. Un valore di ripiego per una chiave di firma e' peggio di un errore: fa
partire in produzione un sistema che chiunque abbia letto il codice sa firmare.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Impostazioni(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Identita' del servizio ------------------------------------------- #
    nome: str = "Centro — conti"
    ambiente: Literal["sviluppo", "produzione"] = "sviluppo"

    # --- Dati -------------------------------------------------------------- #
    # Nessun valore predefinito: senza database non c'e' niente da servire, e
    # un ripiego su SQLite farebbe partire in produzione un sistema che perde
    # tutto al primo riavvio del contenitore.
    database_url: str = Field(..., description="postgresql+asyncpg://...")

    # --- Firma dei gettoni -------------------------------------------------- #
    chiave_jwt: str = Field(..., min_length=32)
    minuti_accesso: int = 15
    giorni_rinnovo: int = 30

    # --- Chi puo' chiamarci ------------------------------------------------- #
    # Allowlist ESPLICITA, mai `*`. Con `allow_credentials` il carattere jolly
    # e' rifiutato dai browser, e a ragione: significherebbe che qualunque
    # sito puo' fare richieste autenticate a nome di chi e' collegato.
    #
    # `NoDecode` NON E' DECORATIVO. Senza, `pydantic-settings` prova a leggere
    # dall'ambiente qualunque campo di tipo lista COME JSON, e lo fa PRIMA dei
    # validatori: `ORIGINI=https://a.it,https://b.it` — la forma che si scrive
    # in un pannello di hosting, e quella documentata in `.env.example` —
    # esplodeva con «Expecting value: line 1 column 1» all'avvio, prima ancora
    # che `_origini_da_stringa` qui sotto potesse vederla. Con `NoDecode` il
    # valore grezzo arriva al validatore, che e' il posto in cui volevamo
    # deciderne la forma.
    origini: Annotated[list[str], NoDecode] = [
        "http://localhost:4330",
        "http://localhost:3000",
    ]

    # --- Cookie -------------------------------------------------------------- #
    # In sviluppo frontend e API stanno entrambi su `localhost`, che per il
    # browser e' lo stesso sito: `lax` basta e non serve HTTPS.
    # In produzione stanno su due domini diversi (il sito su un hosting statico,
    # l'API altrove) e il cookie DEVE essere `none` + `secure`, altrimenti il
    # browser non lo manda e l'accesso non dura oltre il caricamento.
    cookie_samesite: Literal["lax", "none", "strict"] = "lax"
    cookie_secure: bool = False
    cookie_dominio: str | None = None

    # --- Limiti ------------------------------------------------------------- #
    tentativi_accesso: int = 8
    tentativi_registrazione: int = 5
    finestra_limite_s: int = 900

    @field_validator("origini", mode="before")
    @classmethod
    def _origini_da_stringa(cls, v: object) -> object:
        """`ORIGINI=https://a.it,https://b.it` — la forma che si scrive in un
        pannello di hosting, dove non esistono le liste."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @field_validator("origini")
    @classmethod
    def _mai_jolly(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError(
                "ORIGINI non puo' contenere '*': con i cookie di sessione il "
                "jolly e' rifiutato dai browser, ed e' giusto cosi'."
            )
        return v


@lru_cache
def impostazioni() -> Impostazioni:
    """Lette una volta sola. Se manca qualcosa, `pydantic` dice cosa."""
    return Impostazioni()  # type: ignore[call-arg]
