'use client';

import { useSyncExternalStore } from 'react';

/**
 * UN PARAMETRO DELL'INDIRIZZO, LETTO DAL BROWSER.
 *
 * PERCHE' NON `useSearchParams` DI NEXT. Il sito e' un export statico: in fase
 * di build non esiste nessuna richiesta, e quindi nessuna stringa di ricerca.
 * `useSearchParams` obbliga a mettere l'intera pagina dentro un `<Suspense>`
 * per un'informazione che comunque arriva solo nel browser — cerimonia senza
 * guadagno.
 *
 * PERCHE' NON UN `useEffect`. Leggere `location` in un effetto e chiamare
 * `setState` subito dopo funziona, ma costa un secondo render a ogni pagina e
 * la regola `react-hooks/set-state-in-effect` lo segnala a ragione: e' un
 * valore che si LEGGE, non un cambio di stato da propagare.
 *
 * `useSyncExternalStore` e' esattamente lo strumento per questo caso. React
 * usa lo scatto del server per il primo render — quello che deve combaciare
 * con l'HTML — e passa a quello del browser subito dopo l'idratazione, senza
 * lamentarsi della differenza: e' la differenza il motivo per cui esiste.
 *
 * IL VALORE HA TRE FORME, e sono tre cose diverse:
 *   `undefined` — il browser non ha ancora parlato. Non vuol dire «manca».
 *   `null`      — il browser ha parlato: il parametro non c'e'.
 *   una stringa — c'e', ed e' questa.
 *
 * Schiacciare le prime due su un solo valore fa comparire «manca il codice»
 * per un istante a chi il codice ce l'ha, ed e' il guasto che questa firma
 * rende impossibile scrivere per sbaglio.
 */

/* L'indirizzo non cambia sotto i piedi di questa pagina: si arriva da un
   collegamento in un'email e si resta li'. Non c'e' niente a cui iscriversi,
   e la funzione di disiscrizione non ha niente da disfare. */
const MAI = () => () => {};

const SUL_SERVER = () => undefined;

export function useParametro(nome: string): string | null | undefined {
  return useSyncExternalStore(
    MAI,
    () => new URLSearchParams(window.location.search).get(nome),
    SUL_SERVER,
  );
}
