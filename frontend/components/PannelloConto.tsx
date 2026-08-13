'use client';

import { useEffect, useState, type FormEvent } from 'react';

import { conto, ErroreConto, type SessioneAperta } from '@/lib/conto';

import { useSessione } from './Sessione';

/**
 * LA PAGINA DEL CONTO.
 *
 * COSA C'E' DENTRO, e perche' e' poco: i tuoi dati, dove sei collegato, cambia
 * password, chiudi il conto. Niente altro, perche' oggi un conto non sblocca
 * niente — i pronostici sono pubblici e restano pubblici. Questa pagina lo
 * DICE invece di far cercare all'utente la funzione che non c'e'.
 *
 * LA PROTEZIONE E' DEL SERVER, NON DI QUESTA PAGINA. Su un sito statico
 * l'HTML e' scaricabile da chiunque: nascondere il pannello con un `if` non
 * protegge niente, perche' non c'e' niente da proteggere in questo file. I
 * dati arrivano da chiamate autenticate, e a dire di no e' l'API. Quello che
 * si fa qui e' NON MOSTRARE UN PANNELLO VUOTO a chi non e' collegato.
 *
 * CHIUDERE IL CONTO CHIEDE LA PASSWORD E POI CONFERMA. Sono due passaggi per
 * un'azione che non si annulla, e nessuno dei due e' un fastidio inutile: la
 * password ferma chi trovasse una sessione aperta, la conferma ferma il clic
 * distratto.
 */
export function PannelloConto() {
  const { utente, caricamento, aggiorna, esci } = useSessione();

  if (caricamento) {
    return <p className="pagina-conto__attesa">Un momento…</p>;
  }

  if (!utente) {
    return (
      <div className="pagina-conto__fuori">
        <h1 className="titolo-sezione">Non sei collegato</h1>
        <p>
          Questa pagina mostra i dati del tuo conto. <a href="/accedi/">Entra</a> oppure{' '}
          <a href="/registrati/">creane uno</a>.
        </p>
        <p className="pagina-conto__nota">
          I pronostici non stanno dietro l’accesso: sono pubblici e li trovi{' '}
          <a href="/">nella lista delle partite</a> senza registrarti.
        </p>
      </div>
    );
  }

  return (
    <div className="pagina-conto__dentro">
      <header className="pagina-conto__testata">
        <h1 className="titolo-sezione">Ciao {utente.nome}</h1>
        <p className="pagina-conto__nota">
          Un conto oggi <strong>non sblocca niente</strong>: i pronostici sono gli stessi per
          tutti e restano pubblici. Serve a farti ritrovare le tue cose quando ce ne saranno.
          Lo diciamo qui perché tu non vada a cercare una funzione che non esiste.
        </p>
      </header>

      <section className="riquadro">
        <h2 className="label">I tuoi dati</h2>
        <dl className="dati">
          <div>
            <dt>Email</dt>
            <dd className="num">{utente.email}</dd>
          </div>
          <div>
            <dt>Nome</dt>
            <dd>{utente.nome}</dd>
          </div>
          <div>
            <dt>Conto creato</dt>
            <dd className="num">{quando(utente.creato)}</dd>
          </div>
        </dl>
        <button className="azione" type="button" onClick={() => void esci()}>
          Esci
        </button>
      </section>

      <Sessioni />
      <CambioPassword onFatto={() => aggiorna(utente)} />
      <Chiusura onChiuso={() => aggiorna(null)} />
    </div>
  );
}

function quando(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' });
}

/* ------------------------------------------------------------------ */

function Sessioni() {
  const [righe, setRighe] = useState<SessioneAperta[] | null>(null);
  const [errore, setErrore] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    conto
      .sessioni()
      .then((r) => vivo && setRighe(r))
      .catch((e) => vivo && setErrore(e instanceof ErroreConto ? e.message : 'Non riesco a leggerle.'));
    return () => {
      vivo = false;
    };
  }, []);

  return (
    <section className="riquadro">
      <h2 className="label">Dove sei collegato</h2>
      {errore ? <p className="modulo__errore">{errore}</p> : null}
      {righe === null && !errore ? <p className="pagina-conto__attesa">Un momento…</p> : null}
      {righe?.length === 0 ? <p>Nessuna sessione aperta.</p> : null}
      {righe && righe.length > 0 ? (
        <ul className="sessioni">
          {righe.map((s) => (
            <li key={s.id} className="sessioni__riga">
              <span className="sessioni__agente">{leggibile(s.agente)}</span>
              <span className="sessioni__quando num">dal {quando(s.creata)}</span>
              {s.corrente ? <span className="sessioni__questa">questo browser</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
      <button
        className="azione"
        type="button"
        onClick={() => void conto.uscitaOvunque().then(() => location.reload())}
      >
        Chiudi tutte le sessioni
      </button>
      <p className="pagina-conto__nota">
        Chiude anche questa: dopo dovrai rientrare. È la cosa da fare se pensi che qualcun
        altro sia entrato.
      </p>
    </section>
  );
}

/** «Chrome su Windows» invece di 180 caratteri di stringa d'agente. Se non lo
 *  riconosciamo si dice cosi', invece di stampare la stringa cruda. */
function leggibile(agente: string | null): string {
  if (!agente) return 'Browser sconosciuto';
  const sistema = /Windows/i.test(agente)
    ? 'Windows'
    : /Android/i.test(agente)
      ? 'Android'
      : /iPhone|iPad/i.test(agente)
        ? 'iOS'
        : /Mac OS X/i.test(agente)
          ? 'Mac'
          : /Linux/i.test(agente)
            ? 'Linux'
            : null;
  const browser = /Edg\//.test(agente)
    ? 'Edge'
    : /Firefox\//.test(agente)
      ? 'Firefox'
      : /Chrome\//.test(agente)
        ? 'Chrome'
        : /Safari\//.test(agente)
          ? 'Safari'
          : null;
  if (!browser && !sistema) return 'Browser sconosciuto';
  return [browser ?? 'Browser', sistema ? `su ${sistema}` : ''].join(' ').trim();
}

/* ------------------------------------------------------------------ */

function CambioPassword({ onFatto }: { onFatto: () => void }) {
  const [esito, setEsito] = useState<string | null>(null);
  const [errore, setErrore] = useState<string | null>(null);
  const [inCorso, setInCorso] = useState(false);

  /* Campi non controllati, per la stessa ragione spiegata in `ModuloConto`:
     l'idratazione azzererebbe quello che l'utente ha gia' digitato. */
  async function invia(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (inCorso) return;
    const modulo = e.currentTarget;
    const dati = new FormData(modulo);
    setInCorso(true);
    setErrore(null);
    setEsito(null);
    try {
      await conto.cambioPassword({
        password_attuale: String(dati.get('attuale') ?? ''),
        password_nuova: String(dati.get('nuova') ?? ''),
      });
      setEsito('Fatto. Le altre sessioni sono state chiuse.');
      onFatto();
    } catch (err) {
      setErrore(err instanceof ErroreConto ? err.message : 'Non ha funzionato.');
    } finally {
      modulo.reset();
      setInCorso(false);
    }
  }

  return (
    <section className="riquadro">
      <h2 className="label">Cambia password</h2>
      <form className="modulo modulo--dentro" onSubmit={invia} noValidate>
        {errore ? (
          <p className="modulo__errore" role="alert">
            {errore}
          </p>
        ) : null}
        {esito ? (
          <p className="modulo__esito" role="status">
            {esito}
          </p>
        ) : null}
        <label className="modulo__campo">
          <span className="modulo__etichetta">Password di adesso</span>
          <input
            className="modulo__casella"
            type="password"
            name="attuale"
            autoComplete="current-password"
            required
          />
        </label>
        <label className="modulo__campo">
          <span className="modulo__etichetta">Password nuova</span>
          <input
            className="modulo__casella"
            type="password"
            name="nuova"
            autoComplete="new-password"
            required
            minLength={12}
          />
        </label>
        <button className="azione" type="submit" aria-busy={inCorso}>
          {inCorso ? 'Un momento…' : 'Cambia la password'}
        </button>
        <p className="modulo__aiuto">
          Cambiare la password chiude tutte le altre sessioni. È il motivo per cui si cambia.
        </p>
      </form>
    </section>
  );
}

/* ------------------------------------------------------------------ */

function Chiusura({ onChiuso }: { onChiuso: () => void }) {
  const [aperto, setAperto] = useState(false);
  const [errore, setErrore] = useState<string | null>(null);
  const [inCorso, setInCorso] = useState(false);

  async function invia(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (inCorso) return;
    const modulo = e.currentTarget;
    setInCorso(true);
    setErrore(null);
    try {
      await conto.chiusura({
        password: String(new FormData(modulo).get('password') ?? ''),
      });
      onChiuso();
      location.href = '/';
    } catch (err) {
      setErrore(err instanceof ErroreConto ? err.message : 'Non ha funzionato.');
      modulo.reset();
    } finally {
      setInCorso(false);
    }
  }

  return (
    <section className="riquadro riquadro--pericolo">
      <h2 className="label">Chiudi il conto</h2>
      <p>
        Il conto e i suoi dati vengono <strong>cancellati</strong>, non disattivati. Non c’è un
        ripensamento e non ne teniamo una copia.
      </p>
      {!aperto ? (
        <button className="azione azione--pericolo" type="button" onClick={() => setAperto(true)}>
          Voglio chiudere il conto
        </button>
      ) : (
        <form className="modulo modulo--dentro" onSubmit={invia} noValidate>
          {errore ? (
            <p className="modulo__errore" role="alert">
              {errore}
            </p>
          ) : null}
          <label className="modulo__campo">
            <span className="modulo__etichetta">Conferma con la password</span>
            <input
              className="modulo__casella"
              type="password"
              name="password"
              autoComplete="current-password"
              required
            />
          </label>
          <div className="modulo__coppia">
            <button className="azione azione--pericolo" type="submit" aria-busy={inCorso}>
              {inCorso ? 'Un momento…' : 'Cancella tutto'}
            </button>
            <button className="azione" type="button" onClick={() => setAperto(false)}>
              Lascia stare
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
