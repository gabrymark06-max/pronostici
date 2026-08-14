'use client';

import { useState, type FormEvent } from 'react';

import { useParametro } from '@/lib/indirizzo';
import { ErroreProfilo, MINIMO_PASSWORD, profilo } from '@/lib/profilo';

/**
 * I DUE PASSI DEL RECUPERO: chiedi il collegamento, e scegli la password nuova.
 *
 * LA RISPOSTA AL PRIMO PASSO NON DICE SE L'INDIRIZZO ESISTE, e non e' una
 * dimenticanza del testo: e' la stessa decisione presa nell'API. Un «questa
 * email non risulta» qui regalerebbe a chiunque un modo di verificare indirizzi
 * uno per uno senza nemmeno provare una password. Quindi il messaggio e'
 * sempre lo stesso, ed e' scritto in modo da non suonare come una conferma —
 * «se esiste un profilo con quell'indirizzo», non «ti abbiamo mandato».
 */

export function ChiediRecupero() {
  const [fatto, setFatto] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);
  const [inCorso, setInCorso] = useState(false);

  async function invia(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (inCorso) return;
    const dati = new FormData(e.currentTarget);
    setInCorso(true);
    setErrore(null);
    try {
      await profilo.recupero(String(dati.get('email') ?? ''));
      setFatto(true);
    } catch (err) {
      setErrore(err instanceof ErroreProfilo ? err.message : 'Non ha funzionato.');
    } finally {
      setInCorso(false);
    }
  }

  if (fatto) {
    return (
      <div className="esito esito--riuscito">
        <h1 className="titolo-sezione">Controlla la posta</h1>
        <p>
          Se esiste un profilo con quell’indirizzo, gli abbiamo appena mandato un
          collegamento per scegliere una password nuova. Vale 24 ore e si usa una volta sola.
        </p>
        <p className="esito__nota">
          Non è arrivato niente? Guarda nella posta indesiderata. Se non c’è nemmeno lì,
          probabilmente il profilo è registrato con un altro indirizzo.
        </p>
        <p className="esito__azioni">
          <a className="azione" href="/accedi/">
            Torna all’accesso
          </a>
        </p>
      </div>
    );
  }

  return (
    <form className="modulo" onSubmit={invia} noValidate>
      <h1 className="titolo-sezione">Password dimenticata</h1>
      <p className="modulo__intro">
        Scrivi l’indirizzo del tuo profilo. Ti mandiamo un collegamento per sceglierne una
        nuova.
      </p>

      {errore ? (
        <p className="modulo__errore" role="alert">
          {errore}
        </p>
      ) : null}

      <label className="modulo__campo">
        <span className="modulo__etichetta">Email</span>
        <input
          className="modulo__casella"
          type="email"
          name="email"
          autoComplete="email"
          inputMode="email"
          required
        />
      </label>

      <button className="azione azione--piena" type="submit" aria-busy={inCorso}>
        {inCorso ? 'Un momento…' : 'Mandami il collegamento'}
      </button>

      <p className="modulo__altro">
        Ti è tornata in mente? <a href="/accedi/">Entra</a>
      </p>
    </form>
  );
}

/* ------------------------------------------------------------------ */

/**
 * IL SECONDO PASSO. Il gettone arriva nell'indirizzo, la password si sceglie
 * qui.
 *
 * DOPO NON SI ENTRA IN AUTOMATICO, e l'API non apre nessuna sessione. Chi ha
 * reimpostato deve entrare con la password nuova: e' la prova che se l'e'
 * segnata, e se il collegamento fosse stato intercettato l'intruso non si
 * troverebbe comunque una sessione aperta in mano.
 */
export function ConfermaRecupero() {
  /* TRE VALORI, NON DUE, e il terzo e' quello che conta.
     `undefined` = il browser non ha ancora parlato, `null` = ha parlato e il
     codice non c'e', stringa = c'e'. La distinzione la garantisce la firma di
     `useParametro`; qui si spiega perche' e' stata scritta cosi'.

     Con due soli valori l'iniziale era `null` e la lettura ci rimetteva `null`
     quando il codice mancava: React vede lo stesso valore, non rirenderizza, e
     il ramo «manca il codice» non compariva MAI. Chi apriva l'indirizzo senza
     codice si trovava davanti un modulo che, all'invio, non faceva niente — la
     guardia `if (!gettone) return` lo fermava in silenzio. Un modulo morto e'
     peggio di un errore.

     Trovato con il browser, non leggendo: e' il tipo di difetto che sul codice
     sembra corretto perche' il ramo c'e' ed e' scritto bene. */
  const gettone = useParametro('g');
  const [fatto, setFatto] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);
  const [inCorso, setInCorso] = useState(false);

  const inLettura = gettone === undefined;

  async function invia(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (inCorso || !gettone) return;
    const modulo = e.currentTarget;
    const dati = new FormData(modulo);
    setInCorso(true);
    setErrore(null);
    try {
      await profilo.confermaRecupero({
        gettone,
        password_nuova: String(dati.get('password') ?? ''),
      });
      setFatto(true);
    } catch (err) {
      setErrore(err instanceof ErroreProfilo ? err.message : 'Non ha funzionato.');
      modulo.reset();
    } finally {
      setInCorso(false);
    }
  }

  if (fatto) {
    return (
      <div className="esito esito--riuscito">
        <h1 className="titolo-sezione">Password cambiata</h1>
        <p>
          Adesso entra con quella nuova. <strong>Tutte le sessioni aperte sono state
          chiuse</strong>, anche su altri dispositivi: se qualcuno era entrato, adesso è
          fuori.
        </p>
        <p className="esito__azioni">
          <a className="azione azione--piena" href="/accedi/">
            Entra
          </a>
        </p>
      </div>
    );
  }

  if (inLettura) {
    return (
      <div className="esito">
        <h1 className="titolo-sezione">Un momento…</h1>
      </div>
    );
  }

  if (gettone === null) {
    return (
      <div className="esito esito--fallito">
        <h1 className="titolo-sezione">Manca il codice</h1>
        <p>
          Questo indirizzo non porta nessun codice. Apri il collegamento direttamente
          dall’email, oppure <a href="/recupero/">chiedine un altro</a>.
        </p>
      </div>
    );
  }

  return (
    <form className="modulo" onSubmit={invia} noValidate>
      <h1 className="titolo-sezione">Scegli una password nuova</h1>

      {errore ? (
        <p className="modulo__errore" role="alert">
          {errore}
        </p>
      ) : null}

      <label className="modulo__campo">
        <span className="modulo__etichetta">Password nuova</span>
        <input
          className="modulo__casella"
          type="password"
          name="password"
          autoComplete="new-password"
          required
          minLength={MINIMO_PASSWORD}
        />
        <span className="modulo__aiuto">Almeno {MINIMO_PASSWORD} caratteri.</span>
      </label>

      <button className="azione azione--piena" type="submit" aria-busy={inCorso}>
        {inCorso ? 'Un momento…' : 'Cambia la password'}
      </button>

      <p className="modulo__patto">
        Cambiandola chiudiamo tutte le sessioni aperte, su qualunque dispositivo. È il motivo
        per cui si reimposta una password.
      </p>
    </form>
  );
}
