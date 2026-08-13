/**
 * IL CLIENTE DELL'API DEI PROFILI.
 *
 * COSA NON CAMBIA. Il sito resta un export statico: le pagine dei pronostici
 * si costruiscono la notte, non chiamano niente, e reggono qualunque traffico.
 * L'accesso e' l'unica cosa che parla con un server, e ci parla DAL BROWSER,
 * verso un servizio con un altro indirizzo e un altro ciclo di vita. Se quel
 * servizio cade, il sito continua a pubblicare: si perde solo la possibilita'
 * di entrare.
 *
 * I GETTONI NON PASSANO DA QUI. Stanno in cookie `httpOnly` che questo codice
 * non puo' leggere nemmeno volendo — e' il punto. Da qui si mette solo
 * `credentials: 'include'`, che dice al browser di allegarli.
 *
 * L'ERRORE HA SEMPRE LA STESSA FORMA, e questo modulo la traduce in
 * un'eccezione con il `codice` dentro. Le pagine accendono i messaggi sul
 * codice, mai sul testo: il testo puo' cambiare, il codice no.
 */

/** L'indirizzo dell'API, deciso in fase di build. Vuoto = profili spenti. */
export const API = process.env.NEXT_PUBLIC_API_PROFILI ?? '';

/**
 * I profili si accendono solo se qualcuno ha configurato l'indirizzo.
 *
 * Senza, il sito si costruisce e funziona esattamente come prima: niente voce
 * «Accedi», niente pagine dei profili negli indirizzi pubblicati. E' l'unico modo
 * di aggiungere un servizio che puo' non esserci senza mettere in pagina bottoni
 * che non fanno niente.
 */
export const PROFILI_ACCESI = API !== '';

export interface Utente {
  id: string;
  email: string;
  nome: string;
  email_verificata: boolean;
  creato: string;
  ultimo_accesso: string | null;
}

export interface SessioneAperta {
  id: string;
  creata: string;
  scade: string;
  agente: string | null;
  corrente: boolean;
}

export class ErroreProfilo extends Error {
  constructor(
    readonly codice: string,
    messaggio: string,
    readonly stato: number,
  ) {
    super(messaggio);
    this.name = 'ErroreProfilo';
  }
}

/** Quando la rete non risponde affatto. Non e' un errore dell'API: e' l'assenza
 *  dell'API, e va detta in modo diverso. */
export const CODICE_RETE = 'rete_non_raggiungibile';

async function chiama<T>(percorso: string, opzioni: RequestInit = {}): Promise<T> {
  let risposta: Response;
  try {
    risposta = await fetch(`${API}${percorso}`, {
      ...opzioni,
      // Senza questo i cookie non partono e non tornano: e' l'intera
      // meccanica della sessione.
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(opzioni.headers ?? {}) },
    });
  } catch {
    throw new ErroreProfilo(
      CODICE_RETE,
      'Non riesco a raggiungere il servizio dei profili. Il sito funziona lo stesso: sono solo i profili a essere irraggiungibili.',
      0,
    );
  }

  if (risposta.status === 204) return undefined as T;

  let corpo: unknown;
  try {
    corpo = await risposta.json();
  } catch {
    corpo = null;
  }

  if (!risposta.ok) {
    const e = (corpo as { errore?: { codice?: string; dettaglio?: string } } | null)?.errore;
    throw new ErroreProfilo(
      e?.codice ?? 'errore_sconosciuto',
      e?.dettaglio ?? 'Qualcosa non ha funzionato. Riprova.',
      risposta.status,
    );
  }
  return corpo as T;
}

const invia = (percorso: string, dati?: unknown) =>
  chiama<Utente>(percorso, {
    method: 'POST',
    body: dati === undefined ? undefined : JSON.stringify(dati),
  });

/** Il minimo, uguale a quello del backend (`schemi.MINIMO_PASSWORD`). */
export const MINIMO_PASSWORD = 10;

export const profilo = {
  registrazione: (dati: { email: string; nome: string; password: string }) =>
    invia('/profili/registrazione', dati),

  accesso: (dati: { email: string; password: string }) => invia('/profili/accesso', dati),

  /** Chiamata al caricamento di ogni pagina: e' quella che riaccende la sessione
   *  quando il gettone d'accesso e' scaduto ma quello di rinnovo no. */
  rinnovo: () => invia('/profili/rinnovo'),

  io: () => chiama<Utente>('/profili/io'),

  uscita: () => chiama<{ fatto: boolean }>('/profili/uscita', { method: 'POST' }),

  uscitaOvunque: () => chiama<{ fatto: boolean }>('/profili/uscita-ovunque', { method: 'POST' }),

  sessioni: () => chiama<SessioneAperta[]>('/profili/sessioni'),

  cambioPassword: (dati: { password_attuale: string; password_nuova: string }) =>
    chiama<{ fatto: boolean }>('/profili/password', {
      method: 'POST',
      body: JSON.stringify(dati),
    }),

  chiusura: (dati: { password: string }) =>
    chiama<{ fatto: boolean }>('/profili/chiusura', {
      method: 'POST',
      body: JSON.stringify(dati),
    }),

  /* --- La posta --------------------------------------------------------- */

  /** Rispedisce il messaggio di conferma dell'indirizzo. */
  rinviaVerifica: () =>
    chiama<{ fatto: boolean }>('/profili/verifica/invio', { method: 'POST' }),

  /** Conferma l'indirizzo con il gettone dell'email. Non serve essere collegati. */
  verifica: (gettone: string) =>
    chiama<Utente>('/profili/verifica', {
      method: 'POST',
      body: JSON.stringify({ gettone }),
    }),

  /** Chiede il collegamento per reimpostare la password.
   *  Risponde sempre allo stesso modo, che il profilo esista o no. */
  recupero: (email: string) =>
    chiama<{ fatto: boolean }>('/profili/recupero', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  confermaRecupero: (dati: { gettone: string; password_nuova: string }) =>
    chiama<{ fatto: boolean }>('/profili/recupero/conferma', {
      method: 'POST',
      body: JSON.stringify(dati),
    }),
};

/**
 * Chi sono, all'apertura della pagina.
 *
 * DUE CHIAMATE E NON UNA. `io` fallisce con 401 quando il gettone d'accesso e'
 * scaduto — succede dopo quindici minuti, cioe' quasi sempre — ma la sessione
 * puo' essere ancora viva: il gettone di rinnovo dura trenta giorni. Solo se
 * fallisce anche il rinnovo si e' davvero fuori.
 *
 * Restituisce `null` invece di alzare: «non sei collegato» non e' un guasto, e
 * ogni chiamante dovrebbe intercettarlo per non mostrare un errore rosso a chi
 * sta semplicemente leggendo il sito senza profilo.
 */
export async function chiSono(): Promise<Utente | null> {
  if (!PROFILI_ACCESI) return null;
  try {
    return await profilo.io();
  } catch (e) {
    if (e instanceof ErroreProfilo && e.codice === CODICE_RETE) return null;
    try {
      return await profilo.rinnovo();
    } catch {
      return null;
    }
  }
}
