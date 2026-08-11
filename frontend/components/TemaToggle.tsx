'use client';

import { useSyncExternalStore } from 'react';

type Tema = 'light' | 'dark';

const EVENTO = 'tema-cambiato';

/**
 * Il tema scuro è il DEFAULT DEL PRODOTTO e non segue la preferenza di
 * sistema: `:root` è scuro, il chiaro si ottiene solo da qui (MASTER §1).
 * È una decisione di marca — il fondo chiaro uniforme era ciò che faceva
 * leggere il prodotto come un foglio A4.
 *
 * La mitigazione dovuta è questo bottone: sempre visibile in testata, 44×44,
 * con LA PAROLA dello stato invece di una sola icona, e la scelta persistita
 * e applicata prima del primo paint.
 *
 * Il tema vero vive fuori da React — è l'attributo `data-theme` sull'elemento
 * radice. Qui lo si legge con useSyncExternalStore invece di duplicarlo in
 * uno stato: così non esiste il momento in cui i due valori divergono.
 *
 * Senza JavaScript il bottone non compare: il tema resta lo scuro di
 * progetto, quindi non si perde niente. Un bottone morto sarebbe peggio di
 * nessun bottone.
 */
function sottoscrivi(notifica: () => void): () => void {
  window.addEventListener(EVENTO, notifica);
  return () => window.removeEventListener(EVENTO, notifica);
}

function istantanea(): Tema {
  return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
}

/* Durante il render sul server il tema non è conoscibile: si parte dal
   default di progetto e useSyncExternalStore riallinea dopo l'idratazione. */
function istantaneaServer(): Tema {
  return 'dark';
}

/* --surface-2 nei due temi: e' il fondo della testata, cioe' la superficie che
   tocca il cromo del browser. Deve restare allineato a `themeColor` in
   app/layout.tsx e allo script che applica il tema prima del primo paint. */
const META: Record<Tema, string> = { dark: '#151A20', light: '#E3E8ED' };

export function TemaToggle() {
  const tema = useSyncExternalStore(sottoscrivi, istantanea, istantaneaServer);

  function cambia() {
    const prossimo: Tema = tema === 'dark' ? 'light' : 'dark';
    if (prossimo === 'light') document.documentElement.setAttribute('data-theme', 'light');
    else document.documentElement.removeAttribute('data-theme');

    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', META[prossimo]);

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
      className="bottone"
      onClick={cambia}
      aria-label={tema === 'dark' ? 'Passa al tema chiaro' : 'Passa al tema scuro'}
    >
      {/* Il quadratino e' pieno per lo scuro e vuoto per il chiaro, ma la
          PAROLA resta accanto: il glifo non porta mai il significato da solo. */}
      <span
        className={`bottone__marca${tema === 'dark' ? '' : ' bottone__marca--piena'}`}
        aria-hidden="true"
      />
      {tema === 'dark' ? 'Chiaro' : 'Scuro'}
    </button>
  );
}
