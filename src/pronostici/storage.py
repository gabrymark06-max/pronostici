"""Scrittura su `data/`: il repository e' il database.

Due regole che rendono i job idempotenti e i commit leggibili:

* **JSON stabile** (chiavi ordinate, indentazione fissa, newline finale). Due
  esecuzioni con gli stessi dati producono byte identici, quindi `git status`
  e' pulito e il job non crea un commit vuoto.
* **Scrittura atomica** (file temporaneo + `os.replace`). Un job interrotto a
  meta' non lascia un JSON troncato dentro il contratto col frontend.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Versione del contratto con il frontend. Si alza solo con un cambio
# incompatibile, e va annunciato (docs/schema.md).
SCHEMA_VERSION = 1


def write_json(path: Path, payload: Any, *, indent: int = 1) -> bool:
    """Scrive `payload` in `path`. Ritorna True solo se il contenuto e' cambiato.

    Il valore di ritorno e' cio' che permette ai job di committare "solo se
    qualcosa e' cambiato" senza confrontare a mano.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=indent, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return True


def write_text_atomic(path: Path, text: str) -> None:
    """Sostituisce il contenuto di un file in modo atomico.

    Serve a un solo chiamante, `ledger.apply_settlements`, che e' l'unica
    scrittura non-append del sistema: un'interruzione a meta' non deve poter
    lasciare il registro troncato.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    """Append puro. Non riscrive mai le righe esistenti: e' il ledger."""
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out
