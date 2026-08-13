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

/* LE ANCORE DEL PIEDE NON ESISTONO PIU'.
   «Come funziona» e il registro erano due sezioni in fondo alla lista,
   raggiunte da due `href="#..."`. Adesso sono due pagine con un indirizzo
   proprio — /come-funziona/ e /progressi/ — e una costante che tenesse in vita
   il vecchio salto sarebbe solo un modo di non accorgersi che nessuno la usa
   piu'. Restano le ancore che descrivono qualcosa che sta davvero DENTRO una
   pagina, come quella di campionato qui sopra. */
