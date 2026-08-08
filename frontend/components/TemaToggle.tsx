'use client';

import { useSyncExternalStore } from 'react';

type Tema = 'light' | 'dark';

const EVENTO = 'tema-cambiato';

/**
 * Entrambi i temi sono di prima classe: il chiaro (carta calda) è il default
 * di progetto, lo scuro esiste completo per l'uso serale.
 *
 * Il tema vero vive fuori da React — è l'attributo `data-theme` sull'elemento
 * radice, che lo script nel <head> imposta prima del primo paint. Qui lo si
 * legge con useSyncExternalStore invece di duplicarlo in uno stato: così non
 * esiste il momento in cui i due valori divergono, e non c'è nessun lampo di
 * carta chiara per chi ha scelto il buio.
 *
 * Senza JavaScript il bottone non compare: il tema segue comunque
 * `prefers-color-scheme` via CSS, quindi non si perde niente. Un bottone morto
 * sarebbe peggio di nessun bottone.
 */
function sottoscrivi(notifica: () => void): () => void {
  const preferenza = window.matchMedia('(prefers-color-scheme: dark)');
  preferenza.addEventListener('change', notifica);
  window.addEventListener(EVENTO, notifica);
  return () => {
    preferenza.removeEventListener('change', notifica);
    window.removeEventListener(EVENTO, notifica);
  };
}

function istantanea(): Tema {
  const esplicito = document.documentElement.getAttribute('data-theme');
  if (esplicito === 'dark' || esplicito === 'light') return esplicito;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/* Durante il render sul server il tema non è conoscibile: si parte dal default
   di progetto e useSyncExternalStore riallinea subito dopo l'idratazione. */
function istantaneaServer(): Tema {
  return 'light';
}

export function TemaToggle() {
  const tema = useSyncExternalStore(sottoscrivi, istantanea, istantaneaServer);

  function cambia() {
    const prossimo: Tema = tema === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', prossimo);
    try {
      localStorage.setItem('tema', prossimo);
    } catch {
      /* modalità privata: il tema vale per questa sessione e basta. */
    }
    window.dispatchEvent(new Event(EVENTO));
  }

  return (
    <button
      type="button"
      className="tema"
      onClick={cambia}
      aria-label={tema === 'dark' ? 'Passa al tema chiaro' : 'Passa al tema scuro'}
    >
      {tema === 'dark' ? 'Chiaro' : 'Scuro'}
    </button>
  );
}
