/**
 * Le ancore della pagina, in un posto solo.
 *
 * Stanno qui perché le scrivono in due — chi rende la sezione (`id=…`) e chi
 * ci punta dalla barra (`href="#…"`) — e due copie della stessa stringa sono
 * un link rotto che aspetta il momento buono.
 */

/** L'ancora di un campionato dentro la pagina del giorno. */
export function ancoraCampionato(codice: string): string {
  return `campionato-${codice.toLowerCase()}`;
}

/** Il blocco in fondo che spiega il punteggio, il silenzio e la quota equa. */
export const ANCORA_FUNZIONAMENTO = 'come-funziona';

/**
 * Il blocco in fondo con quanti pronostici sono usciti.
 *
 * Si chiama «registro» e non «rendimento» per una ragione di prodotto, non di
 * gusto: `rendimento` e' nella lista delle parole vietate del guardiano
 * (scripts/check-parole-vietate.mjs) insieme a ROI, profitto e puntata. Sono
 * tutte parole che promettono un guadagno, e questo sito non ne promette
 * nessuno. «Registro» dice cosa c'e' davvero: un elenco di cose scritte prima
 * e non modificate dopo.
 */
export const ANCORA_REGISTRO = 'registro';
