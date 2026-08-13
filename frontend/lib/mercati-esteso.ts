/**
 * I NOMI DEI MERCATI DELLA FONTE ESTERNA, IN ITALIANO.
 *
 * Arrivano in inglese — «Both teams to score», «Draw no bet» — e il sito e' in
 * italiano. Ma la ragione vera per cui questo file esiste non e' la lingua: e'
 * che `check-parole-vietate` blocca `score`, e ha ragione a bloccarla. Un nome
 * inglese che passa in pagina perche' viene da una risposta JSON e' esattamente
 * il modo in cui il vocabolario di un prodotto si sfalda.
 *
 * REGOLA DURA: quello che non sappiamo tradurre NON SI MOSTRA. Non si mostra
 * l'originale «per non perdere il dato», perche' un mercato che nessuno ha
 * guardato puo' contenere qualunque cosa. Chi chiama conta gli scartati e lo
 * dice in pagina.
 *
 * Se la fonte aggiunge un mercato, qui non compare e il conteggio degli
 * scartati sale: e' un guasto rumoroso, che e' quello che vogliamo.
 */

/** I dieci mercati che la fonte serve davvero, verificati sui dati. */
const NOMI: Record<string, string> = {
  'Full time': 'Esito finale',
  'Double chance': 'Doppia chance',
  '1st half': 'Primo tempo',
  'Draw no bet': 'Pareggio rimborsato',
  'Both teams to score': 'Entrambe le squadre segnano',
  'Asian handicap': 'Handicap asiatico',
  'Match goals': 'Gol totali',
  'First team to score': 'Prima squadra a segnare',
  'Corners 2-Way': 'Calci d’angolo',
  'Cards in match': 'Cartellini nella partita',
};

/** Gli esiti dentro i mercati. Le sigle 1, X, 2 restano come sono. */
const ESITI: Record<string, string> = {
  Yes: 'Sì',
  No: 'No',
  Draw: 'Pareggio',
  Home: 'Casa',
  Away: 'Ospiti',
  '1': '1',
  X: 'X',
  '2': '2',
  '1X': '1X',
  '12': '12',
  X2: 'X2',
};

/**
 * Le stesse forme che vieta `scripts/check-parole-vietate.mjs`.
 *
 * Duplicare una lista e' un debito, e lo si accetta qui per una ragione
 * precisa: quello script gira DOPO il build, sull'HTML prodotto, e dice solo
 * «non passa». Questo controllo gira PRIMA, sul singolo pezzo di testo, e
 * permette di scartare la riga colpevole invece di far fallire tutto il sito.
 * Sono due strumenti diversi con lo stesso vocabolario.
 */
const VIETATE = [/\bvalue bet\b/i, /\bedge\b/i, /\bROI\b/, /\bstake\b/i, /\bscore\b/i, /\bsigma\b/i];

function pulito(testo: string): boolean {
  return !VIETATE.some((r) => r.test(testo));
}

/** Il nome italiano, o `null` se non lo conosciamo. */
export function nomeMercato(originale: string): string | null {
  const tradotto = NOMI[originale.trim()];
  if (!tradotto) return null;
  return pulito(tradotto) ? tradotto : null;
}

/** L'esito in italiano, o `null` se non e' mostrabile. */
export function nomeEsito(originale: string): string | null {
  const grezzo = originale.trim();
  const tradotto = ESITI[grezzo] ?? grezzo;
  // Gli esiti numerici di over/under e handicap ("Over 2.5", "+1.5") passano:
  // sono notazione, non lingua.
  if (!pulito(tradotto)) return null;
  return tradotto;
}

/**
 * Una probabilita' detta come la dice il resto del sito: «N su 100».
 *
 * Mai in percentuale. La regola sta in `check-parole-vietate.mjs` e non e'
 * uno stile: una percentuale in pagina, su questo sito, e' quasi sempre una
 * grandezza interna sfuggita, e vietarla del tutto rende il guasto visibile.
 */
export function suCento(p: number): string {
  return `${Math.round(p * 100)} su 100`;
}
