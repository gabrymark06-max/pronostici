"""Accende il sito in locale: le pagine e il servizio dei profili, insieme.

PERCHE' ESISTE. Il sito e' fatto di due pezzi che girano separati:

  - le PAGINE (Next.js, cartella `frontend/`) sulla porta 3000 — calendario,
    pronostici, progressi: tutto cio' che si legge senza essere entrati;
  - i PROFILI (FastAPI, cartella `backend/`) sulla porta 8000 — registrazione,
    accesso, verifica dell'email, cambio password.

Accenderne uno solo non da' un errore: le pagine si vedono benissimo, e il
guasto salta fuori solo dopo, al momento di entrare, come un «impossibile
contattare il servizio» che sembra un problema di rete. Questo file accende
tutti e due nello stesso momento, cosi' quel caso non capita.

I due pezzi usano anche due Python diversi: il backend ha il suo ambiente in
`backend/.venv`, dove stanno FastAPI e uvicorn. Lanciarlo col Python di sistema
si ferma subito con «No module named 'uvicorn'», ed e' esattamente per non
doverselo ricordare che qui sotto il percorso e' scritto una volta sola.

COME SI USA. Apri il terminale nella cartella del progetto e scrivi:

    python scripts/sito.py

Aspetta la riga «IL SITO E' PRONTO», poi apri http://localhost:3000.
Per spegnere: CTRL+C in questa finestra. Si fermano entrambi.

NON confonderlo con `scripts/giornata.py`: quello AGGIORNA i dati (calendario,
risultati, pronostici di oggi) e va lanciato una volta al giorno. Questo qui
non tocca niente, mostra solo quello che c'e' gia'.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
FRONTEND = RADICE / "frontend"
BACKEND = RADICE / "backend"
PYTHON_BACKEND = BACKEND / ".venv" / "Scripts" / "python.exe"

INDIRIZZO = "http://localhost:3000"


def _chiudi(processo: subprocess.Popen) -> None:
    """Spegne un processo E I SUOI FIGLI.

    `terminate()` da solo non basta su Windows: `npm run dev` e' un lanciatore
    che avvia Next in un processo separato, e uccidere il lanciatore lascia
    Next vivo sulla porta 3000. Al giro dopo la porta risulta occupata e il
    sito parte sul 3001 — dove pero' il backend non accetta le chiamate,
    perche' 3001 non e' fra le origini autorizzate. `taskkill /T` chiude
    l'albero intero e il problema non si presenta.
    """
    if processo.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(processo.pid)],
            capture_output=True,
        )
    else:
        processo.terminate()
    try:
        processo.wait(timeout=10)
    except subprocess.TimeoutExpired:
        processo.kill()


def main() -> int:
    # Senza questa riga la riga «IL SITO E' PRONTO» puo' restare nel buffer di
    # Python e non comparire mai: i due server figli scrivono di continuo sullo
    # stesso schermo, ma i NOSTRI messaggi escono solo a blocchi. Chi guarda
    # vede l'output di Next fermarsi e nessuna istruzione, e conclude che si e'
    # piantato.
    sys.stdout.reconfigure(line_buffering=True)

    if not PYTHON_BACKEND.exists():
        print(f"Manca l'ambiente del backend: {PYTHON_BACKEND}")
        print("Si ricrea cosi', dalla cartella backend/:")
        print("  python -m venv .venv")
        print("  .venv\\Scripts\\python -m pip install -e .")
        return 1

    if not (FRONTEND / "node_modules").exists():
        print("Mancano le dipendenze del sito.")
        print("Si installano cosi', dalla cartella frontend/:  npm install")
        return 1

    processi: list[tuple[str, subprocess.Popen]] = []
    try:
        print("Accendo i profili (porta 8000)...", flush=True)
        processi.append(
            (
                "profili",
                subprocess.Popen([str(PYTHON_BACKEND), "avvia_prova.py"], cwd=BACKEND),
            )
        )

        print("Accendo le pagine (porta 3000)...", flush=True)
        # `shell=True` perche' su Windows `npm` e' uno script `.cmd`, non un
        # eseguibile: senza, Popen non lo trova e muore con FileNotFoundError.
        processi.append(
            (
                "pagine",
                subprocess.Popen("npm run dev", cwd=FRONTEND, shell=True),
            )
        )

        # Next impiega qualche secondo a compilare la prima pagina. Dire
        # l'indirizzo prima che sia pronto invita ad aprirlo e a vedere un
        # errore di connessione, che sembra un guasto e non lo e'.
        time.sleep(12)

        for nome, processo in processi:
            if processo.poll() is not None:
                print(f"\n«{nome}» non e' partito. L'errore e' qui sopra.")
                return 1

        print("\n" + "=" * 58)
        print("  IL SITO E' PRONTO:  " + INDIRIZZO)
        print("=" * 58)
        print("\n  CTRL+C in questa finestra per spegnere tutto.\n")

        # Se uno dei due muore da solo, si spegne anche l'altro: un sito a
        # meta' e' peggio di un sito spento, perche' il guasto non si vede.
        while True:
            for nome, processo in processi:
                if processo.poll() is not None:
                    print(f"\n«{nome}» si e' fermato. Spengo anche il resto.")
                    return 1
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nSpengo.")
        return 0
    finally:
        for _, processo in reversed(processi):
            _chiudi(processo)


if __name__ == "__main__":
    raise SystemExit(main())
