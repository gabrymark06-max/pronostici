/**
 * I PREZZI DELLA FONTE PRINCIPALE, nella forma della tavola «Altri mercati».
 *
 * Quella tavola nasceva per la fonte secondaria, e leggeva solo lei. Ma anche
 * `odds.prices` sono prezzi veri — la mediana di operatori reali su esito
 * finale e gol totali — e su una partita che la secondaria non copre restavano
 * scritti nel dato e invisibili in pagina.
 *
 * Misurato il 25 agosto 2026 su Valencia-Betis: cinque prezzi veri in archivio,
 * nessun numero sulla scheda. Il pronostico consigliato era su una famiglia che
 * nessuno quota, e la tavola dei mercati leggeva solo l'altra fonte: il sito
 * sapeva quanto pagava l'1X2 e non lo diceva.
 *
 * Qui i due insiemi si presentano allo stesso modo. NON si mescolano: ogni
 * mercato porta la sua `fonte`, e la tavola dichiara la provenienza.
 */
import type { MercatoEsteso, Quote } from './tipi';

/** Le chiavi dell'esito finale, nell'ordine in cui si leggono. */
const ESITO_FINALE: { chiave: string; esito: string }[] = [
  { chiave: '1x2_home', esito: '1' },
  { chiave: '1x2_draw', esito: 'X' },
  { chiave: '1x2_away', esito: '2' },
];

const RE_LINEA = /^(over|under)_([\d.]+)$/;

function mercato(
  nome: string,
  linea: string | null,
  esiti: { esito: string; decimale: number }[],
  operatori: number,
  vincenti: number,
): MercatoEsteso | null {
  if (esiti.length < 2) return null;

  /* La somma delle inverse e' l'overround: quanto il banco si prende. Si
     calcola sui prezzi VERI che stiamo mostrando, non su probabilita' prese
     altrove — altrimenti il margine dichiarato non sarebbe quello di questi
     numeri. */
  const grezze = esiti.map((e) => 1 / e.decimale);
  const somma = grezze.reduce((a, b) => a + b, 0);

  return {
    fonte: 'the-odds-api',
    n_bookmaker: operatori,
    mercato: nome,
    linea,
    esiti: esiti.map((e, i) => ({
      esito: e.esito,
      decimale: e.decimale,
      probabilita_implicita: ((grezze[i] ?? 0) / somma) * vincenti,
    })),
    somma_probabilita: somma,
    margine_percento: (somma / vincenti - 1) * 100,
  };
}

/**
 * I mercati che la fonte principale quota, pronti per la tavola.
 *
 * Torna una lista vuota quando non c'e' nessun prezzo: non e' un guasto, e' una
 * partita che quella fonte non copre.
 */
export function mercatiPrincipali(odds: Quote | null | undefined): MercatoEsteso[] {
  const prezzi = odds?.prices;
  if (!prezzi) return [];
  const operatori = odds?.price_books ?? 0;
  const fuori: MercatoEsteso[] = [];

  const finale: { esito: string; decimale: number }[] = [];
  for (const v of ESITO_FINALE) {
    const q = prezzi[v.chiave];
    if (typeof q === 'number') finale.push({ esito: v.esito, decimale: q });
  }
  if (finale.length === ESITO_FINALE.length) {
    const m = mercato('Esito finale', null, finale, operatori, 1);
    if (m) fuori.push(m);
  }

  /* I gol totali arrivano a coppie: una linea senza il suo contrario non e'
     un mercato, e' meta' di un mercato — e il margine non si potrebbe
     calcolare. */
  const linee = new Set<string>();
  for (const chiave of Object.keys(prezzi)) {
    const trovato = RE_LINEA.exec(chiave);
    if (trovato?.[2]) linee.add(trovato[2]);
  }
  for (const linea of [...linee].sort((a, b) => Number(a) - Number(b))) {
    const over = prezzi[`over_${linea}`];
    const under = prezzi[`under_${linea}`];
    if (typeof over !== 'number' || typeof under !== 'number') continue;
    const m = mercato(
      'Gol totali',
      linea,
      [
        { esito: 'Over', decimale: over },
        { esito: 'Under', decimale: under },
      ],
      operatori,
      1,
    );
    if (m) fuori.push(m);
  }

  return fuori;
}

/**
 * I mercati delle due fonti in una lista sola, senza doppioni.
 *
 * LE DUE SI SOVRAPPONGONO: entrambe quotano i gol totali sopra e sotto 2,5.
 * Concatenandole, la tavola mostrava quella linea due volte — 1,91 e 1,94 —
 * e due prezzi diversi per la stessa scommessa, uno sotto l'altro, sembrano un
 * errore anche quando sono tutti e due veri.
 *
 * A parità di mercato e linea vince la PRINCIPALE: è quella su cui il progetto
 * si è fatto misurare, e la sua mediana poggia su ventiquattro operatori contro
 * i tre che la secondaria mostra ai nostri runner.
 */
export function uniscoMercati(
  principali: MercatoEsteso[],
  secondari: MercatoEsteso[],
): MercatoEsteso[] {
  const chiave = (m: MercatoEsteso) => `${m.mercato}/${m.linea ?? ''}`;
  const visti = new Set(principali.map(chiave));
  return [...principali, ...secondari.filter((m) => !visti.has(chiave(m)))];
}
