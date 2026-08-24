"""Il contratto fra chi scrive i mercati e chi li mostra.

QUESTO E' IL GUASTO CHE HA GIA' SVUOTATO LA PAGINA. `lib/mercati-esteso.ts` ha
una regola dura e giusta: un mercato il cui nome non sa tradurre NON SI MOSTRA,
perche' un nome mai guardato puo' contenere qualunque cosa. Ma la fonte nuova
mandava nomi italiani («Doppia chance») e quella tabella conosceva solo quelli
inglesi di Sofascore («Double chance»): ogni mercato veniva scartato.

Il job diceva 43 partite con i mercati, i file di dati li contenevano, e la
sezione «Altri mercati» era vuota. Nessuno dei due lati era rotto — era rotto
l'accordo fra i due, e non c'era niente che lo controllasse.

Qui si controlla. Il test legge il file TypeScript: e' brutto, e vale comunque,
perche' l'alternativa e' scoprirlo aprendo il sito.
"""

from __future__ import annotations

import re
from pathlib import Path

from pronostici.sources import betexplorer as bx

TABELLA = Path(__file__).resolve().parents[1] / "frontend" / "lib" / "mercati-esteso.ts"


def _chiavi(nome_costante: str) -> set[str]:
    testo = TABELLA.read_text(encoding="utf-8")
    blocco = re.search(
        rf"const {nome_costante}: Record<[^>]+> = \{{(.*?)\n\}};", testo, re.S
    )
    assert blocco, f"{nome_costante} non trovata in mercati-esteso.ts"
    return {
        m.group(1) or m.group(2)
        # Le chiavi possono essere fra virgolette (`'1X':`) o nude (`X2:`), e
        # quelle nude possono contenere cifre: senza le cifre nella classe,
        # `X2` sfuggiva e il test accusava un buco che non c'era.
        for m in re.finditer(
            r"^\s*'([^']+)':|^\s*([A-Za-zÀ-ſ][A-Za-zÀ-ſ0-9]*):", blocco.group(1), re.M
        )
    }


def test_ogni_mercato_che_scriviamo_sa_essere_tradotto() -> None:
    attesi = {nome for nome, _, _ in bx.MERCATI.values()}
    noti = _chiavi("NOMI")
    assert attesi <= noti, f"la pagina scarterebbe: {sorted(attesi - noti)}"


def test_ogni_esito_che_scriviamo_sa_essere_tradotto() -> None:
    attesi = {e for _, colonne, _ in bx.MERCATI.values() for e in colonne}
    noti = _chiavi("ESITI")
    assert attesi <= noti, f"la pagina scarterebbe: {sorted(attesi - noti)}"


def test_la_doppia_chance_ha_la_stessa_copertura_dai_due_lati() -> None:
    """Il numero di esiti che si avverano sta scritto in due linguaggi.

    In Python decide come si sgonfiano le quote, in TypeScript come si legge il
    margine in pagina. Se divergono, la pagina accusa l'operatore di un margine
    doppio di quello vero — o glielo dimezza.
    """
    noti = _chiavi("COPERTURA")
    for nome, _, vincenti in bx.MERCATI.values():
        if vincenti > 1:
            perche = f"«{nome}» copre {vincenti} volte, ma COPERTURA non lo sa"
            assert nome in noti, perche
