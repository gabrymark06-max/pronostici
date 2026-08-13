"""Le prove dei conti.

Non provano che il codice giri: provano le DECISIONI. Ogni cosa scritta nel
commento in testa a `rotte/conti.py` ha qui sotto una prova che fallisce se
qualcuno la disfa senza accorgersene — l'errore d'accesso indistinguibile, la
rotazione del gettone, il cambio password che caccia fuori gli altri.
"""

from __future__ import annotations

import pytest

BUONA = "una-password-lunga-e-varia"


async def registra(cliente, email="tizio@esempio.it", nome="Tizio", password=BUONA):
    return await cliente.post(
        "/conti/registrazione", json={"email": email, "nome": nome, "password": password}
    )


# ------------------------------------------------------------------ #
# Registrazione                                                      #
# ------------------------------------------------------------------ #


async def test_registrazione_crea_il_conto_e_apre_la_sessione(cliente):
    r = await registra(cliente)
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["email"] == "tizio@esempio.it"
    assert corpo["nome"] == "Tizio"
    # I due cookie sono stati posati.
    assert "centro_accesso" in r.cookies
    assert "centro_rinnovo" in r.cookies


async def test_la_risposta_non_contiene_mai_la_password(cliente):
    r = await registra(cliente)
    assert "hash_password" not in r.text
    assert BUONA not in r.text


async def test_i_gettoni_non_sono_nel_corpo(cliente):
    """I gettoni stanno nei cookie `httpOnly` e in nessun altro posto."""
    r = await registra(cliente)
    assert "token" not in r.text.lower()
    assert "eyJ" not in r.text  # il prefisso di un JWT in base64


async def test_email_normalizzata(cliente):
    r = await registra(cliente, email="  Tizio@Esempio.IT  ")
    assert r.status_code == 201
    assert r.json()["email"] == "tizio@esempio.it"
    # E il maiuscolo non permette un secondo conto sulla stessa casella.
    doppione = await registra(cliente, email="TIZIO@ESEMPIO.IT")
    assert doppione.status_code == 409


async def test_email_gia_presa_non_viene_confermata(cliente):
    await registra(cliente)
    r = await registra(cliente, nome="Un altro")
    assert r.status_code == 409
    corpo = r.json()["errore"]
    assert corpo["codice"] == "registrazione_non_completata"
    # DECISIONE 2: il messaggio non dice «questa email esiste».
    assert "esiste" not in corpo["dettaglio"].lower()
    assert "già registrat" not in corpo["dettaglio"].lower()


@pytest.mark.parametrize(
    "password", ["corta", "aaaaaaaaaaaaaaaa", "12345678901"]
)
async def test_password_deboli_rifiutate(cliente, password):
    r = await registra(cliente, password=password)
    assert r.status_code == 422
    assert r.json()["errore"]["codice"] == "dati_non_validi"


async def test_errore_di_validazione_ha_la_stessa_busta(cliente):
    """FastAPI ne userebbe una sua: qui deve essere quella di tutti."""
    r = await cliente.post("/conti/registrazione", json={"email": "non-una-email"})
    assert r.status_code == 422
    assert set(r.json()["errore"]) >= {"codice", "dettaglio"}


# ------------------------------------------------------------------ #
# Accesso                                                            #
# ------------------------------------------------------------------ #


async def test_accesso_riuscito(cliente):
    await registra(cliente)
    r = await cliente.post(
        "/conti/accesso", json={"email": "tizio@esempio.it", "password": BUONA}
    )
    assert r.status_code == 200
    assert r.json()["ultimo_accesso"] is not None


async def test_utente_inesistente_e_password_sbagliata_sono_indistinguibili(cliente):
    """DECISIONE 1: la stessa risposta, parola per parola."""
    await registra(cliente)
    inesistente = await cliente.post(
        "/conti/accesso", json={"email": "nessuno@esempio.it", "password": BUONA}
    )
    sbagliata = await cliente.post(
        "/conti/accesso", json={"email": "tizio@esempio.it", "password": "un-altra-password"}
    )
    assert inesistente.status_code == sbagliata.status_code == 401
    assert inesistente.json() == sbagliata.json()
    assert inesistente.json()["errore"]["codice"] == "credenziali_non_valide"


async def test_troppi_tentativi_chiudono_fuori(cliente):
    await registra(cliente)
    for _ in range(8):
        await cliente.post(
            "/conti/accesso", json={"email": "tizio@esempio.it", "password": "sbagliata-1"}
        )
    r = await cliente.post(
        "/conti/accesso", json={"email": "tizio@esempio.it", "password": "sbagliata-1"}
    )
    assert r.status_code == 429
    assert r.json()["errore"]["codice"] == "troppi_tentativi"
    assert "Retry-After" in r.headers


async def test_il_limite_non_conta_gli_accessi_riusciti(cliente):
    await registra(cliente)
    for _ in range(12):
        r = await cliente.post(
            "/conti/accesso", json={"email": "tizio@esempio.it", "password": BUONA}
        )
        assert r.status_code == 200, "un accesso riuscito non deve consumare tentativi"


# ------------------------------------------------------------------ #
# Sessione                                                           #
# ------------------------------------------------------------------ #


async def test_io_richiede_l_accesso(cliente):
    r = await cliente.get("/conti/io")
    assert r.status_code == 401
    assert r.json()["errore"]["codice"] == "non_autenticato"


async def test_io_dopo_l_accesso(cliente):
    await registra(cliente)
    r = await cliente.get("/conti/io")
    assert r.status_code == 200
    assert r.json()["email"] == "tizio@esempio.it"


async def test_il_gettone_di_rinnovo_non_vale_come_accesso(cliente):
    """Il campo `tipo` dentro il gettone serve esattamente a questo."""
    await registra(cliente)
    rinnovo = cliente.cookies["centro_rinnovo"]
    cliente.cookies.clear()
    cliente.cookies.set("centro_accesso", rinnovo)
    r = await cliente.get("/conti/io")
    assert r.status_code == 401


async def test_rinnovo_ruota_il_gettone(cliente):
    """DECISIONE 3: usato una volta, il vecchio non vale piu'."""
    await registra(cliente)
    vecchio = cliente.cookies["centro_rinnovo"]

    r = await cliente.post("/conti/rinnovo")
    assert r.status_code == 200
    assert cliente.cookies["centro_rinnovo"] != vecchio

    # Il vecchio, riproposto, non entra.
    cliente.cookies.set("centro_rinnovo", vecchio)
    r = await cliente.post("/conti/rinnovo")
    assert r.status_code == 401
    assert r.json()["errore"]["codice"] == "sessione_scaduta"


async def test_uscita_invalida_la_sessione(cliente):
    await registra(cliente)
    rinnovo = cliente.cookies["centro_rinnovo"]
    assert (await cliente.post("/conti/uscita")).status_code == 200

    # Anche riesumando il cookie a mano, quella sessione non esiste piu'.
    cliente.cookies.set("centro_rinnovo", rinnovo)
    assert (await cliente.post("/conti/rinnovo")).status_code == 401


async def test_uscita_funziona_anche_senza_sessione(cliente):
    """Non deve fallire quando il gettone era gia' marcio: chi clicca «esci»
    deve uscire, non ricevere un errore."""
    assert (await cliente.post("/conti/uscita")).status_code == 200


async def test_sessioni_elenca_e_segna_quella_corrente(cliente):
    await registra(cliente)
    await cliente.post("/conti/rinnovo")
    r = await cliente.get("/conti/sessioni")
    assert r.status_code == 200
    righe = r.json()
    assert len(righe) == 1, "la rotazione non deve lasciare sessioni orfane"
    assert righe[0]["corrente"] is True


# ------------------------------------------------------------------ #
# Password e chiusura                                                #
# ------------------------------------------------------------------ #


async def test_cambio_password_richiede_quella_attuale(cliente):
    await registra(cliente)
    r = await cliente.post(
        "/conti/password",
        json={
            "password_attuale": "quella-sbagliata",
            "password_nuova": "una-nuova-lunghissima",
        },
    )
    assert r.status_code == 403
    assert r.json()["errore"]["codice"] == "password_attuale_errata"


async def test_cambio_password_caccia_fuori_gli_altri(cliente, app_e_db):
    """E' il motivo per cui uno cambia la password."""
    await registra(cliente)
    altrove = cliente.cookies["centro_rinnovo"]  # un secondo browser, in finta
    await cliente.post("/conti/rinnovo")  # il primo browser va avanti per conto suo

    r = await cliente.post(
        "/conti/password",
        json={"password_attuale": BUONA, "password_nuova": "un-altra-password-lunga"},
    )
    assert r.status_code == 200

    # Chi ha cambiato resta dentro...
    assert (await cliente.get("/conti/io")).status_code == 200
    # ...e la sessione dell'altro browser e' morta.
    cliente.cookies.set("centro_rinnovo", altrove)
    assert (await cliente.post("/conti/rinnovo")).status_code == 401


async def test_il_gettone_di_accesso_gia_emesso_smette_di_valere(cliente):
    """La prova che mancava, e che un browser vero ha smascherato.

    Cancellare le sessioni toglie i gettoni di RINNOVO. Quelli d'ACCESSO sono
    firmati e valgono fino alla scadenza: senza uno spartiacque, dopo un cambio
    password l'altro browser restava dentro fino a quindici minuti — e
    quindici minuti sono un'eternita' nel momento in cui uno cambia la password
    perche' teme che qualcuno sia entrato.

    Qui si tiene da parte il gettone d'accesso di prima, si cambia la password,
    e si verifica che quel gettone non apra piu' niente.
    """
    await registra(cliente)
    vecchio_accesso = cliente.cookies["centro_accesso"]

    r = await cliente.post(
        "/conti/password",
        json={"password_attuale": BUONA, "password_nuova": "un-altra-password-lunga"},
    )
    assert r.status_code == 200

    # Il browser dell'intruso ha solo il gettone d'accesso di prima.
    cliente.cookies.clear()
    cliente.cookies.set("centro_accesso", vecchio_accesso)
    fuori = await cliente.get("/conti/io")
    assert fuori.status_code == 401, "il gettone d'accesso di prima non deve valere piu'"


async def test_uscita_ovunque_invalida_anche_i_gettoni_di_accesso(cliente):
    await registra(cliente)
    vecchio_accesso = cliente.cookies["centro_accesso"]
    assert (await cliente.post("/conti/uscita-ovunque")).status_code == 200

    cliente.cookies.clear()
    cliente.cookies.set("centro_accesso", vecchio_accesso)
    assert (await cliente.get("/conti/io")).status_code == 401


async def test_chi_cambia_la_password_non_si_butta_fuori_da_solo(cliente):
    """Lo spartiacque e' troncato al secondo proprio per questo: con i
    microsecondi il gettone coniato nello stesso istante risulterebbe piu'
    vecchio dello spartiacque."""
    await registra(cliente)
    r = await cliente.post(
        "/conti/password",
        json={"password_attuale": BUONA, "password_nuova": "un-altra-password-lunga"},
    )
    assert r.status_code == 200
    assert (await cliente.get("/conti/io")).status_code == 200


async def test_la_password_nuova_funziona_e_la_vecchia_no(cliente):
    await registra(cliente)
    await cliente.post(
        "/conti/password",
        json={"password_attuale": BUONA, "password_nuova": "un-altra-password-lunga"},
    )
    await cliente.post("/conti/uscita")

    vecchia = await cliente.post(
        "/conti/accesso", json={"email": "tizio@esempio.it", "password": BUONA}
    )
    assert vecchia.status_code == 401
    nuova = await cliente.post(
        "/conti/accesso",
        json={"email": "tizio@esempio.it", "password": "un-altra-password-lunga"},
    )
    assert nuova.status_code == 200


async def test_chiusura_cancella_davvero(cliente, app_e_db):
    from sqlalchemy import func, select

    from centro_conti.modelli import Sessione as SessioneDb
    from centro_conti.modelli import Utente

    _, fabbrica = app_e_db
    await registra(cliente)

    r = await cliente.post("/conti/chiusura", json={"password": BUONA})
    assert r.status_code == 200

    async with fabbrica() as db:
        quanti = (await db.execute(select(func.count()).select_from(Utente))).scalar_one()
        sessioni = (
            await db.execute(select(func.count()).select_from(SessioneDb))
        ).scalar_one()
    assert quanti == 0, "il conto deve sparire, non restare disattivato"
    assert sessioni == 0, "le sessioni devono seguirlo per cascata"

    # E la stessa email torna libera.
    assert (await registra(cliente)).status_code == 201


async def test_chiusura_richiede_la_password(cliente):
    await registra(cliente)
    r = await cliente.post("/conti/chiusura", json={"password": "non-e-questa"})
    assert r.status_code == 403


# ------------------------------------------------------------------ #
# Il servizio                                                        #
# ------------------------------------------------------------------ #


async def test_salute(cliente):
    r = await cliente.get("/salute")
    assert r.status_code == 200 and r.json() == {"stato": "va"}


async def test_openapi_dichiara_la_forma_dell_errore(cliente):
    """Il frontend legge di qui: se la forma non e' dichiarata, la indovina."""
    r = await cliente.get("/openapi.json")
    assert r.status_code == 200
    schemi = r.json()["components"]["schemas"]
    assert "Errore" in schemi
    assert set(schemi["CorpoErrore"]["properties"]) == {"codice", "dettaglio"}
