import { notFound } from 'next/navigation';

import { PROFILI_ACCESI } from './profilo';

/**
 * FERMA LE PAGINE DEI PROFILI QUANDO I PROFILI SONO SPENTI.
 *
 * `lib/profilo.ts` promette che senza `NEXT_PUBLIC_API_PROFILI` non finiscono
 * «pagine dei profili negli indirizzi pubblicati». La voce «Accedi» spariva
 * davvero, ma le pagine venivano esportate lo stesso: `/accedi` pubblicava un
 * modulo con due campi e un bottone che, senza un indirizzo a cui parlare, non
 * poteva fare niente. Un modulo morto su un sito pubblico e' peggio di una
 * pagina che non c'e'.
 *
 * Va chiamata come prima istruzione del componente di pagina: in export
 * statico `notFound()` viene risolta a build, quindi quell'indirizzo non
 * esiste proprio nel sito pubblicato.
 */
export function soloSeProfiliAccesi(): void {
  if (!PROFILI_ACCESI) {
    notFound();
  }
}
