'use client';

import { useEffect, useState, type FormEvent } from 'react';

import { ErroreProfilo, MINIMO_PASSWORD, profilo } from '@/lib/profilo';

/**
 * IL RECUPERO DELLA PASSWORD, nei suoi due tempi.
 *
 * `ChiediRecupero` — si scrive l'indirizzo e parte un'email.
 * `ScegliPassword` — si apre il collegamento e si sceglie la password nuova.
 *
 * LA PRIMA SCHERMATA NON DICE MAI SE L'INDIRIZZO ESISTE, e la risposta e'
 * sempre la stessa. Non e' una scortesia: dire «questa email non risulta»
 * regalerebbe a chiunque un modo di verificare indirizzi uno per uno senza
 * nemmeno provare una password. Il backend fa lo stesso, e le due cose devono
 * combaciare — se la pagina distinguesse, la prudenza del backend non
 * servirebbe a niente.
 *
 * Il testo lo dice in chiaro invece di far finta di niente: «se quell'indirizzo
 * ha un profilo, il messaggio è partito». Cosi' chi ha sbagliato a scrivere
 * capisce perche' non arriva niente, senza che noi si confermi nulla.
 */

export function ChiediRecupero() {
  const [inCorso, setInCorso] = useState(false);
  const [fatto, setFatto] = useState(false);
  const [errore, setErrore] = useState<ErroreProfilo | null>(null);

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
      setErrore(
        err instanceof ErroreProfilo
          ? err
          : new ErroreProfilo('errore_sconosciuto', 'Non ha funzionato. Riprova.', 0),
      );
    } finally {
      setInCorso(false);
    }
  }

  if (fatto) {
    return (
      <div className="pagina-profilo__fuori">
        <h1 className="titolo-sezione">Guarda la posta</h1>
        <p>
          Se quell’indirizzo ha un profilo, il messaggio è partito. Dentro c’è un
          collegamento che vale <strong>24 ore</strong> e si usa una volta sola.
        </p>
        <p className="pagina-profilo__nota">
          Non arriva niente? Controlla la posta indesiderata, e che l’indirizzo sia scritto
          giusto. <a href="/accedi/">Torna all’accesso</a>.
        </p>
      </div>
    );
  }

  return (
    <form className="modulo" onSubmit={invia} noValidate>
      <h1 className="titolo-sezione">Password dimenticata</h1>
      <p className="modulo__aiuto">
        Scrivi l’indirizzo del tuo profilo: ti mandiamo un collegamento per scegliere una
        password nuova.
      </p>

      {errore ? (
        <p
          className={`modulo__errore${errore.codice === 'rete_non_raggiungibile' ? ' modulo__errore--nostro' : ''}`}
          role="alert"
        >
          {errore.message}
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
        Te la sei ricordata? <a href="/accedi/">Entra</a>
      </p>
    </form>
  );
}

/* ------------------------------------------------------------------ */

export function ScegliPassword() {
  const [gettone, setGettone] = useState<string | null>(null);
  const [inCorso, setInCorso] = useState(false);
  const [fatto, setFatto] = useState(false);
  const [errore, setErrore] = useState<ErroreProfilo | null>(null);

  /* Il gettone si legge dall'indirizzo dopo il montaggio: su un export statico
     non c'e' un server che veda la stringa di ricerca. Vedi `Verifica`. */
  useEffect(() => {
    setGettone(new URLSearchParams(window.location.search).get('g'));
  }, []);

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
      setErrore(
        err instanceof ErroreProfilo
          ? err
          : new ErroreProfilo('errore_sconosciuto', 'Non ha funzionato. Riprova.', 0),
      );
      modulo.reset();
    } finally {
      setInCorso(false);
    }
  }

  if (fatto) {
    return (
      <div className="pagina-profilo__fuori">
        <h1 className="titolo-sezione">Password cambiata</h1>
        <p>
          Fatto. <strong>Tutte le sessioni aperte sono state chiuse</strong>, questa compresa:
          se qualcuno era entrato, adesso è fuori.
        </p>
        <p className="pagina-profilo__nota">
          <a href="/accedi/">Entra con la password nuova</a>.
        </p>
      </div>
    );
  }

  if (gettone === null) {
    return (
      <div className="pagina-profilo__fuori">
        <h1 className="titolo-sezione">Manca il codice</h1>
        <p>
          Questo indirizzo si apre dal collegamento che ti abbiamo mandato per email.{' '}
          <a href="/recupero/">Chiedine uno</a>.
        </p>
      </div>
    );
  }

  return (
    <form className="modulo" onSubmit={invia} noValidate>
      <h1 className="titolo-sezione">Scegli la password nuova</h1>

      {errore ? (
        <p
          className={`modulo__errore${errore.codice === 'rete_non_raggiungibile' ? ' modulo__errore--nostro' : ''}`}
          role="alert"
        >
          {errore.message}
          {errore.codice === 'gettone_non_valido' ? (
            <>
              {' '}
              <a href="/recupero/">Chiedine un altro</a>.
            </>
          ) : null}
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
        Cambiarla qui <strong>chiude tutte le sessioni aperte</strong>, su ogni dispositivo.
        È il motivo per cui si reimposta una password.
      </p>
    </form>
  );
}
