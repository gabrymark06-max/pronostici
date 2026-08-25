/**
 * LE QUOTE, E UNA REGOLA SOLA: una quota è un prezzo che qualcuno espone
 * davvero, oppure non esiste.
 *
 * Fino al 25 agosto 2026 qui vivevano tre numeri. Due erano calcolati da noi:
 * `1 / probabilità nostra` — chiamata «la nostra quota equa» — e
 * `1 / probabilità di mercato sgonfiata`. Erano etichettati, e l'etichetta non
 * bastava: un numero con due decimali stampato sotto la parola «quota» viene
 * letto come un prezzo, perché è così che si legge una quota. Nessun operatore
 * pagava quei numeri.
 *
 * **Resta il terzo**: la mediana lorda degli operatori che quel mercato lo
 * quotano. Ha il margine dentro, ed è l'unico che qualcuno può davvero giocare.
 *
 * COSA NON SI PERDE. La probabilità c'è ancora, ed è sempre stata il prodotto:
 * `1/p` non aggiungeva informazione, la travestiva. Dove il prezzo non c'è, la
 * pagina mostra la probabilità e tace sulla quota — che è il vero stato delle
 * cose.
 *
 * DUE FONTI, entrambe di prezzi veri:
 *
 * ① `odds.prices` — the-odds-api, mediana di operatori europei o ADM. Copre
 *    cinque mercati: esito finale e Over/Under 2,5 e 3,5.
 * ② `contorno.prezzi` — betexplorer, mediana degli operatori che mostra a chi
 *    chiede. Copre doppia chance, gol totali su ogni linea, entrambe segnano.
 *
 * Misurato il 25 agosto 2026 sui pronostici consigliati: con la sola ① quattro
 * su trentatré avevano un prezzo, con entrambe undici. I restanti sono gol di
 * squadra e handicap europeo, che nessuna fonte gratuita quota — e lì non si
 * inventa niente.
 *
 * PERCHÉ NON C'È SISAL. Nessuna fonte gratuita la espone: the-odds-api non la
 * include in nessuna regione, verificato sulla loro tavola dei bookmaker. Non
 * si inventa un prezzo per un marchio che non abbiamo, e non si scrive
 * «Sisal» sopra il numero di un altro.
 *
 * NON SI NOMINA L'OPERATORE. Il prezzo compare come consenso: mostrare il
 * marchio di un operatore senza un accordo è pubblicità non richiesta, e a
 * distanza di ore sarebbe anche un prezzo stantio spacciato per fresco.
 */
import { decimale, suCento } from './formato';
import { contornoDi } from './contorno';
import type { Fixture, Mercato } from './tipi';

export interface QuoteDelMercato {
  /** IL PREZZO, quello vero. `null` quando nessuna fonte quota il mercato. */
  prezzo: number | null;
  /** `it` = operatori ADM italiani, `eu` = mediana europea, `us` = betexplorer. */
  provenienza: 'it' | 'eu' | 'us' | null;
  /** Quanti operatori compongono il consenso. */
  operatori: number;
  /**
   * DA DOVE VIENE IL PREZZO.
   *
   * `principale` è the-odds-api, la fonte su cui il progetto si è fatto
   * misurare. `secondaria` è betexplorer, che copre i mercati che la prima non
   * quota. Le due non si mescolano mai nella stessa cella, e la pagina lo dice:
   * un numero senza provenienza è un numero di cui non si può discutere.
   */
  fonte: 'principale' | 'secondaria' | null;
  /**
   * La probabilità che il mercato attribuisce all'esito, tolto il margine.
   *
   * NON è una quota e non va stampata come tale: è il termine di confronto con
   * la nostra stima, ed è un numero fra 0 e 1. Sta qui perché il confronto fra
   * le due probabilità resta il modo in cui il pronostico si rende
   * verificabile.
   */
  pMercato: number | null;
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
export function quoteDi(mercato: Mercato, fixture: Fixture): QuoteDelMercato {
  /* SI PASSA LA PARTITA, non i suoi pezzi.
     Prima questa funzione prendeva `odds` e il contorno separati, e un
     chiamante le passava `contorno.market_p` al posto del contorno: le sole
     probabilita' dove servivano anche i prezzi. Il typecheck non se n'e'
     accorto — un `Record<string, number>` e' assegnabile a un tipo di sole
     proprieta' opzionali, perche' l'index signature non dichiara nessuna
     proprieta' e il controllo passa a vuoto — e per un giorno la tavola dei
     mercati e' rimasta vuota su ogni partita.
     Con la partita intera l'errore non e' rappresentabile. */
  const odds = fixture.odds;
  const contorno = contornoDi(fixture);
  const prezzoPrincipale = odds?.prices?.[mercato.key];
  const haPrincipale = typeof prezzoPrincipale === 'number' && prezzoPrincipale > 1;

  const trovato = contorno?.prezzi?.[mercato.key];
  const prezzoSecondario = trovato?.decimale;
  /* La principale ha SEMPRE la precedenza, anche quando la secondaria copre lo
     stesso mercato: è quella su cui il progetto si è fatto misurare, e cambiare
     fonte a parità di disponibilità renderebbe due partite non confrontabili
     fra loro. */
  const haSecondario =
    !haPrincipale && typeof prezzoSecondario === 'number' && prezzoSecondario > 1;

  const pPrincipale = odds?.market_p?.[mercato.key];
  const pSecondaria = contorno?.market_p?.[mercato.key];
  const p =
    typeof pPrincipale === 'number' && pPrincipale > 0 && pPrincipale < 1
      ? pPrincipale
      : typeof pSecondaria === 'number' && pSecondaria > 0 && pSecondaria < 1
        ? pSecondaria
        : null;

  return {
    prezzo: haPrincipale ? prezzoPrincipale : haSecondario ? prezzoSecondario : null,
    provenienza: haPrincipale ? (odds?.price_scope === 'it' ? 'it' : 'eu') : haSecondario ? 'us' : null,
    operatori: haPrincipale ? (odds?.price_books ?? 0) : haSecondario ? (trovato?.operatori ?? 0) : 0,
    fonte: haPrincipale ? 'principale' : haSecondario ? 'secondaria' : null,
    pMercato: p,
  };
}

/** Comoda per la riga di lista: le quote del pronostico consigliato. */
export function quoteDelPronostico(fixture: Fixture): QuoteDelMercato | null {
  if (fixture.prediction === null) return null;
  return quoteDi(fixture.prediction, fixture);
}

/**
 * Il confronto fra la nostra stima e quella del mercato, in parole.
 *
 * SI CONFRONTANO DUE PROBABILITÀ, non due quote. Prima qui comparivano
 * `1/p` e `1/p_mercato`: due numeri esatti, e nessuno dei due un prezzo. Le
 * probabilità dicono la stessa cosa senza travestirsi da qualcosa che nessuno
 * paga.
 *
 * La soglia dell'uno per cento non è estetica: sotto quella differenza il
 * de-vig e l'arrotondamento pesano quanto il segnale, e scrivere «più
 * probabile» su uno scarto che sta dentro il rumore sarebbe dare una
 * precisione che non abbiamo.
 */
export function fraseConfronto(q: QuoteDelMercato, nostra: number): string | null {
  if (q.pMercato === null) return null;

  const scarto = q.pMercato - nostra;
  const numeri =
    `Noi la diamo al ${suCento(nostra)} su 100, il mercato al ` +
    `${suCento(q.pMercato)} (a margine tolto).`;

  if (Math.abs(scarto) < 0.01) {
    return `${numeri} Siamo d’accordo: su questa scommessa non vediamo niente che il mercato non veda già.`;
  }
  if (scarto < 0) {
    return `${numeri} Il mercato la dà per meno probabile di noi.`;
  }
  return `${numeri} Il mercato la dà per più probabile di noi.`;
}

/** La riga sul prezzo lordo, quando lo conosciamo. Nomina la provenienza, mai l'operatore. */
export function fraseSportello(q: QuoteDelMercato): string | null {
  if (q.prezzo === null) return null;
  /* DA DOVE VENGONO, DETTO GIUSTO. La fonte secondaria mostra operatori
     diversi a seconda dell'indirizzo di chi chiede, e i nostri giri partono da
     runner americani: sono `bet365.us`, `betmgm.us`, `stake.com`. Scriverli
     «europei» perche' quello diceva il ramo di ripiego era una piccola bugia
     dentro una modifica fatta apposta per toglierle. */
  const dove =
    q.provenienza === 'it'
      ? 'con licenza italiana'
      : q.provenienza === 'us'
        ? 'statunitensi'
        : 'europei';
  const fonte =
    q.operatori === 1 ? `un operatore ${dove}` : `${q.operatori} operatori ${dove}`;
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
  if (q.pMercato === null) return null;
  return Math.min(1, Math.max(0, q.pMercato));
}
