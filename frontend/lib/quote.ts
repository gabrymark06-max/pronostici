/**
 * LE QUOTE.
 *
 * Due numeri diversi, con due statuti diversi, e la differenza fra i due è il
 * punto di tutto il prodotto.
 *
 * ① LA QUOTA EQUA — `1 / probabilità`. È SEMPRE disponibile, su ogni
 *    pronostico e su ogni mercato, perché è solo un'altra forma della
 *    probabilità che già mostriamo. Vuol dire: «a questa quota la scommessa è
 *    in pari; sotto, il valore atteso è negativo». È il numero più utile che
 *    possiamo dare, perché non dipende da dove uno gioca.
 *
 * ② LA QUOTA DI MERCATO — il prezzo lordo mediano degli operatori. Esiste solo
 *    su 1X2 e Over/Under, e solo sulle partite per cui il budget delle quote
 *    ha permesso una chiamata: sulla grande maggioranza dei pronostici NON
 *    c'è, e la lista deve reggere quella assenza senza sembrare rotta.
 *
 * PERCHÉ NON C'È SISAL. Nessuna fonte gratuita la espone: the-odds-api, che è
 * la nostra, non la include in nessuna regione. Gli unici due operatori con
 * licenza ADM disponibili sono Codere IT e Unibet IT, e sono quelli che
 * finiscono qui quando ci sono. Non si inventa un prezzo per un marchio che
 * non abbiamo, e non si scrive «Sisal» sopra il numero di un altro.
 *
 * NON SI NOMINA L'OPERATORE. Il prezzo compare come consenso e basta: mostrare
 * il marchio di un operatore senza un accordo è pubblicità non richiesta, e a
 * distanza di ore sarebbe anche un prezzo stantio spacciato per fresco.
 */
import { decimale } from './formato';
import type { Fixture, Mercato, Quote } from './tipi';

/** Sotto questa probabilità la quota equa esplode e smette di dire qualcosa. */
const P_MINIMA_PER_QUOTA = 0.01;

export interface QuoteDelMercato {
  /** `1 / p`, sempre presente. */
  equa: number;
  /** Il prezzo lordo del consenso, se quel mercato è quotato dalla fonte. */
  mercato: number | null;
  /** `it` = operatori ADM italiani, `eu` = mediana europea. */
  provenienza: 'it' | 'eu' | null;
  /** Quanti operatori compongono il consenso. */
  operatori: number;
}

/** `0.9153` → `1.09`. La sola forma in cui una quota equa entra in pagina. */
export function quotaEqua(p: number): number {
  return 1 / Math.max(p, P_MINIMA_PER_QUOTA);
}

/** `1.0925` → `"1,09"`. Due decimali, virgola italiana, sempre. */
export function formattaQuota(q: number): string {
  return decimale(q, 2);
}

/**
 * Le quote di un mercato dentro una partita.
 *
 * `odds.prices` usa le NOSTRE chiavi (`1x2_home`, `over_2.5`), non quelle
 * della fonte: la corrispondenza è già stata fatta nel backend, e qui basta
 * una lettura diretta. Quando la chiave non c'è — cioè quasi sempre, perché
 * handicap, doppia chance e gol di squadra non sono coperti — `mercato` resta
 * `null` e la colonna mostra un trattino.
 */
export function quoteDi(mercato: Mercato, odds: Quote | null | undefined): QuoteDelMercato {
  const prezzo = odds?.prices?.[mercato.key];
  const valido = typeof prezzo === 'number' && prezzo > 1;
  return {
    equa: quotaEqua(mercato.p),
    mercato: valido ? prezzo : null,
    provenienza: valido ? (odds?.price_scope === 'it' ? 'it' : 'eu') : null,
    operatori: odds?.price_books ?? 0,
  };
}

/** Comoda per la riga di lista: le quote del pronostico consigliato. */
export function quoteDelPronostico(fixture: Fixture): QuoteDelMercato | null {
  if (fixture.prediction === null) return null;
  return quoteDi(fixture.prediction, fixture.odds);
}

/**
 * Il margine fra il prezzo offerto e la nostra quota equa, in parole.
 *
 * Se il mercato paga PIÙ della quota equa, per noi quella scommessa ha valore
 * atteso positivo. Non è un consiglio a giocare — il pronostico è già stato
 * scelto senza guardare qui — ma è il confronto che rende il numero
 * verificabile da chiunque, ed è l'unica ragione per cui la quota di mercato
 * sta in pagina.
 */
export function fraseConfronto(q: QuoteDelMercato): string | null {
  if (q.mercato === null) return null;
  const fonte =
    q.provenienza === 'it'
      ? q.operatori === 1
        ? 'un operatore con licenza italiana'
        : `${q.operatori} operatori con licenza italiana`
      : `${q.operatori} operatori europei`;

  if (q.mercato > q.equa) {
    return (
      `Il mercato paga ${formattaQuota(q.mercato)} (${fonte}), sopra la nostra ` +
      `quota equa di ${formattaQuota(q.equa)}: per noi il prezzo è generoso.`
    );
  }
  return (
    `Il mercato paga ${formattaQuota(q.mercato)} (${fonte}), sotto la nostra ` +
    `quota equa di ${formattaQuota(q.equa)}: per noi il prezzo è caro.`
  );
}

/**
 * Dove sta la probabilità implicita nella quota di mercato, come frazione
 * 0–1. È la posizione della TACCA sul misurino: la distanza fra il
 * riempimento (noi) e la tacca (loro) È il vantaggio, e si vede senza leggere
 * un numero.
 *
 * Il prezzo è lordo — margine incluso — quindi `1/prezzo` sovrastima sempre un
 * po' la probabilità vera del mercato. La tacca è un riferimento visivo, non
 * una misura: per questo non porta mai un'etichetta numerica accanto.
 */
export function posizioneTacca(q: QuoteDelMercato): number | null {
  if (q.mercato === null) return null;
  return Math.min(1, Math.max(0, 1 / q.mercato));
}
