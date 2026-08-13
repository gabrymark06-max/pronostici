# Centro — conti

Registrazione, accesso e sessioni per il sito dei pronostici. È un **servizio a
sé**: gira su un altro indirizzo e ha un altro ciclo di vita rispetto al sito.

## Perché è separato

Il sito è un export statico — nessun runtime, nessuna chiave, nessuna chiamata
a nessuno (decisione del brief 11.2). È quella scelta che gli permette di
reggere qualunque traffico e di non consumare quote.

I conti hanno bisogno di un server. Tenerli qui dentro significa che **se questo
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
.venv/Scripts/python -m uvicorn centro_conti.main:app --reload --port 8000
```

La documentazione interattiva è su <http://localhost:8000/documentazione>.

Il frontend va costruito con l'indirizzo dell'API:

```bash
cd ../frontend
echo "NEXT_PUBLIC_API_CONTI=http://localhost:8000" > .env.local
npm run build
```

**Senza quella variabile i conti restano spenti** e il sito si costruisce
esattamente come prima: niente voce «Accedi», niente pagine dei conti. È
voluto — un bottone che porta a un modulo che non può funzionare è peggio di
nessun bottone.

## Le prove

```bash
.venv/Scripts/python -m pytest tests -q     # 40
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
| `rotte/conti.py` | L'errore d'accesso è identico che l'email esista o no, e con lo stesso tempo di risposta | Altrimenti si prova un elenco di indirizzi e si tiene quello che risponde «password sbagliata» |
| `rotte/conti.py` | La registrazione non conferma se l'email è già presa | Direbbe la stessa cosa dal lato opposto |
| `rotte/conti.py` | Il gettone di rinnovo ruota a ogni uso | Un gettone rubato e riusato non entra, oppure fa accorgere il proprietario |
| `modelli.py` | Ogni gettone porta una *generazione*; cambiare password la incrementa | Senza, i gettoni d'accesso già emessi restavano validi 15 minuti dopo il cambio password |
| `dipendenze.py` | I gettoni stanno in cookie `httpOnly`, mai in `localStorage` | Una dipendenza compromessa leggerebbe `localStorage` e porterebbe via le sessioni di tutti |
| `sicurezza.py` | Argon2id, non bcrypt | bcrypt tronca a 72 byte in silenzio |
| `rotte/conti.py` | Chiudere il conto **cancella**, non disattiva | Un conto «chiuso» che resta in tabella è un archivio di dati personali che nessuno ha più motivo di tenere |

## Limiti dichiarati

**Il limitatore dei tentativi è in memoria** (`limiti.py`). Con più di un
processo ogni processo ha il suo conto, e i tentativi effettivi si moltiplicano
per il numero di processi. Va bene per un'istanza sola — che è come parte
questo servizio — e quando ne servirà una seconda quel modulo va spostato su
Redis.

**Non c'è verifica dell'email e non c'è recupero password.** Entrambe hanno
bisogno di spedire posta, e questo progetto non ha ancora un servizio di
spedizione. La colonna `email_verificata` esiste già in tabella perché
aggiungerla dopo, su una tabella piena, sarebbe una migrazione in più.

Sono anche le **due cose che vanno fatte prima di far pagare qualcuno**: non si
vende a un indirizzo che nessuno ha confermato, e un cliente che perde la
password e non può recuperarla è un cliente perso e arrabbiato.

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
