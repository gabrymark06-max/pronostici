/**
 * LE QUOTE.
 *
 * TRE numeri, con tre statuti diversi. Confonderli è il modo più facile di
 * mentire con dei numeri veri, quindi qui hanno tre nomi e tre funzioni.
 *
 * ① LA NOSTRA QUOTA EQUA — `1 / probabilità nostra`. SEMPRE disponibile, su
 *    ogni pronostico, perché è solo un'altra forma della probabilità che già
 *    mostriamo. Vuol dire: «a questa quota la scommessa è in pari; sotto, il
 *    valore atteso è negativo».
 *
 * ② LA QUOTA EQUA DEL MERCATO — `1 / probabilità di mercato sgonfiata`. È
 *    quello che il mercato pensa, tolto il margine dell'operatore. È il
 *    confronto che conta davvero, perché è pari a pari: la nostra stima contro
 *    la loro, senza che il margine sporchi la differenza. Ed è lo stesso
 *    numero che il modello usa internamente per decidere.
 *
 * ③ IL PREZZO ALLO SPORTELLO — la quota lorda mediana degli operatori. Ha il
 *    margine dentro, ed è l'unico dei tre che qualcuno può davvero giocare.
 *
 * COPERTURA, misurata e non sperata. ② esiste per gli undici mercati che le
 * quote gratuite determinano in modo esatto: 1X2, le tre doppie chance,
 * l'handicap europeo ±1, il multigol 0-2, Over/Under 2.5. ③ esiste solo per i
 * cinque quotati direttamente. Su gol di squadra, entrambe segnano e multigol
 * stretti non esiste nessuno dei due, e non si inventa: quelle scommesse la
 * fonte gratuita non le copre.
 *
 * PERCHÉ NON C'È SISAL. Nessuna fonte gratuita la espone: the-odds-api, che è
 * la nostra, non la include in nessuna regione — verificato sulla loro tavola
 * dei bookmaker. Gli unici due operatori con licenza ADM disponibili sono
 * Codere IT e Unibet IT, e sono quelli che finiscono in ③ quando ci sono. Non
 * si inventa un prezzo per un marchio che non abbiamo, e non si scrive
 * «Sisal» sopra il numero di un altro.
 *
 * NON SI NOMINA L'OPERATORE. Il prezzo compare come consenso: mostrare il
 * marchio di un operatore senza un accordo è pubblicità non richiesta, e a
 * distanza di ore sarebbe anche un prezzo stantio spacciato per fresco.
 */
import { decimale } from './formato';
import type { Fixture, Mercato, Quote } from './tipi';

/** Sotto questa probabilità la quota equa esplode e smette di dire qualcosa. */
const P_MINIMA_PER_QUOTA = 0.01;

export interface QuoteDelMercato {
  /** ① `1 / p` nostra. Sempre presente. */
  nostra: number;
  /** ② `1 / p` di mercato, sgonfiata. `null` se il mercato non lo determina. */
  mercato: number | null;
  /** ③ Il prezzo lordo allo sportello. `null` quasi sempre. */
  prezzo: number | null;
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
 * `odds.market_p` e `odds.prices` usano le NOSTRE chiavi (`1x2_home`,
 * `dc_x2`), non quelle della fonte: la corrispondenza è già stata fatta nel
 * backend, e qui basta una lettura diretta.
 */
export function quoteDi(mercato: Mercato, odds: Quote | null | undefined): QuoteDelMercato {
  const pMercato = odds?.market_p?.[mercato.key];
  const prezzo = odds?.prices?.[mercato.key];
  const haMercato = typeof pMercato === 'number' && pMercato > 0 && pMercato < 1;
  const haPrezzo = typeof prezzo === 'number' && prezzo > 1;

  return {
    nostra: quotaEqua(mercato.p),
    mercato: haMercato ? 1 / pMercato : null,
    prezzo: haPrezzo ? prezzo : null,
    provenienza: haPrezzo ? (odds?.price_scope === 'it' ? 'it' : 'eu') : null,
    operatori: odds?.price_books ?? 0,
  };
}

/** Comoda per la riga di lista: le quote del pronostico consigliato. */
export function quoteDelPronostico(fixture: Fixture): QuoteDelMercato | null {
  if (fixture.prediction === null) return null;
  return quoteDi(fixture.prediction, fixture.odds);
}

/**
 * Il confronto fra la nostra quota equa e quella del mercato, in parole.
 *
 * Se il mercato paga PIÙ di quanto paghiamo noi, vuol dire che dà l'evento per
 * meno probabile di quanto lo diamo noi: per noi quel prezzo è generoso. Non è
 * un consiglio a giocare — il pronostico è già stato scelto senza guardare qui
 * — ma è il confronto che rende il numero verificabile da chiunque.
 *
 * La soglia dell'uno per cento non è estetica: sotto quella differenza il
 * de-vig e l'arrotondamento a due decimali pesano quanto il segnale, e
 * scrivere «generoso» su uno scarto che sta dentro il rumore sarebbe dare
 * una precisione che non abbiamo.
 */
export function fraseConfronto(q: QuoteDelMercato): string | null {
  if (q.mercato === null) return null;

  const scarto = (q.mercato - q.nostra) / q.nostra;
  const numeri =
    `Noi diciamo ${formattaQuota(q.nostra)}, il mercato ${formattaQuota(q.mercato)}` +
    ' (a margine tolto).';

  if (Math.abs(scarto) < 0.01) {
    return `${numeri} Siamo d’accordo: su questa scommessa non vediamo niente che il mercato non veda già.`;
  }
  if (scarto > 0) {
    return `${numeri} Il mercato la dà per meno probabile di noi: se hai ragione tu a seguirci, il prezzo è dalla tua parte.`;
  }
  return `${numeri} Il mercato la dà per più probabile di noi: il prezzo che troverai è più caro del nostro valore.`;
}

/** La riga sul prezzo lordo, quando lo conosciamo. Nomina la provenienza, mai l'operatore. */
export function fraseSportello(q: QuoteDelMercato): string | null {
  if (q.prezzo === null) return null;
  const fonte =
    q.provenienza === 'it'
      ? q.operatori === 1
        ? 'un operatore con licenza italiana'
        : `${q.operatori} operatori con licenza italiana`
      : `${q.operatori} operatori europei`;
  return `Allo sportello questa scommessa si trova a ${formattaQuota(q.prezzo)} (${fonte}), margine incluso.`;
}

/**
 * Dove sta la probabilità di mercato, come frazione 0–1. È la posizione della
 * TACCA sul misurino: la distanza fra il riempimento (noi) e la tacca (loro) È
 * il vantaggio, e si vede senza leggere un numero.
 *
 * Si usa la probabilità SGONFIATA, non `1/prezzo`: il prezzo lordo contiene il
 * margine, quindi `1/prezzo` sovrastima sempre un po' e la tacca cadrebbe
 * sistematicamente a destra del vero. Una marca visiva storta in una sola
 * direzione è peggio di una marca assente.
 */
export function posizioneTacca(q: QuoteDelMercato): number | null {
  if (q.mercato === null) return null;
  return Math.min(1, Math.max(0, 1 / q.mercato));
}
