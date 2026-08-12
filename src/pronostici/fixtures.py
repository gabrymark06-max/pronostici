"""I file giornalieri di `data/fixtures/` — il contratto col frontend.

Un file per giorno, riscritto da piu' job (`score` scrive il preliminare,
`finalize` il definitivo, `settle` l'esito). Riscriverlo da zero a ogni
esecuzione perderebbe informazione, quindi la scrittura e' un **merge con tre
regole dure**, che sono le regole di prodotto del brief 7.2 tradotte in
codice:

* **non si retrocede mai** un pronostico definitivo a preliminare — se lo si
  facesse, un `score` notturno cancellerebbe la revisione del giorno prima;
* **niente scritture dopo il fischio d'inizio**, mai, per nessun motivo, se
  non l'esito;
* **niente sparisce**: una partita gia' presente nel file resta, anche se il
  job corrente non la ha ricalcolata.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .config import FIXTURES_DIR
from .storage import SCHEMA_VERSION, read_json, write_json

PHASE_RANK = {"preliminary": 0, "definitive": 1}

# Le probabilita' che la card di silenzio mostra "senza consiglio" (brief 8.4):
# chi voleva i numeri li ha, chi voleva un consiglio ha una risposta.
RAW_KEYS = (
    "1x2_home", "1x2_draw", "1x2_away", "over_2.5", "under_2.5", "btts_yes",
)


def build_payload(
    scored,
    phase: str,
    *,
    previous: dict[str, Any] | None = None,
    transition: str | None = None,
    odds_meta: dict[str, Any] | None = None,
) -> dict:
    """La forma che il frontend consuma.

    Il silenzio e' un tipo di prima classe, non un ramo `else`: ha il suo
    motivo e le sue probabilita' grezze. La fase precedente e' **contenuto**
    della scheda, non un metadato nascosto (brief 7.2).
    """
    sel = scored.selection
    match = scored.match
    payload: dict[str, Any] = {
        "match_id": match.match_id,
        "competition": match.competition,
        # La fase del torneo, solo quando c'e': il frontend la mostra al posto
        # del nome della competizione. Vedi `archive.Match.stage`.
        "stage": match.stage,
        "utc_date": match.utc_date,
        "matchday": match.matchday,
        "home": {
            "name": match.home_name,
            "tla": match.home_tla,
            "crest": match.home_crest,
        },
        "away": {
            "name": match.away_name,
            "tla": match.away_tla,
            "crest": match.away_crest,
        },
        "phase": phase,
        "source": scored.source,
        "model_weight": scored.model_weight,
        "expected_goals": {
            "home": round(scored.lam_home, 3),
            "away": round(scored.lam_away, 3),
        },
        "reasons": scored.reasons,
        "diagnostics": {
            "n_candidates": sel.n_candidates,
            "n_clusters": sel.n_clusters,
            "filter_bites": sel.filter_bites,
            "truncated_mass": float(f"{scored.truncated_mass:.3e}"),
        },
        "raw_probabilities": {
            key: round(scored.market_probabilities[key], 4)
            for key in RAW_KEYS
            if key in scored.market_probabilities
        },
    }
    if sel.pick is not None:
        payload["prediction"] = {
            **sel.pick.to_dict(),
            "cluster_members": sel.cluster_members,
            "runners_up": [c.to_dict() for c in sel.runners_up],
        }
        payload["silence"] = None
    else:
        payload["prediction"] = None
        payload["silence"] = {"reason": sel.silence_reason}
    if scored.half_time:
        payload["half_time"] = {k: round(v, 4) for k, v in scored.half_time.items()}
    if transition is not None:
        payload["transition"] = transition
    if previous is not None:
        payload["previous"] = {
            "phase": previous.get("phase"),
            "written_at": previous.get("written_at"),
            "market_key": previous.get("market_key"),
            "market_label": previous.get("market_label"),
            "p": previous.get("p"),
            "silence_reason": previous.get("silence_reason"),
        }
    if odds_meta is not None:
        payload["odds"] = odds_meta
    return payload


def day_path(day: str):
    return FIXTURES_DIR / f"{day}.json"


def load_day(day: str) -> dict[str, Any] | None:
    return read_json(day_path(day), default=None)


def _kickoff_passed(entry: dict, now: datetime) -> bool:
    raw = entry.get("utc_date")
    if not raw:
        return False
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")) <= now
    except ValueError:
        return False


def upsert_day(
    day: str,
    entries: list[dict],
    *,
    generated_at: datetime | None = None,
    allow_after_kickoff: bool = False,
) -> bool:
    """Fonde `entries` nel file del giorno. True se il file e' cambiato."""
    now = generated_at or datetime.now(UTC)
    existing = load_day(day) or {}
    merged: dict[int, dict] = {
        int(f["match_id"]): f for f in existing.get("fixtures", [])
    }

    for entry in entries:
        match_id = int(entry["match_id"])
        old = merged.get(match_id)
        if old is not None:
            if not allow_after_kickoff and _kickoff_passed(old, now):
                continue  # congelato al fischio d'inizio
            new_rank = PHASE_RANK.get(entry.get("phase", ""), 0)
            old_rank = PHASE_RANK.get(old.get("phase", ""), 0)
            if new_rank < old_rank:
                continue  # mai retrocedere il definitivo a preliminare
            entry = _conserva_campi_altrui(old, entry)
        merged[match_id] = entry

    fixtures = sorted(
        merged.values(), key=lambda f: (f.get("utc_date", ""), f["match_id"])
    )
    silent = sum(1 for f in fixtures if f.get("prediction") is None)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "date": day,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Il conteggio dichiarato in testa alla lista (brief 8.4): un sito
        # che conta i propri silenzi sembra severo, uno che li nasconde
        # sembra rotto.
        "silence_count": silent,
        "total": len(fixtures),
        "fixtures": fixtures,
    }

    # `generated_at` da solo non e' un cambiamento. Senza questo confronto ogni
    # esecuzione notturna produrrebbe un commit che non dice niente, e la
    # cronologia del registro - che e' la prova di pubblicazione - si
    # riempirebbe di rumore in cui il cambiamento vero non si trova piu'.
    if existing and _same_content(existing, payload):
        return False
    return write_json(day_path(day), payload)


# I campi che una partita porta ma che NON appartengono al job che la scrive.
# `score` costruisce il payload dal solo modello e non sa niente di quote o di
# risultati: senza questa lista, la sua scrittura notturna cancellava i prezzi
# che `jobs.quote` aveva attaccato la mattina prima. Il guasto era invisibile
# nella pipeline reale — `quote` gira alle 10:00 e li rimetteva — e si vedeva
# solo eseguendo `score` a mano, cioe' esattamente quando qualcuno guarda.
#
# La regola generale: chi riscrive una partita conserva cio' che non e' suo.
CAMPI_DI_ALTRI = ("odds", "result", "outcome")


def _conserva_campi_altrui(vecchio: dict, nuovo: dict) -> dict:
    """Riporta nel nuovo payload i campi che il chiamante non possiede.

    Solo se il nuovo non li porta: chi li porta li sta aggiornando davvero, e
    ha la precedenza.
    """
    mancanti = {
        campo: vecchio[campo]
        for campo in CAMPI_DI_ALTRI
        if campo in vecchio and nuovo.get(campo) is None
    }
    return {**nuovo, **mancanti} if mancanti else nuovo


def _same_content(a: dict, b: dict) -> bool:
    ignore = {"generated_at"}
    return {k: v for k, v in a.items() if k not in ignore} == {
        k: v for k, v in b.items() if k not in ignore
    }
