'use client';

import { useSyncExternalStore } from 'react';

/**
 * E' GIA' PASSATO QUESTO ISTANTE?
 *
 * IL PROBLEMA CHE RISOLVE. Questo sito e' un export statico: l'HTML e' scritto
 * una volta, di notte, e poi resta fermo fino alla ricostruzione dopo. Un
 * `Date.now()` dentro un componente non e' «adesso», e' «l'ora in cui e' stata
 * costruita la pagina» — e le due cose distano fino a ventiquattro ore.
 *
 * Il difetto che ne veniva era piccolo e brutto: una partita cominciata dopo
 * l'ultima costruzione continuava a promettere «l'arbitro esce a pochi giorni
 * dal fischio» mentre la partita era in corso.
 *
 * PERCHE' NON UN `useEffect` CON `setState`. Perche' il primo render dovrebbe
 * comunque dire la stessa cosa dell'HTML — altrimenti React protesta per un
 * disallineamento — e allora tanto vale dichiararlo: e' esattamente il
 * contratto di `useSyncExternalStore`, che ha uno scatto per il server e uno
 * per il browser e sa che sono diversi.
 *
 * LO SCATTO DEL SERVER LO PASSA CHI CHIAMA, e non e' un dettaglio: e' quello
 * che finisce nell'HTML. Deve essere la verita' AL MOMENTO DELLA COSTRUZIONE
 * (`COSTRUZIONE` in `lib/dati`), non un `false` di comodo. Con `false` fisso,
 * una partita di una settimana fa verrebbe scritta nell'HTML come «non ancora
 * giocata» e il browser la correggerebbe subito dopo: un lampo di contenuto
 * sbagliato su ogni pagina vecchia, per risolvere un problema che riguarda
 * solo le ultime ore.
 *
 * Quello che resta scoperto e' esattamente la finestra fra la costruzione e
 * adesso — al massimo una notte — ed e' la finestra per cui questo file esiste.
 *
 * L'ISCRIZIONE E' UN TIMER, quindi la pagina lasciata aperta si corregge da
 * sola al fischio d'inizio invece di aspettare un ricaricamento.
 */
export function usePassato(istante: number, allaCostruzione: boolean): boolean {
  return useSyncExternalStore(
    (avvisa) => {
      const mancano = istante - Date.now();
      if (mancano <= 0) return () => {};
      // `setTimeout` sopra i 24,8 giorni va in overflow e scatta SUBITO: il
      // numero e' a 32 bit con segno. Oltre quella soglia non si arma niente —
      // una pagina non resta aperta un mese, e se resta, si ricarica.
      if (mancano > 2 ** 31 - 1) return () => {};
      const t = setTimeout(avvisa, mancano);
      return () => clearTimeout(t);
    },
    () => Date.now() >= istante,
    () => allaCostruzione,
  );
}
