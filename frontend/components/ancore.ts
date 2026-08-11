/**
 * L'ancora di un campionato dentro la pagina del giorno.
 *
 * Sta in un file suo perché la scrivono in due — il gruppo nella lista
 * (`<details id>`) e la voce nella barra laterale (`<a href="#…">`) — e due
 * copie della stessa regola di formattazione sono un link rotto che aspetta.
 */
export function ancoraCampionato(codice: string): string {
  return `campionato-${codice.toLowerCase()}`;
}
