"""Archivio permanente delle partite (rischio 7 del brief).

football-data.org espone **due stagioni scorrevoli**: quando si apre la
2026-27, la 2024-25 sparisce e lo storico si accorcerebbe da solo. Qui ogni
partita vista anche una volta sola resta per sempre, versionata nel repo.

Regola di merge: una partita archiviata **non viene mai persa**, e viene
aggiornata solo se la nuova versione porta piu' informazione (un risultato
dove prima c'era un calendario). Cosi' `ingest` e' idempotente e non riscrive
il passato.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import ARCHIVE_DIR
from .storage import read_json, write_json

# Stati che football-data usa per una partita conclusa con un punteggio valido.
FINISHED_STATES = {"FINISHED", "AWARDED"}


@dataclass(frozen=True)
class Match:
    """Una partita, nella nostra forma, non nella loro."""

    match_id: int
    competition: str
    season: int
    utc_date: str
    status: str
    matchday: int | None
    home_id: int
    home_name: str
    home_tla: str | None
    home_crest: str | None
    away_id: int
    away_name: str
    away_tla: str | None
    away_crest: str | None
    ft_home: int | None
    ft_away: int | None
    ht_home: int | None
    ht_away: int | None
    venue: str | None
    referee: str | None
    first_seen: str

    @property
    def is_finished(self) -> bool:
        return (
            self.status in FINISHED_STATES
            and self.ft_home is not None
            and self.ft_away is not None
        )

    @property
    def date(self) -> datetime:
        return datetime.fromisoformat(self.utc_date.replace("Z", "+00:00"))

    @property
    def information_score(self) -> int:
        """Quanta informazione porta questo record. Serve al merge."""
        score = 0
        if self.ft_home is not None:
            score += 2
        if self.ht_home is not None:
            score += 1
        if self.status in FINISHED_STATES:
            score += 1
        return score


def parse_match(payload: dict[str, Any], competition: str, season: int) -> Match:
    """Normalizza il payload di football-data. Tollera i campi assenti:
    il piano gratuito non garantisce venue e arbitro su ogni partita."""
    score = payload.get("score") or {}
    full = score.get("fullTime") or {}
    half = score.get("halfTime") or {}
    home = payload.get("homeTeam") or {}
    away = payload.get("awayTeam") or {}
    referees = payload.get("referees") or []
    return Match(
        match_id=int(payload["id"]),
        competition=competition,
        season=season,
        utc_date=payload["utcDate"],
        status=payload.get("status", "UNKNOWN"),
        matchday=payload.get("matchday"),
        home_id=int(home.get("id") or 0),
        home_name=home.get("name") or "?",
        home_tla=home.get("tla"),
        home_crest=home.get("crest"),
        away_id=int(away.get("id") or 0),
        away_name=away.get("name") or "?",
        away_tla=away.get("tla"),
        away_crest=away.get("crest"),
        ft_home=full.get("home"),
        ft_away=full.get("away"),
        ht_home=half.get("home"),
        ht_away=half.get("away"),
        venue=payload.get("venue"),
        referee=(referees[0].get("name") if referees else None),
        first_seen=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )


def archive_path(competition: str, season: int) -> Path:
    return ARCHIVE_DIR / competition / f"{season}.json"


def load_season(competition: str, season: int) -> list[Match]:
    payload = read_json(archive_path(competition, season), default=None)
    if not payload:
        return []
    return [Match(**row) for row in payload["matches"]]


def load_all(competition: str) -> list[Match]:
    """Tutto lo storico archiviato di una competizione, ordinato per data."""
    directory = ARCHIVE_DIR / competition
    if not directory.exists():
        return []
    matches: list[Match] = []
    for file in sorted(directory.glob("*.json")):
        payload = read_json(file, default=None)
        if payload:
            matches.extend(Match(**row) for row in payload["matches"])
    matches.sort(key=lambda m: (m.utc_date, m.match_id))
    return matches


def merge_season(competition: str, season: int, incoming: Iterable[Match]) -> dict:
    """Fonde le partite nuove con quelle gia' archiviate.

    Ritorna un riepilogo per il log del job. Non cancella mai una partita:
    e' l'intera ragione per cui questo modulo esiste.
    """
    existing = {m.match_id: m for m in load_season(competition, season)}
    added = updated = 0
    for match in incoming:
        old = existing.get(match.match_id)
        if old is None:
            existing[match.match_id] = match
            added += 1
        elif match.information_score > old.information_score:
            # Si conserva la data di primo avvistamento: e' una prova.
            existing[match.match_id] = Match(
                **{**asdict(match), "first_seen": old.first_seen}
            )
            updated += 1

    rows = [asdict(m) for m in sorted(existing.values(), key=lambda m: m.utc_date)]
    changed = write_json(
        archive_path(competition, season),
        {"competition": competition, "season": season, "matches": rows},
    )
    return {
        "competition": competition,
        "season": season,
        "added": added,
        "updated": updated,
        "total": len(rows),
        "file_changed": changed,
    }
