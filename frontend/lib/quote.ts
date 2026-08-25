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
 * TRE FONTI, tutte di prezzi veri, in quest'ordine di precedenza:
 *
 * ① `odds.prices` — the-odds-api, mediana di ventiquattro operatori europei o
 *    ADM. Copre cinque mercati: esito finale e Over/Under 2,5 e 3,5.
 * ② `contorno.prezzi` con `fonte: 'betexplorer'` — mediana degli operatori che
 *    mostra a chi chiede. Doppia chance, gol totali su ogni linea, entrambe
 *    segnano.
 * ③ `contorno.prezzi` con `fonte: 'kambi'` — UN operatore solo, e per questo
 *    ultimo. Copre gol di squadra e handicap europeo, che nessun comparatore
 *    gratuito pubblica, e fa da ripiego su tutto il resto dove le mediane non
 *    arrivano.
 *
 * L'ordine non è una preferenza estetica: una mediana di venti libri dice cosa
 * costa quella scommessa sul mercato, il prezzo di uno dice cosa costa da lui.
 * Dove c'è la mediana vince la mediana. Dove non c'è, un prezzo di un operatore
 * è meglio del silenzio — purché la pagina scriva «un operatore» e non «il
 * mercato», ed è quello che fa `fraseSportello`.
 *
 * Misurato sui pronostici consigliati delle 62 partite in cartellone: con la
 * sola ① quattro avevano un prezzo, con ①② quattordici, con tutte e tre
 * cinquantadue. Dei dieci rimasti, due sono combo che nessuno quota, tre sono
 * partite su cui il libro non è ancora aperto, e cinque sono linee che quel
 * bookmaker non espone per quella partita. Lì non si inventa niente.
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
  /** DOVE SONO GLI OPERATORI: `it` con licenza italiana, `eu` europei, `us` statunitensi. */
  provenienza: 'it' | 'eu' | 'us' | null;
  /**
   * Quanti operatori compongono il prezzo. UNO è un valore normale, non un
   * caso di confine: su gol di squadra e handicap europeo è quasi sempre uno,
   * e la pagina deve dirlo invece di far passare quel numero per un consenso.
   */
  operatori: number;
  /**
   * DA DOVE VIENE IL PREZZO.
   *
   * `principale` è the-odds-api, la fonte su cui il progetto si è fatto
   * misurare. `secondaria` è il contorno — betexplorer dove ha una mediana,
   * kambi dove nessuno ce l'ha. Le due non si mescolano mai nella stessa
   * cella, e la pagina lo dice: un numero senza provenienza è un numero di cui
   * non si può discutere.
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

  /* DUE FONTI DENTRO LA STESSA MAPPA, e non stanno nello stesso posto del
     mondo. `contorno.prezzi` lo riempivano solo le mediane di betexplorer, che
     dai nostri runner mostra libri statunitensi; dal 25 agosto 2026 lo riempie
     anche kambi, che è un operatore europeo e uno solo. Il campo `fonte` viaggia
     con il prezzo apposta: senza, la frase sarebbe giusta per una delle due e
     falsa per l'altra, e nessun controllo potrebbe pescarlo. */
  const doveSecondario = trovato?.fonte === 'kambi' ? 'eu' : 'us';

  return {
    prezzo: haPrincipale ? prezzoPrincipale : haSecondario ? prezzoSecondario : null,
    provenienza: haPrincipale
      ? odds?.price_scope === 'it'
        ? 'it'
        : 'eu'
      : haSecondario
        ? doveSecondario
        : null,
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
  /* AL SINGOLARE E AL PLURALE, perché adesso il singolare capita davvero.
     Finché le fonti erano due mediane, `operatori === 1` era un caso di
     confine; da quando c'è kambi è il caso normale su gol di squadra e
     handicap, e «un operatore europei» sarebbe la prima cosa che si legge. */
  const dove =
    q.provenienza === 'it'
      ? ['con licenza italiana', 'con licenza italiana']
      : q.provenienza === 'us'
        ? ['statunitense', 'statunitensi']
        : ['europeo', 'europei'];
  const fonte =
    q.operatori === 1
      ? `un operatore ${dove[0]}`
      : `${q.operatori} operatori ${dove[1]}`;
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
