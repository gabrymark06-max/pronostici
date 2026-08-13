"""Job 4-ter — `sofascore`: attacca formazioni, arbitro e quote estese.

    python -m pronostici.jobs.sofascore --window-days 4
    python -m pronostici.jobs.sofascore --dry-run

COSA SCRIVE. Un solo campo, `sofascore`, su ogni partita futura che riesce ad
agganciare. Dentro ci sono tre cose che il resto della pipeline non ha:

  * l'ARBITRO designato, con il suo storico disciplinare;
  * le FORMAZIONI, con scritto se sono probabili o gia' ufficiali;
  * le QUOTE su mercati che la fonte attuale non copre — cartellini nella
    partita, calci d'angolo, prima squadra a segnare, primo tempo.

COSA NON TOCCA, MAI. `prediction`, `silence`, `phase`, `source`,
`model_weight`, `reasons`, il registro. Non partecipa alla decisione: quella
resta dove sta, sul modello e sulle quote di mercato gia' cablate. Qui si
aggiunge contesto, e il contesto non vota.

PERCHE' LE FORMAZIONI VANNO RIPRESE PIU' VOLTE. Compaiono come PROBABILI e
diventano UFFICIALI vicino al calcio d'inizio. Il campo `confermate` dice quale
delle due si sta guardando, e questo job va fatto girare piu' di una volta al
giorno per le partite imminenti se si vuole la versione definitiva.

QUANDO L'AGGANCIO FALLISCE. La partita resta senza il campo `sofascore` e il
motivo finisce nel report. Non si inventa niente per riempire il buco: una
scheda senza formazioni e' onesta, una scheda con le formazioni di un'altra
partita e' un disastro invisibile.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from .. import fixtures as fx
from ..sources import sofascore as sf

log = logging.getLogger("pronostici.sofascore")

# Pausa fra una partita e l'altra. Sofascore non pubblica un limite di
# frequenza; questa e' cortesia, non obbligo, e tiene il job lontano da
# qualunque soglia non dichiarata.
PAUSA_S = 0.4

# Oltre questa distanza le formazioni non esistono ancora e l'arbitro spesso
# nemmeno: si spenderebbero chiamate per riscrivere blocchi vuoti.
FINESTRA_DEFAULT = 4


def _giorni(finestra: int, oggi: str) -> list[str]:
    base = datetime.strptime(oggi, "%Y-%m-%d").replace(tzinfo=UTC)
    return [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(finestra + 1)]


# DA MERCATO SOFASCORE ALLE NOSTRE CHIAVI.
#
# Solo cio' che si mappa SENZA INTERPRETARE. Sono quattro famiglie:
#
#   Full time            -> 1x2_home / 1x2_draw / 1x2_away
#   Double chance        -> dc_1x / dc_x2 / dc_12
#   Both teams to score  -> btts_yes / btts_no
#   Match goals + linea  -> over_<L> / under_<L>
#
# Restano fuori, e non per pigrizia:
#
#   * «1st half» rimanda tre esiti di cui DUE si chiamano `X`. Un mercato che
#     non sa nominare i propri esiti non si mappa: qualunque scelta sarebbe
#     un'ipotesi su quale dei due sia il vero `1`;
#   * handicap asiatico, calci d'angolo, cartellini, prima squadra a segnare:
#     il nostro catalogo non ha la chiave corrispondente, quindi non c'e'
#     niente contro cui confrontarli. Restano visibili in «altri mercati»,
#     dove non fingono di essere paragonabili al nostro numero.
_ESITI_1X2 = {"1": "1x2_home", "X": "1x2_draw", "2": "1x2_away"}
_ESITI_DC = {"1X": "dc_1x", "X2": "dc_x2", "12": "dc_12"}
_ESITI_BTTS = {"Yes": "btts_yes", "No": "btts_no"}
# Le linee che il nostro catalogo conosce. Le altre (0,5, 6,5...) esistono su
# Sofascore ma non da noi: mapparle creerebbe chiavi che nessuno legge.
_LINEE_GOL = {"2.5", "3.5"}


def _chiavi_del_mercato(mercato: dict) -> dict[str, float]:
    """Le probabilita' implicite di un mercato, con le NOSTRE chiavi.

    Vuoto quando il mercato non e' mappabile: e' il caso normale, non un
    errore.
    """
    nome = (mercato.get("mercato") or "").strip()
    linea = (mercato.get("linea") or "").strip()
    fuori: dict[str, float] = {}

    for esito in mercato.get("esiti") or []:
        p = esito.get("probabilita_implicita")
        if not isinstance(p, (int, float)) or not 0 < p < 1:
            continue
        nome_esito = (esito.get("esito") or "").strip()
        chiave: str | None = None
        if nome == "Full time":
            chiave = _ESITI_1X2.get(nome_esito)
        elif nome == "Double chance":
            chiave = _ESITI_DC.get(nome_esito)
        elif nome == "Both teams to score":
            chiave = _ESITI_BTTS.get(nome_esito)
        elif nome == "Match goals" and linea in _LINEE_GOL:
            if nome_esito == "Over":
                chiave = f"over_{linea}"
            elif nome_esito == "Under":
                chiave = f"under_{linea}"
        if chiave:
            fuori[chiave] = float(p)
    return fuori


def _market_p(quote: dict) -> dict[str, float]:
    """Probabilita' di mercato SGONFIATE, dalle quote Sofascore.

    La probabilita' implicita di un prezzo contiene il margine: su un mercato
    completo le implicite sommano a piu' di 1 — 1,05 significa un margine del
    cinque per cento. Dividere ognuna per la somma toglie il margine in modo
    proporzionale, che e' la normalizzazione piu' semplice e l'unica difendibile
    senza assumere come l'operatore distribuisce il margine fra gli esiti.
    E' la stessa cosa che il progetto fa gia' sulle quote dell'altra fonte.

    Un mercato con un solo esito leggibile NON si sgonfia: normalizzarlo
    darebbe probabilita' 1, cioe' certezza, che e' l'opposto di quello che
    quel prezzo dice.
    """
    fuori: dict[str, float] = {}
    for mercato in quote.get("mercati") or []:
        chiavi = _chiavi_del_mercato(mercato)
        if len(chiavi) < 2:
            continue
        somma = sum(chiavi.values())
        if not 0.9 < somma < 1.6:
            # Somma implausibile: quote sospese, o un mercato incompleto letto
            # a meta'. Meglio saltarlo che pubblicare un numero storto.
            continue
        for k, p in chiavi.items():
            fuori[k] = round(p / somma, 5)
    return fuori


def _senza_ora(blocco: dict) -> dict:
    """Il blocco senza `letto`, per confrontare la sostanza e non il momento."""
    return {k: v for k, v in blocco.items() if k != "letto"}


def _blocco(
    scheda: dict, evento_id: int, torneo: str, as_of: str, *, ore_prima: float | None = None
) -> dict:
    """Riduce la scheda del CLI al blocco che finisce nel file.

    Si tiene poco e con criterio: la scheda grezza porta anche cose che la
    pagina non usa, e un file di fixture non e' un archivio della fonte.
    """
    blocco: dict = {
        "evento_id": evento_id,
        "torneo": torneo,
        "letto": as_of,
    }

    arbitro = scheda.get("arbitro")
    if isinstance(arbitro, dict) and arbitro.get("nome"):
        blocco["arbitro"] = {
            "nome": arbitro["nome"],
            "paese": arbitro.get("paese"),
            "partite": arbitro.get("partite_arbitrate"),
            "gialli": arbitro.get("cartellini_gialli"),
            "rossi": arbitro.get("cartellini_rossi"),
            "gialli_per_partita": arbitro.get("gialli_per_partita"),
        }
        if arbitro.get("stadio"):
            blocco["stadio"] = arbitro["stadio"]

    form = scheda.get("formazioni")
    if isinstance(form, dict) and (form.get("casa") or {}).get("titolari"):
        # QUANTO PRIMA sono state lette. Sofascore pubblica formazioni PREVISTE
        # con giorni d'anticipo, e le marca `confermate: false` esattamente come
        # quelle probabili di un'ora prima del fischio. Lo stesso campo copre
        # due gradi di affidabilita' molto diversi: una previsione a tre giorni
        # e' un'ipotesi sulla rosa, una a un'ora e' quasi la formazione vera.
        #
        # Il numero si registra QUI, che e' il momento in cui e' vero. La pagina
        # lo usa per dire «probabili, lette tre giorni prima» invece di
        # appiattire tutto su «probabili».
        blocco["formazioni"] = {
            "confermate": bool(form.get("confermate")),
            "ore_prima": round(ore_prima, 1) if ore_prima is not None else None,
            "casa": {
                "modulo": (form.get("casa") or {}).get("modulo"),
                "titolari": (form.get("casa") or {}).get("titolari", []),
                "panchina": (form.get("casa") or {}).get("panchina", []),
            },
            "ospiti": {
                "modulo": (form.get("ospiti") or {}).get("modulo"),
                "titolari": (form.get("ospiti") or {}).get("titolari", []),
                "panchina": (form.get("ospiti") or {}).get("panchina", []),
            },
        }

    quote = scheda.get("quote")
    if isinstance(quote, dict) and quote.get("mercati"):
        blocco["quote"] = {
            "n_mercati": quote.get("n_mercati"),
            "mercati": quote.get("mercati", []),
        }
        # Le stesse quote tradotte nelle nostre chiavi e sgonfiate: e' quello
        # che riempie la colonna «il mercato» sulle partite che la fonte
        # principale non copre. Sta in un campo suo, e non dentro `odds`,
        # perche' la provenienza non si mescola: la pagina deve poter dire da
        # dove viene il numero che mostra.
        mp = _market_p(quote)
        if mp:
            blocco["market_p"] = mp

    mancanti = scheda.get("parti_mancanti")
    if isinstance(mancanti, dict) and mancanti:
        blocco["parti_mancanti"] = mancanti
    return blocco


def run(
    *,
    finestra: int = FINESTRA_DEFAULT,
    dry_run: bool = False,
    oggi: str | None = None,
) -> dict:
    started = time.monotonic()
    adesso = datetime.now(UTC)
    oggi = oggi or adesso.strftime("%Y-%m-%d")
    as_of = adesso.strftime("%Y-%m-%dT%H:%M:%SZ")

    report: dict = {
        "generated_at": as_of,
        "finestra_giorni": finestra,
        "esaminate": 0,
        "agganciate": 0,
        "con_formazioni": 0,
        "con_arbitro": 0,
        "con_quote": 0,
        "non_agganciate": [],
        "days_written": [],
        "dry_run": dry_run,
    }

    if not sf.disponibile():
        report["errore"] = (
            f"binario Sofascore assente ({sf.percorso_cli()}): il job si spegne senza scrivere"
        )
        log.warning(report["errore"])
        report["seconds"] = round(time.monotonic() - started, 1)
        return report

    cache = sf._carica_cache()
    per_giorno: dict[str, list[dict]] = defaultdict(list)

    for giorno in _giorni(finestra, oggi):
        esistente = fx.load_day(giorno)
        if not esistente:
            continue
        for entry in esistente.get("fixtures", []):
            # Il fischio d'inizio congela: dopo, formazioni e quote non sono
            # piu' informazione pre-partita e non vanno riscritte.
            try:
                calcio = datetime.fromisoformat(entry["utc_date"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if calcio <= adesso:
                continue

            report["esaminate"] += 1
            aggancio = sf.aggancia(
                entry["home"]["name"], entry["away"]["name"], entry["utc_date"], cache=cache
            )
            time.sleep(PAUSA_S)

            if aggancio.evento_id is None:
                report["non_agganciate"].append(
                    {
                        "match_id": entry["match_id"],
                        "partita": f"{entry['home']['name']} - {entry['away']['name']}",
                        "motivo": aggancio.motivo,
                    }
                )
                continue

            try:
                scheda = sf.scheda(aggancio.evento_id)
            except sf.SofascoreNonDisponibile as exc:
                report["non_agganciate"].append(
                    {
                        "match_id": entry["match_id"],
                        "partita": f"{entry['home']['name']} - {entry['away']['name']}",
                        "motivo": f"scheda non letta: {exc}",
                    }
                )
                continue
            time.sleep(PAUSA_S)

            blocco = _blocco(
                scheda,
                aggancio.evento_id,
                aggancio.torneo,
                as_of,
                ore_prima=(calcio - adesso).total_seconds() / 3600,
            )
            report["agganciate"] += 1
            if "formazioni" in blocco:
                report["con_formazioni"] += 1
            if "arbitro" in blocco:
                report["con_arbitro"] += 1
            if "quote" in blocco:
                report["con_quote"] += 1

            # Si riscrive solo se e' cambiato qualcosa di SOSTANZA. `letto`
            # cambia a ogni giro per costruzione e non e' una novita': se
            # entrasse nel confronto, ogni esecuzione riscriverebbe tutti i
            # file e il registro delle modifiche diventerebbe illeggibile.
            precedente = entry.get("sofascore") or {}
            if _senza_ora(blocco) == _senza_ora(precedente):
                continue
            per_giorno[giorno].append({**entry, "sofascore": blocco})

    sf._salva_cache(cache)

    if not dry_run:
        for giorno, aggiornate in per_giorno.items():
            # `generated_at` vuole un datetime: serve a `upsert_day` per
            # decidere quali partite sono gia' iniziate, non come etichetta.
            if aggiornate and fx.upsert_day(giorno, aggiornate, generated_at=adesso):
                report["days_written"].append(giorno)

    report["seconds"] = round(time.monotonic() - started, 1)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Formazioni, arbitro e quote estese da Sofascore")
    parser.add_argument("--window-days", type=int, default=FINESTRA_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--today", default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = run(finestra=args.window_days, dry_run=args.dry_run, oggi=args.today)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if not report.get("errore") else 1


if __name__ == "__main__":
    raise SystemExit(main())
