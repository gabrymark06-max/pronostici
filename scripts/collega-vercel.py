"""Collega questo repository a Vercel, una volta sola.

COSA FA, in ordine: crea (o ritrova) il progetto su Vercel, legge i due
identificatori che il deploy da GitHub Actions richiede, e li deposita fra i
segreti del repository insieme all'indirizzo pubblico del sito.

PERCHE' UNO SCRIPT E NON `vercel link`.
`vercel link` vuole un login interattivo nel browser e scrive `.vercel/` in
locale: va bene una volta sul proprio computer, ma i tre valori che servono
alla CI restano da copiare a mano in tre punti diversi, ed e' li' che si
sbaglia — il piu' delle volte incollando l'`orgId` al posto del `projectId`,
che produce un errore di autorizzazione che sembra un token scaduto.

L'UNICA COSA CHE NON PUO' FARE DA SE' e' il token: si crea a mano su
https://vercel.com/account/tokens perche' e' la credenziale che autorizza
tutto il resto. Lo script non lo scrive mai su disco.

    py scripts/collega-vercel.py

Rilanciarlo e' innocuo: se il progetto esiste gia' lo riusa invece di
duplicarlo, e riscrive gli stessi segreti.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.vercel.com"
NOME_PROGETTO = "pronostici"


def chiama(
    percorso: str, token: str, corpo: dict | None = None, ammetti_assente: bool = False
) -> dict | None:
    dati = json.dumps(corpo).encode() if corpo is not None else None
    richiesta = urllib.request.Request(
        f"{API}{percorso}",
        data=dati,
        method="POST" if dati else "GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404 and ammetti_assente:
            return None
        testo = e.read().decode(errors="replace")
        try:
            messaggio = json.loads(testo)["error"]["message"]
        except Exception:
            messaggio = testo[:400]
        raise SystemExit(f"Vercel ha risposto {e.code}: {messaggio}") from None


def indirizzo_pubblico(progetto: dict, token: str) -> str:
    """L'indirizzo vero del sito, CHIESTO A VERCEL e mai dedotto dal nome.

    Qui c'e' stato un errore che vale la pena lasciare scritto. Questo script
    componeva `https://{nome}.vercel.app` dando per scontato che il nome del
    progetto diventasse il sottodominio. Non e' cosi': `pronostici.vercel.app`
    era gia' di qualcun altro — un sito di pronostici, per giunta — e Vercel
    aveva assegnato `pronostici-sigma.vercel.app` senza dirlo a nessuno.

    Il deploy passava verde: e' il sitemap che usciva sbagliato, 351 URL che
    dichiaravano ai motori di ricerca il sito di un concorrente come indirizzo
    canonico. Un guasto che non si vede da nessun log — solo aprendo l'indirizzo
    e accorgendosi che il titolo e' di un altro prodotto.

    Su un progetto appena creato non c'e' ancora nessun alias: si scopre solo
    dopo la prima pubblicazione. In quel caso si dice, e si rilancia dopo.
    """
    alias = ((progetto.get("targets") or {}).get("production") or {}).get("alias") or []
    if not alias:
        return ""
    # Vercel ne elenca diversi (`nome-hash-utente`, `nome-parola`, gli eventuali
    # domini propri). Quello stabile e' il piu' corto: gli altri contengono
    # l'identificativo del singolo deploy e cambiano a ogni pubblicazione.
    return "https://" + min(alias, key=len)


def gh(*argomenti: str) -> None:
    esito = subprocess.run(["gh", *argomenti], capture_output=True, text=True)
    if esito.returncode != 0:
        raise SystemExit(
            f"`gh {' '.join(argomenti[:2])}` e' fallito:\n{esito.stderr.strip()}"
        )


def main() -> int:
    token = os.environ.get("VERCEL_TOKEN", "").strip()
    if not token:
        print("Token da https://vercel.com/account/tokens")
        print("(non viene stampato ne' salvato su disco)")
        token = input("VERCEL_TOKEN: ").strip()
    if not token:
        print("Nessun token, niente da fare.", file=sys.stderr)
        return 1

    utente = chiama("/v2/user", token)["user"]
    print(f"Account Vercel: {utente.get('username') or utente.get('email')}")

    # Il progetto puo' gia' esistere: chi ha provato a collegarlo dal sito di
    # Vercel prima di arrivare qui ne ha gia' uno con questo nome. Crearne un
    # secondo darebbe un `pronostici-1` che pubblica e non lo guarda nessuno.
    progetto = chiama(f"/v9/projects/{NOME_PROGETTO}", token, ammetti_assente=True)
    if progetto is not None:
        print(f"Progetto gia' esistente: {progetto['name']}")
    else:
        progetto = chiama(
            "/v11/projects",
            token,
            # `framework: null` = nessun preset. La CI carica `frontend/out/`
            # gia' costruito e verificato: se Vercel ci riconoscesse Next.js
            # proverebbe a ricostruire con impostazioni sue, e in produzione
            # finirebbe un build diverso da quello appena passato dai controlli.
            {"name": NOME_PROGETTO, "framework": None},
        )
        print(f"Progetto creato: {progetto['name']}")

    org = progetto.get("accountId") or utente["id"]
    sito = indirizzo_pubblico(progetto, token)

    gh("secret", "set", "VERCEL_TOKEN", "--body", token)
    gh("secret", "set", "VERCEL_ORG_ID", "--body", org)
    gh("secret", "set", "VERCEL_PROJECT_ID", "--body", progetto["id"])

    print()
    print("Segreti scritti nel repository:")
    print(f"  VERCEL_ORG_ID       {org}")
    print(f"  VERCEL_PROJECT_ID   {progetto['id']}")
    print("  VERCEL_TOKEN        (nascosto)")

    if sito:
        gh("variable", "set", "SITO", "--body", sito)
        print(f"  SITO                {sito}")
        print()
        print("Ora lancia la pubblicazione:")
        print("  gh workflow run frontend.yml")
        return 0

    print("  SITO                ancora ignoto")
    print()
    print("Il progetto non ha ancora pubblicato niente, quindi Vercel non gli ha")
    print("assegnato nessun indirizzo: si scopre solo dopo il primo deploy, e")
    print("indovinarlo dal nome e' esattamente l'errore che ha gia' pubblicato un")
    print("sitemap verso il sito di un altro. Due comandi, in ordine:")
    print()
    print("  gh workflow run frontend.yml     # fallira' rosso: SITO manca ancora")
    print("  py scripts/collega-vercel.py     # ora l'indirizzo c'e', lo scrive")
    print("  gh workflow run frontend.yml     # questa pubblica davvero")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
