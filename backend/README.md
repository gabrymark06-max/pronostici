# Centro — profili

Registrazione, accesso, sessioni, conferma dell'indirizzo e recupero della password per il sito dei pronostici. È un **servizio a
sé**: gira su un altro indirizzo e ha un altro ciclo di vita rispetto al sito.

## Perché è separato

Il sito è un export statico — nessun runtime, nessuna chiave, nessuna chiamata
a nessuno (decisione del brief 11.2). È quella scelta che gli permette di
reggere qualunque traffico e di non consumare quote.

I profili hanno bisogno di un server. Tenerli qui dentro significa che **se questo
servizio cade, il sito continua a pubblicare pronostici**: si perde solo la
possibilità di accedere. La parte che può rompersi non deve poter portare giù
quella che non può.

## Avvio in locale

Serve Postgres. Con Docker:

```bash
docker run -d --name centro-db -e POSTGRES_PASSWORD=centro -p 5432:5432 postgres:16
```

Poi:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # su Linux/Mac: .venv/bin/python

cp .env.example .env        # e riempi CHIAVE_JWT
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn centro_profili.main:app --reload --port 8000
```

La documentazione interattiva è su <http://localhost:8000/documentazione>.

Il frontend va costruito con l'indirizzo dell'API:

```bash
cd ../frontend
echo "NEXT_PUBLIC_API_PROFILI=http://localhost:8000" > .env.local
npm run build
```

**Senza quella variabile i profili restano spenti** e il sito si costruisce
esattamente come prima: niente voce «Accedi», niente pagine dei profili. È
voluto — un bottone che porta a un modulo che non può funzionare è peggio di
nessun bottone.

## Le prove

```bash
.venv/Scripts/python -m pytest tests -q     # 60
.venv/Scripts/python -m ruff check src tests alembic
```

Girano su SQLite in memoria e verificano le **decisioni**, non che il codice
giri: l'errore d'accesso indistinguibile, la rotazione del gettone, il cambio
password che caccia fuori gli altri browser.

Quello che le prove **non** coprono, e va saputo:

- la migrazione Alembic è scritta per Postgres e le prove girano su SQLite.
  `tests/test_migrazione.py` ne genera l'SQL in modalità offline e controlla
  che ogni colonna dei modelli ci sia, ma **applicarla contro un Postgres vero
  è un passaggio a mano**, da fare la prima volta che si va in esercizio;
- il limitatore dei tentativi vive in memoria: vedi sotto.

## Le decisioni che contano

Sono spiegate per esteso nei commenti dei file. In breve:

| Dove | Cosa | Perché |
|---|---|---|
| `rotte/profili.py` | L'errore d'accesso è identico che l'email esista o no, e con lo stesso tempo di risposta | Altrimenti si prova un elenco di indirizzi e si tiene quello che risponde «password sbagliata» |
| `rotte/profili.py` | La registrazione non conferma se l'email è già presa | Direbbe la stessa cosa dal lato opposto |
| `rotte/profili.py` | Il gettone di rinnovo ruota a ogni uso | Un gettone rubato e riusato non entra, oppure fa accorgere il proprietario |
| `modelli.py` | Ogni gettone porta una *generazione*; cambiare password la incrementa | Senza, i gettoni d'accesso già emessi restavano validi 15 minuti dopo il cambio password |
| `dipendenze.py` | I gettoni stanno in cookie `httpOnly`, mai in `localStorage` | Una dipendenza compromessa leggerebbe `localStorage` e porterebbe via le sessioni di tutti |
| `sicurezza.py` | Argon2id, non bcrypt | bcrypt tronca a 72 byte in silenzio |
| `rotte/profili.py` | Chiudere il profilo **cancella**, non disattiva | Un profilo «chiuso» che resta in tabella è un archivio di dati personali che nessuno ha più motivo di tenere |

## Limiti dichiarati

**Il limitatore dei tentativi è in memoria** (`limiti.py`). Con più di un
processo ogni processo ha il suo profilo, e i tentativi effettivi si moltiplicano
per il numero di processi. Va bene per un'istanza sola — che è come parte
questo servizio — e quando ne servirà una seconda quel modulo va spostato su
Redis.

**La posta, in sviluppo, non parte davvero.** `POSTA_MODO=finta` (il
predefinito) scrive il messaggio nei log — per intero, collegamento compreso —
invece di spedirlo. Si prova così il giro completo senza un account SMTP e
senza rischiare di spedire a qualcuno per sbaglio.

È il predefinito **di proposito**, non un ripiego: un servizio che crede di
spedire e non spedisce lascia le persone ad aspettare un'email che non
arriverà, e nessun log dice niente perché non c'è stato nessun errore. Qui la
finta si vede a ogni messaggio, e `smtp` si accende a mano.

Per spedire davvero:

```
POSTA_MODO=smtp
POSTA_DA=Centro <no-reply@il-tuo-dominio.it>
SMTP_HOST=smtp.tuo-fornitore.it
SMTP_PORTA=587
SMTP_UTENTE=...
SMTP_PASSWORD=...
SITO=https://il-tuo-dominio.it
```

`SITO` è l'indirizzo del **sito**, non dell'API: è quello che finisce nei
collegamenti dentro le email.

## In produzione

Tre variabili cambiano, e senza non funziona niente:

```
AMBIENTE=produzione
COOKIE_SAMESITE=none
COOKIE_SECURE=true
ORIGINI=https://il-tuo-dominio.it
```

Il sito e l'API stanno su due domini diversi: per il browser sono due siti, e
un cookie `lax` non viene mandato. `COOKIE_SECURE=true` richiede **HTTPS su
entrambi** — su http l'accesso sembra riuscire e poi la sessione non dura oltre
il caricamento della pagina.

E genera una chiave vera:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
