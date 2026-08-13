'use client';

import { useRouter } from 'next/navigation';
import { useState, type FormEvent } from 'react';

import { MINIMO_PASSWORD, profilo, ErroreProfilo, type Utente } from '@/lib/profilo';

import { useSessione } from './Sessione';

/**
 * IL MODULO DI ACCESSO E DI REGISTRAZIONE, che sono lo stesso modulo con un
 * campo in piu'.
 *
 * TUTTO IL LAVORO DI QUESTO FILE STA NEGLI STATI D'ERRORE, che sono la parte
 * che nessuno disegna e l'unica che l'utente incontra quando ha un problema.
 * Ce ne sono quattro, e sono diversi:
 *
 *   · il servizio non risponde       → non e' colpa tua, il sito funziona
 *   · le credenziali non tornano     → riprova, e il campo password si svuota
 *   · troppi tentativi               → quanto aspettare, detto in minuti
 *   · il modulo non e' valido        → quale campo, evidenziato
 *
 * Un solo «errore, riprova» per tutti e quattro sarebbe la cosa piu' facile e
 * lascerebbe l'utente senza sapere se il problema e' suo o nostro.
 *
 * NIENTE `disabled` SUL BOTTONE MENTRE SI ASPETTA. Un bottone disattivato non
 * riceve il fuoco e i lettori di schermo smettono di annunciarlo: chi ascolta
 * perde il punto in cui si trovava. Resta attivo, cambia testo, e il secondo
 * clic viene ignorato dal codice.
 *
 * L'ERRORE E' IN UNA REGIONE `aria-live`, cosi' chi non vede lo schermo lo
 * sente comparire invece di doverlo andare a cercare.
 *
 * I CAMPI NON SONO CONTROLLATI, e non e' pigrizia: e' un difetto vero, trovato
 * provando il giro con un browser. Il sito e' statico — l'HTML arriva prima del
 * JavaScript — e un campo controllato viene RIAZZERATO quando React idrata la
 * pagina, perche' in quel momento lo stato del componente e' ancora la stringa
 * vuota. Chi digita in fretta su una connessione lenta si vede sparire quello
 * che ha scritto, e sul modulo d'accesso si vede sparire la password senza
 * capire perche'.
 *
 * Con campi non controllati il valore vive nel DOM, l'idratazione non lo tocca,
 * e al momento dell'invio si legge con `FormData`. In piu' sparisce un render
 * per ogni tasto premuto.
 */

type Modo = 'accesso' | 'registrazione';

const TESTI = {
  accesso: {
    titolo: 'Entra',
    bottone: 'Entra',
    inCorso: 'Sto entrando…',
    altro: 'Non hai un profilo?',
    altroLink: '/registrati/',
    altroTesto: 'Creane uno',
  },
  registrazione: {
    titolo: 'Crea un profilo',
    bottone: 'Crea il profilo',
    inCorso: 'Sto creando il profilo…',
    altro: 'Hai già un profilo?',
    altroLink: '/accedi/',
    altroTesto: 'Entra',
  },
} as const;

export function ModuloProfilo({ modo }: { modo: Modo }) {
  const t = TESTI[modo];
  const router = useRouter();
  const { aggiorna } = useSessione();

  const [inCorso, setInCorso] = useState(false);
  const [errore, setErrore] = useState<ErroreProfilo | null>(null);

  async function invia(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (inCorso) return;
    const modulo = e.currentTarget;
    const dati = new FormData(modulo);
    const email = String(dati.get('email') ?? '');
    const nome = String(dati.get('nome') ?? '');
    const password = String(dati.get('password') ?? '');

    setInCorso(true);
    setErrore(null);
    try {
      const u: Utente =
        modo === 'accesso'
          ? await profilo.accesso({ email, password })
          : await profilo.registrazione({ email, nome, password });
      aggiorna(u);
      router.push('/profilo/');
    } catch (err) {
      const e2 = err instanceof ErroreProfilo ? err : null;
      setErrore(
        e2 ??
          new ErroreProfilo('errore_sconosciuto', 'Qualcosa non ha funzionato. Riprova.', 0),
      );
      // La password si svuota SEMPRE dopo un errore, anche quando il problema
      // era la rete: se qualcuno guarda lo schermo alle spalle, un campo pieno
      // dopo un errore e' il momento in cui resta li' piu' a lungo.
      // Si tocca il DOM perche' il campo non e' controllato, ed e' il solo
      // punto in cui questo modulo lo fa.
      const campo = modulo.elements.namedItem('password');
      if (campo instanceof HTMLInputElement) {
        campo.value = '';
        campo.focus();
      }
    } finally {
      setInCorso(false);
    }
  }

  const codice = errore?.codice;
  const suPassword = codice === 'credenziali_non_valide' || codice === 'dati_non_validi';

  return (
    <form className="modulo" onSubmit={invia} noValidate>
      <h1 className="titolo-sezione">{t.titolo}</h1>

      {errore ? (
        <p
          className={`modulo__errore${codice === 'rete_non_raggiungibile' ? ' modulo__errore--nostro' : ''}`}
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

      {modo === 'registrazione' ? (
        <label className="modulo__campo">
          <span className="modulo__etichetta">Come ti chiamiamo</span>
          <input
            className="modulo__casella"
            type="text"
            name="nome"
            autoComplete="given-name"
            required
            minLength={2}
            maxLength={60}
          />
          <span className="modulo__aiuto">
            Solo per salutarti. Non compare da nessuna parte se non nella tua pagina.
          </span>
        </label>
      ) : null}

      <label className="modulo__campo">
        <span className="modulo__etichetta">Password</span>
        <input
          className="modulo__casella"
          type="password"
          name="password"
          /* `new-password` in registrazione fa proporre al gestore di password
             una password generata; `current-password` in accesso gli fa
             compilare quella salvata. Scambiarli e' il difetto per cui i
             gestori di password «non funzionano» su tanti siti. */
          autoComplete={modo === 'registrazione' ? 'new-password' : 'current-password'}
          required
          minLength={modo === 'registrazione' ? MINIMO_PASSWORD : 1}
          aria-invalid={suPassword || undefined}
        />
        {modo === 'registrazione' ? (
          <span className="modulo__aiuto">Almeno {MINIMO_PASSWORD} caratteri.</span>
        ) : null}
      </label>

      <button className="azione azione--piena" type="submit" aria-busy={inCorso}>
        {inCorso ? t.inCorso : t.bottone}
      </button>

      <p className="modulo__altro">
        {t.altro} <a href={t.altroLink}>{t.altroTesto}</a>
      </p>

      {modo === 'accesso' ? (
        <p className="modulo__altro">
          <a href="/recupero/">Password dimenticata?</a>
        </p>
      ) : null}

      {modo === 'registrazione' ? (
        <p className="modulo__patto">
          Un profilo serve a ritrovare le tue cose. <strong>Non cambia i pronostici</strong>: sono
          gli stessi per tutti, pubblici, e restano leggibili senza registrarsi. Non mandiamo
          posta pubblicitaria e non cediamo l’indirizzo a nessuno. Puoi chiudere il profilo
          quando vuoi, e sparisce davvero.
        </p>
      ) : null}
    </form>
  );
}
