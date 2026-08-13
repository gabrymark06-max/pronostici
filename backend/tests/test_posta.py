"""Verifica dell'indirizzo e recupero della password.

COME SI PROVA SENZA SPEDIRE NIENTE. In sviluppo `posta.spedisci` non spedisce:
scrive il messaggio nei log. Qui si intercetta la stessa funzione e si tiene da
parte il messaggio, cosi' si puo' tirare fuori il collegamento e proseguire il
giro esattamente come farebbe una persona che apre l'email.

E' il motivo per cui `posta.spedisci` prende un oggetto `Messaggio` invece di
comporre la mail dentro le rotte: cosi' il pezzo da intercettare e' uno solo.
"""

from __future__ import annotations

import re

import pytest
import pytest_asyncio

BUONA = "una-password-varia"


@pytest_asyncio.fixture
async def posta_finta(monkeypatch):
    """Trattiene i messaggi invece di spedirli, e li restituisce."""
    from centro_profili import posta
    from centro_profili.rotte import profili

    spediti: list[posta.Messaggio] = []

    async def trattieni(m: posta.Messaggio) -> None:
        spediti.append(m)

    # Va sostituita nel MODULO CHE LA USA, non solo dove e' definita: le rotte
    # fanno `from .. import posta` e poi `posta.spedisci(...)`, quindi si passa
    # per l'attributo del modulo `posta` — che e' lo stesso oggetto. Sostituire
    # `profili.posta.spedisci` e `posta.spedisci` e' la stessa cosa, e si fa
    # cosi' per renderlo evidente a chi legge.
    monkeypatch.setattr(profili.posta, "spedisci", trattieni)
    return spediti


def collegamento(messaggio) -> str:
    trovato = re.search(r"https?://\S+", messaggio.testo)
    assert trovato, f"nessun collegamento nel messaggio:\n{messaggio.testo}"
    return trovato.group(0)


def gettone_da(messaggio) -> str:
    return collegamento(messaggio).split("g=", 1)[1]


async def registra(cliente, email="tizio@esempio.it", nome="Tizio", password=BUONA):
    return await cliente.post(
        "/profili/registrazione",
        json={"email": email, "nome": nome, "password": password},
    )


# ------------------------------------------------------------------ #
# Verifica dell'indirizzo                                            #
# ------------------------------------------------------------------ #


async def test_la_registrazione_spedisce_la_conferma(cliente, posta_finta):
    r = await registra(cliente)
    assert r.status_code == 201
    assert r.json()["email_verificata"] is False
    assert len(posta_finta) == 1
    assert posta_finta[0].a == "tizio@esempio.it"
    assert "/verifica/" in collegamento(posta_finta[0])


async def test_il_collegamento_conferma_l_indirizzo(cliente, posta_finta):
    await registra(cliente)
    g = gettone_da(posta_finta[0])

    r = await cliente.post("/profili/verifica", json={"gettone": g})
    assert r.status_code == 200
    assert r.json()["email_verificata"] is True


async def test_la_verifica_non_richiede_di_essere_collegati(cliente, posta_finta):
    """Chi apre l'email puo' farlo dal telefono o dopo giorni."""
    await registra(cliente)
    g = gettone_da(posta_finta[0])
    cliente.cookies.clear()

    assert (await cliente.post("/profili/verifica", json={"gettone": g})).status_code == 200


async def test_il_gettone_vale_una_volta_sola(cliente, posta_finta):
    await registra(cliente)
    g = gettone_da(posta_finta[0])
    assert (await cliente.post("/profili/verifica", json={"gettone": g})).status_code == 200

    r = await cliente.post("/profili/verifica", json={"gettone": g})
    assert r.status_code == 400
    assert r.json()["errore"]["codice"] == "gettone_non_valido"


async def test_un_gettone_inventato_non_vale(cliente, posta_finta):
    await registra(cliente)
    r = await cliente.post("/profili/verifica", json={"gettone": "x" * 43})
    assert r.status_code == 400


async def test_il_rinvio_annulla_il_collegamento_di_prima(cliente, posta_finta):
    """Due collegamenti vivi insieme raddoppiano la finestra in cui uno rubato
    apre, e non servono a niente."""
    await registra(cliente)
    primo = gettone_da(posta_finta[0])

    assert (await cliente.post("/profili/verifica/invio")).status_code == 200
    secondo = gettone_da(posta_finta[1])
    assert primo != secondo

    assert (
        await cliente.post("/profili/verifica", json={"gettone": primo})
    ).status_code == 400
    assert (
        await cliente.post("/profili/verifica", json={"gettone": secondo})
    ).status_code == 200


async def test_non_si_rispedisce_a_chi_ha_gia_confermato(cliente, posta_finta):
    await registra(cliente)
    await cliente.post("/profili/verifica", json={"gettone": gettone_da(posta_finta[0])})

    r = await cliente.post("/profili/verifica/invio")
    assert r.status_code == 409
    assert r.json()["errore"]["codice"] == "email_gia_verificata"


async def test_il_rinvio_e_limitato(cliente, posta_finta):
    """Senza limite, un profilo diventa un modo di spedire posta a raffica da
    un dominio che non e' il proprio."""
    await registra(cliente)
    for _ in range(3):
        await cliente.post("/profili/verifica/invio")
    r = await cliente.post("/profili/verifica/invio")
    assert r.status_code == 429


# ------------------------------------------------------------------ #
# Recupero della password                                            #
# ------------------------------------------------------------------ #


async def test_il_recupero_spedisce_il_collegamento(cliente, posta_finta):
    await registra(cliente)
    posta_finta.clear()

    r = await cliente.post("/profili/recupero", json={"email": "tizio@esempio.it"})
    assert r.status_code == 200
    assert len(posta_finta) == 1
    assert "/recupero/conferma/" in collegamento(posta_finta[0])


async def test_il_recupero_non_dice_se_l_indirizzo_esiste(cliente, posta_finta):
    """La stessa risposta, parola per parola, e nessuna email spedita."""
    await registra(cliente)
    posta_finta.clear()

    esiste = await cliente.post("/profili/recupero", json={"email": "tizio@esempio.it"})
    posta_finta.clear()
    non_esiste = await cliente.post("/profili/recupero", json={"email": "nessuno@esempio.it"})

    assert esiste.status_code == non_esiste.status_code == 200
    assert esiste.json() == non_esiste.json()
    assert posta_finta == [], "a un indirizzo sconosciuto non si spedisce niente"


async def test_il_collegamento_reimposta_la_password(cliente, posta_finta):
    await registra(cliente)
    posta_finta.clear()
    await cliente.post("/profili/recupero", json={"email": "tizio@esempio.it"})
    g = gettone_da(posta_finta[0])

    r = await cliente.post(
        "/profili/recupero/conferma",
        json={"gettone": g, "password_nuova": "la-password-nuova"},
    )
    assert r.status_code == 200

    vecchia = await cliente.post(
        "/profili/accesso", json={"email": "tizio@esempio.it", "password": BUONA}
    )
    assert vecchia.status_code == 401
    nuova = await cliente.post(
        "/profili/accesso",
        json={"email": "tizio@esempio.it", "password": "la-password-nuova"},
    )
    assert nuova.status_code == 200


async def test_reimpostare_caccia_fuori_tutte_le_sessioni(cliente, posta_finta):
    """Chi reimposta lo fa quasi sempre perche' teme che qualcuno sia entrato:
    quel qualcuno deve uscire, e subito."""
    await registra(cliente)
    intruso_accesso = cliente.cookies["centro_accesso"]
    intruso_rinnovo = cliente.cookies["centro_rinnovo"]

    posta_finta.clear()
    await cliente.post("/profili/recupero", json={"email": "tizio@esempio.it"})
    await cliente.post(
        "/profili/recupero/conferma",
        json={
            "gettone": gettone_da(posta_finta[0]),
            "password_nuova": "la-password-nuova",
        },
    )

    cliente.cookies.clear()
    cliente.cookies.set("centro_accesso", intruso_accesso)
    assert (await cliente.get("/profili/io")).status_code == 401

    cliente.cookies.clear()
    cliente.cookies.set("centro_rinnovo", intruso_rinnovo)
    assert (await cliente.post("/profili/rinnovo")).status_code == 401


async def test_reimpostare_non_apre_una_sessione(cliente, posta_finta):
    """Se il collegamento fosse stato intercettato, l'intruso non deve
    ritrovarsi una sessione aperta in mano: deve conoscere la password."""
    await registra(cliente)
    posta_finta.clear()
    await cliente.post("/profili/recupero", json={"email": "tizio@esempio.it"})
    cliente.cookies.clear()

    r = await cliente.post(
        "/profili/recupero/conferma",
        json={
            "gettone": gettone_da(posta_finta[0]),
            "password_nuova": "la-password-nuova",
        },
    )
    assert r.status_code == 200
    assert (await cliente.get("/profili/io")).status_code == 401


async def test_reimpostare_conferma_anche_l_indirizzo(cliente, posta_finta):
    """Il gettone e' arrivato in quella casella: l'indirizzo e' provato."""
    await registra(cliente)
    posta_finta.clear()
    await cliente.post("/profili/recupero", json={"email": "tizio@esempio.it"})
    await cliente.post(
        "/profili/recupero/conferma",
        json={
            "gettone": gettone_da(posta_finta[0]),
            "password_nuova": "la-password-nuova",
        },
    )
    r = await cliente.post(
        "/profili/accesso",
        json={"email": "tizio@esempio.it", "password": "la-password-nuova"},
    )
    assert r.json()["email_verificata"] is True


async def test_il_gettone_di_recupero_vale_una_volta_sola(cliente, posta_finta):
    await registra(cliente)
    posta_finta.clear()
    await cliente.post("/profili/recupero", json={"email": "tizio@esempio.it"})
    g = gettone_da(posta_finta[0])

    assert (
        await cliente.post(
            "/profili/recupero/conferma",
            json={"gettone": g, "password_nuova": "la-password-nuova"},
        )
    ).status_code == 200
    r = await cliente.post(
        "/profili/recupero/conferma",
        json={"gettone": g, "password_nuova": "un-altra-ancora"},
    )
    assert r.status_code == 400


async def test_un_gettone_di_verifica_non_vale_per_il_recupero(cliente, posta_finta):
    """I due tipi non si scambiano: altrimenti chi riesce a farsi mandare una
    verifica potrebbe usarla per cambiare la password."""
    await registra(cliente)
    g = gettone_da(posta_finta[0])

    r = await cliente.post(
        "/profili/recupero/conferma",
        json={"gettone": g, "password_nuova": "la-password-nuova"},
    )
    assert r.status_code == 400


@pytest.mark.parametrize("password", ["corta", "aaaaaaaaaaaa"])
async def test_la_password_nuova_deve_reggere_le_stesse_regole(
    cliente, posta_finta, password
):
    await registra(cliente)
    posta_finta.clear()
    await cliente.post("/profili/recupero", json={"email": "tizio@esempio.it"})
    r = await cliente.post(
        "/profili/recupero/conferma",
        json={"gettone": gettone_da(posta_finta[0]), "password_nuova": password},
    )
    assert r.status_code == 422


async def test_dieci_caratteri_bastano(cliente, posta_finta):
    """Il minimo e' 10, non 12."""
    r = await registra(cliente, password="dieci-cara")
    assert len("dieci-cara") == 10
    assert r.status_code == 201


async def test_nove_caratteri_non_bastano(cliente, posta_finta):
    r = await registra(cliente, password="nove-cara")
    assert r.status_code == 422
