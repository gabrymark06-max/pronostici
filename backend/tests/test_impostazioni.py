"""Le impostazioni lette dall'ambiente.

Questo file esiste per un guasto vero: `ORIGINI=https://a.it,https://b.it` —
la forma documentata in `.env.example`, e l'unica che si puo' scrivere nel
pannello di un hosting — faceva morire l'avvio con un errore di JSON.

Il difetto e' della classe piu' cattiva: si vede solo all'avvio, e solo con la
variabile impostata. Le prove giravano tutte verdi perche' usano i valori
predefiniti, e in locale funzionava. Sarebbe uscito al primo deploy.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def _impostazioni(monkeypatch, **variabili):
    from centro_conti import impostazioni as modulo

    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("CHIAVE_JWT", "chiave-di-prova-lunga-abbastanza-per-passare")
    for k, v in variabili.items():
        monkeypatch.setenv(k, v)
    modulo.impostazioni.cache_clear()
    try:
        return modulo.impostazioni()
    finally:
        modulo.impostazioni.cache_clear()


def test_origini_separate_da_virgola(monkeypatch):
    imp = _impostazioni(monkeypatch, ORIGINI="https://uno.it,https://due.it")
    assert imp.origini == ["https://uno.it", "https://due.it"]


def test_origini_con_spazi_intorno(monkeypatch):
    imp = _impostazioni(monkeypatch, ORIGINI=" https://uno.it , https://due.it ")
    assert imp.origini == ["https://uno.it", "https://due.it"]


def test_una_sola_origine(monkeypatch):
    imp = _impostazioni(monkeypatch, ORIGINI="https://solo.it")
    assert imp.origini == ["https://solo.it"]


def test_il_jolly_e_rifiutato(monkeypatch):
    """Con i cookie di sessione `*` e' rifiutato dai browser: meglio non
    partire che partire con una configurazione che non funzionera'."""
    with pytest.raises(ValidationError, match="jolly"):
        _impostazioni(monkeypatch, ORIGINI="https://uno.it,*")


def test_senza_chiave_non_parte(monkeypatch):
    from centro_conti import impostazioni as modulo

    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.delenv("CHIAVE_JWT", raising=False)
    modulo.impostazioni.cache_clear()
    try:
        with pytest.raises(ValidationError):
            modulo.impostazioni()
    finally:
        modulo.impostazioni.cache_clear()


def test_chiave_troppo_corta_rifiutata(monkeypatch):
    from centro_conti import impostazioni as modulo

    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("CHIAVE_JWT", "corta")
    modulo.impostazioni.cache_clear()
    try:
        with pytest.raises(ValidationError):
            modulo.impostazioni()
    finally:
        modulo.impostazioni.cache_clear()
