/**
 * Formattazione. Una sola lingua: italiano.
 *
 * Regole del prodotto applicate qui, una volta sola:
 *  - le probabilità si dicono "72 su 100", mai "72%", mai "confidenza"
 *  - le date sono in formato lungo italiano, mai 22/08/2026
 *  - i decimali usano la virgola
 */

const FUSO = 'Europe/Rome';

const GIORNI = ['domenica', 'lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato'];
const GIORNI_BREVI = ['DOM', 'LUN', 'MAR', 'MER', 'GIO', 'VEN', 'SAB'];
const MESI = [
  'gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno',
  'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre',
];

/** Una data `YYYY-MM-DD` come oggetto, a mezzogiorno UTC: nessun scivolamento di fuso. */
function daIso(data: string): Date {
  return new Date(`${data}T12:00:00Z`);
}

/** "sabato 22 agosto" */
export function dataLunga(data: string): string {
  const d = daIso(data);
  return `${GIORNI[d.getUTCDay()]} ${d.getUTCDate()} ${MESI[d.getUTCMonth()]}`;
}

/** "Sabato 22 agosto" — iniziale maiuscola, il resto minuscolo. */
export function dataLungaMaiuscola(data: string): string {
  const s = dataLunga(data);
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * `{ sigla: 'SAB', numero: '22' }` — le due righe di una voce della striscia
 * dei giorni. Mono maiuscolo su due livelli: la sigla si legge di sfuggita,
 * il numero è l'ancora.
 */
export function pezziGiorno(data: string): { sigla: string; numero: string } {
  const d = daIso(data);
  return { sigla: GIORNI_BREVI[d.getUTCDay()] ?? '', numero: String(d.getUTCDate()) };
}

/** "22 agosto 2026" — per le ricevute e i timestamp. */
export function dataConAnno(data: string): string {
  const d = daIso(data);
  return `${d.getUTCDate()} ${MESI[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** Da un istante ISO completo alla data lunga con anno: "8 agosto 2026". */
export function istanteInData(iso: string): string {
  return dataConAnno(iso.slice(0, 10));
}

/**
 * "l'8 agosto" / "il 22 agosto" — l'articolo elide davanti a 8 e 11.
 */
export function conArticolo(iso: string): string {
  const giorno = Number(iso.slice(8, 10));
  const testo = istanteInData(iso);
  return giorno === 8 || giorno === 11 ? `l'${testo}` : `il ${testo}`;
}

/**
 * "all'8 agosto" / "al 22 agosto" — la preposizione articolata.
 *
 * Le transizioni dicono «Fino AL ... dicevamo», non «fino IL». Con
 * `conArticolo` uscivano frasi come «Fino l'8 agosto 2026 dicevamo Casa Over
 * 1.5»: un errore di grammatica italiana proprio nel blocco che esiste per
 * guadagnare fiducia, cioe' dove costa di piu'. Il commento della funzione
 * precedente scriveva la forma giusta; era il codice a non averla.
 */
export function conPreposizione(iso: string): string {
  const giorno = Number(iso.slice(8, 10));
  const testo = istanteInData(iso);
  return giorno === 8 || giorno === 11 ? `all'${testo}` : `al ${testo}`;
}

/** "20:45" nel fuso italiano. */
export function ora(iso: string): string {
  return new Intl.DateTimeFormat('it-IT', {
    timeZone: FUSO,
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso));
}

/** Il valore di `datetime` per `<time>`: l'istante ISO così com'è. */
export function attributoOra(iso: string): string {
  return iso;
}

/** 0.7169 → 72. La sola forma in cui una probabilità entra in pagina. */
export function suCento(p: number): number {
  return Math.round(p * 100);
}

/** 0.079 → "0,079". Virgola decimale, cifre fisse. */
export function decimale(n: number, cifre = 2): string {
  return n.toLocaleString('it-IT', { minimumFractionDigits: cifre, maximumFractionDigits: cifre });
}

/** 1234 → "1.234" */
export function intero(n: number): string {
  return n.toLocaleString('it-IT');
}

/**
 * I testi generati dal backend arrivano con gli apostrofi ASCII al posto degli
 * accenti ("e'", "gia'", "piu'"). Sono frasi già pronte da mostrare
 * (schema.md: `reasons` è italiano pronto), quindi la correzione è tipografica
 * e sta qui, nello strato di presentazione — non riscrive il contenuto.
 * Da togliere quando il backend emette gli accenti corretti alla fonte.
 */
const ACCENTI: [RegExp, string][] = [
  [/\be'(?![\p{L}'])/gu, 'è'],
  [/\bE'(?![\p{L}'])/gu, 'È'],
  [/\bgia'(?![\p{L}'])/gu, 'già'],
  [/\bpiu'(?![\p{L}'])/gu, 'più'],
  [/\bperche'(?![\p{L}'])/gu, 'perché'],
  [/\bpoiche'(?![\p{L}'])/gu, 'poiché'],
  [/\bcosi'(?![\p{L}'])/gu, 'così'],
  [/\bpuo'(?![\p{L}'])/gu, 'può'],
  [/\bpero'(?![\p{L}'])/gu, 'però'],
  [/\bgiu'(?![\p{L}'])/gu, 'giù'],
];

export function testoPulito(testo: string): string {
  let fuori = testo;
  for (const [cerca, sostituisci] of ACCENTI) fuori = fuori.replace(cerca, sostituisci);
  return fuori;
}
