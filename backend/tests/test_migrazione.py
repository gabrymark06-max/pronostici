"""La migrazione deve dire la stessa cosa dei modelli.

PERCHE' QUESTA PROVA ESISTE. Le altre girano su SQLite e non toccano Alembic:
verificano il comportamento, non lo schema che finira' in produzione. Il modo
tipico in cui questo si rompe non e' un errore di sintassi — e' qualcuno che
aggiunge una colonna a `modelli.py`, la usa, vede le prove verdi, e scopre in
produzione che la tabella quella colonna non ce l'ha.

Qui si genera l'SQL della migrazione in modalita' OFFLINE — nessun database
serve — e si controlla che ogni colonna dei modelli compaia. Non e' un
confronto completo di tipi e vincoli: e' la rete che prende la caduta piu'
frequente e piu' costosa.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def sql() -> str:
    ambiente = {
        **os.environ,
        # In modalita' offline Alembic non si collega: la URL serve solo a
        # scegliere il dialetto con cui scrivere l'SQL.
        "DATABASE_URL": "postgresql+asyncpg://finto:finto@localhost:5432/finto",
        "CHIAVE_JWT": "chiave-finta-lunga-abbastanza-per-le-prove-offline",
    }
    esito = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=RADICE,
        env=ambiente,
        capture_output=True,
        text=True,
    )
    assert esito.returncode == 0, esito.stderr
    return esito.stdout


def test_ogni_colonna_dei_modelli_esiste_nella_migrazione(sql: str) -> None:
    from centro_conti.modelli import Base

    mancanti: list[str] = []
    for tabella in Base.metadata.tables.values():
        assert f"CREATE TABLE {tabella.name}" in sql, f"tabella {tabella.name} non creata"
        # Si isola il blocco della tabella, altrimenti una colonna che esiste
        # in un'altra tabella farebbe passare il controllo per sbaglio.
        blocco = sql.split(f"CREATE TABLE {tabella.name}", 1)[1].split(");", 1)[0]
        for colonna in tabella.columns:
            if colonna.name not in blocco:
                mancanti.append(f"{tabella.name}.{colonna.name}")
    assert not mancanti, f"colonne nei modelli ma non nella migrazione: {mancanti}"


def test_l_email_e_unica_nel_database(sql: str) -> None:
    """Non basta il controllo applicativo: fra la SELECT e la INSERT ci passa
    una seconda registrazione."""
    assert "CREATE UNIQUE INDEX ix_utenti_email" in sql


def test_le_sessioni_seguono_l_utente_cancellato(sql: str) -> None:
    """Senza la cascata, chiudere un conto lascerebbe sessioni orfane che
    permettono ancora di rinnovare."""
    assert "ON DELETE CASCADE" in sql


def test_gli_istanti_portano_il_fuso(sql: str) -> None:
    assert "TIMESTAMP WITH TIME ZONE" in sql
    assert "TIMESTAMP WITHOUT TIME ZONE" not in sql
