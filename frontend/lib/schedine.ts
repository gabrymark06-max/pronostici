/**
 * LE DUE SCHEDINE DEL GIORNO — il raddoppio e la multipla.
 *
 * Un solo fatto governa tutto questo file, e conviene averlo chiaro prima di
 * leggere una riga di codice:
 *
 *   LA NOSTRA QUOTA E' 1 DIVISO LA PROBABILITA'.
 *
 * Quindi la quota di una schedina — il prodotto delle quote — e' 1 diviso il
 * prodotto delle probabilita'. Le due grandezze sono la stessa cosa scritta al
 * contrario: **una multipla a quota 5,00 vale 20 su 100 comunque la componi**,
 * con due partite rischiose o con dieci sicure. Non esiste una combinazione
 * furba che porti a 5,00 con piu' probabilita' di un'altra.
 *
 * Questo cancella l'unica cosa che i siti di schedine vendono — «la nostra
 * selezione arriva a quota 5 con l'85 per cento di riuscita» — e lascia in
 * piedi una sola domanda vera: CON QUANTE PARTITE ci arrivi. Meno gambe
 * significa meno errore di modello accumulato e meno cose che possono andare
 * storte in modi che il modello non vede. Quindi:
 *
 *   * IL RADDOPPIO: due partite, e fra tutte le coppie quella con la
 *     probabilita' piu' alta che arriva comunque a 2,00.
 *   * LA MULTIPLA: il MINOR numero di partite che arriva a 5,00, e fra le
 *     composizioni di quella lunghezza la piu' probabile.
 *
 * Entrambe le regole sono la stessa: «il prodotto piu' vicino al bersaglio
 * restando sotto». Sotto e non sopra, perche' il bersaglio e' un minimo di
 * quota: arrivarci da sopra vorrebbe dire una quota piu' bassa di quella
 * chiesta.
 *
 * L'INDIPENDENZA E' UN'IPOTESI, e va detta. Moltiplicare le probabilita' vale
 * se le partite sono indipendenti. Fra partite DIVERSE e' difendibile — non
 * perfetto: stessa giornata, stesso campionato, stesso meteo — e qui e'
 * garantito che siano diverse perche' il catalogo produce un pronostico per
 * partita e la lista non ne contiene due della stessa. Fra due mercati della
 * STESSA partita non varrebbe per niente, ed e' il motivo per cui non se ne
 * mettono mai due.
 */
import { quoteDi } from './quote';
import { tace, type Fixture, type FixtureConPronostico, type Pronostico } from './tipi';
import { contornoDi } from './contorno';

/** Il minimo di quota che ognuna delle due schedine deve raggiungere. */
export const QUOTA_RADDOPPIO = 2;
export const QUOTA_MULTIPLA = 5;

/** Oltre questo non e' piu' una schedina, e' un elenco. Vedi `componi()`. */
const GAMBE_MASSIME = 8;

export interface Gamba {
  fixture: FixtureConPronostico;
  pronostico: Pronostico;
  /**
   * IL PREZZO TROVATO su questa singola partita, o `null`.
   *
   * Era `1/probabilita' nostra`, che e' un numero nostro: una gamba non
   * «vale» quella quota, nessuno la paga. Qui c'e' il prezzo vero quando una
   * delle due fonti quota quel mercato, e niente quando non lo quota nessuno.
   */
  prezzo: number | null;
  /** `null` finche' la partita non e' conclusa. */
  uscito: boolean | null;
}

export type EsitoSchedina = 'in-corso' | 'uscita' | 'non-uscita';

export interface Schedina {
  tipo: 'raddoppio' | 'multipla';
  gambe: Gamba[];
  /** Il prodotto delle probabilita'. E' esattamente `1 / quota`. */
  p: number;
  /**
   * IL PREZZO DELLA MULTIPLA: il prodotto dei prezzi veri, e `null` se anche
   * UNA sola gamba non ne ha uno.
   *
   * Un prodotto parziale non e' una quota piu' bassa: e' un numero che non
   * corrisponde a nessuna giocata.
   */
  prezzo: number | null;
  /**
   * La probabilita' MASSIMA che questa schedina doveva rispettare.
   *
   * Era espressa come quota minima — 2 per il raddoppio, 5 per la multipla —
   * e finiva in pagina come «non arriva a 5,00». Ma quel 5 non e' un prezzo
   * che qualcuno espone: e' una soglia nostra, e nella pagina di un sito che
   * non stampa piu' quote calcolate leggerla come una quota confonde. Le due
   * scritture sono la stessa cosa: quota 5 e' 20 su 100.
   */
  bersaglioP: number;
  /** `false` quando le partite del giorno non bastavano ad arrivarci. */
  bersaglioRaggiunto: boolean;
  esito: EsitoSchedina;
  /** Quante gambe sono gia' concluse. Serve a dire «3 su 5» mentre si gioca. */
  concluse: number;
}

/* ------------------------------------------------------------------ */
/* Le gambe candidate                                                 */
/* ------------------------------------------------------------------ */

/**
 * Le partite del giorno su cui ci siamo esposti, in ordine di probabilita'.
 *
 * Il silenzio non e' una gamba: dove non abbiamo un pronostico non abbiamo
 * niente da mettere in una schedina, e riempire con il secondo miglior mercato
 * di una partita su cui abbiamo taciuto sarebbe rimangiarsi il silenzio nel
 * posto piu' visibile del sito.
 *
 * L'ordine finale usa `match_id` a parita' di probabilita': senza, due build
 * dello stesso giorno potrebbero produrre due schedine diverse, e una schedina
 * che cambia da sola non e' un pronostico datato.
 */
export function gambeCandidate(fixtures: Fixture[]): Gamba[] {
  const fuori: Gamba[] = [];
  for (const fixture of fixtures) {
    if (tace(fixture)) continue;
    const pronostico = fixture.prediction;
    if (!(pronostico.p > 0 && pronostico.p < 1)) continue;
    const q = quoteDi(pronostico, fixture.odds, contornoDi(fixture));
    fuori.push({
      fixture,
      pronostico,
      prezzo: q.prezzo,
      uscito: fixture.outcome === null || fixture.outcome === undefined ? null : fixture.outcome === 1,
    });
  }
  return fuori.sort((a, b) => b.pronostico.p - a.pronostico.p || a.fixture.match_id - b.fixture.match_id);
}

/* ------------------------------------------------------------------ */
/* La composizione                                                    */
/* ------------------------------------------------------------------ */

function prodotto(gambe: Gamba[]): number {
  return gambe.reduce((acc, g) => acc * g.pronostico.p, 1);
}

/**
 * La coppia con la probabilita' piu' alta fra quelle che arrivano al bersaglio.
 *
 * Forza bruta su tutte le coppie: con quaranta partite in un giorno sono
 * ottocento confronti, e un'euristica qui non farebbe risparmiare niente di
 * misurabile mentre renderebbe la regola piu' difficile da spiegare in pagina.
 */
function coppiaMigliore(cands: Gamba[], massimo: number): Gamba[] | null {
  let scelta: Gamba[] | null = null;
  let miglior = -1;
  for (let i = 0; i < cands.length; i += 1) {
    for (let j = i + 1; j < cands.length; j += 1) {
      const a = cands[i];
      const b = cands[j];
      if (!a || !b) continue;
      const p = a.pronostico.p * b.pronostico.p;
      if (p <= massimo && p > miglior) {
        miglior = p;
        scelta = [a, b];
      }
    }
  }
  return scelta;
}

/**
 * Il minor numero di partite che sta sotto `massimo`, e fra quelle la piu'
 * probabile.
 *
 * DUE PASSI. Il primo trova la LUNGHEZZA: le gambe meno probabili sono quelle
 * che fanno scendere il prodotto piu' in fretta, quindi se `k` di quelle non
 * bastano non basta nessun'altra scelta di `k`. Il secondo alza la
 * probabilita' a lunghezza fissa, scambiando una gamba alla volta con la
 * migliore sostituta che tenga il prodotto sotto il bersaglio, finche' non
 * c'e' piu' nessuno scambio che migliori.
 *
 * Lo scambio migliore ad ogni giro rende il risultato indipendente
 * dall'ordine in cui si prova, che e' quello che serve per avere due build
 * identiche sullo stesso giorno.
 */
function insiemeMigliore(cands: Gamba[], massimo: number, tetto: number): Gamba[] | null {
  const perRischio = [...cands].sort(
    (a, b) => a.pronostico.p - b.pronostico.p || a.fixture.match_id - b.fixture.match_id,
  );

  /* Si parte da TRE, non da due: con due sarebbe un raddoppio, e le due
     schedine del giorno finirebbero per essere la stessa cosa scritta due
     volte ogni volta che una coppia arriva gia' a 5,00. */
  let scelta: Gamba[] | null = null;
  for (let k = 3; k <= Math.min(tetto, perRischio.length); k += 1) {
    const tentativo = perRischio.slice(0, k);
    if (prodotto(tentativo) <= massimo) {
      scelta = tentativo;
      break;
    }
  }
  if (!scelta) return null;

  const dentro = new Set(scelta.map((g) => g.fixture.match_id));
  const fuori = cands.filter((g) => !dentro.has(g.fixture.match_id));

  for (;;) {
    let miglioreP = prodotto(scelta);
    let scambio: { esce: number; entra: Gamba } | null = null;
    for (let i = 0; i < scelta.length; i += 1) {
      for (const entra of fuori) {
        const provvisorio = scelta.map((g, idx) => (idx === i ? entra : g));
        const p = prodotto(provvisorio);
        if (p <= massimo && p > miglioreP) {
          miglioreP = p;
          scambio = { esce: i, entra };
        }
      }
    }
    if (!scambio) break;
    const { esce, entra } = scambio;
    const uscita = scelta[esce];
    if (!uscita) break;
    scelta = scelta.map((g, idx) => (idx === esce ? entra : g));
    fuori.splice(fuori.indexOf(entra), 1, uscita);
  }

  return scelta;
}

function assembla(
  tipo: Schedina['tipo'],
  gambe: Gamba[],
  bersaglio: number,
  raggiunto: boolean,
): Schedina {
  const ordinate = [...gambe].sort(
    (a, b) => a.fixture.utc_date.localeCompare(b.fixture.utc_date) || a.fixture.match_id - b.fixture.match_id,
  );
  const p = prodotto(ordinate);

  /* Il prezzo solo se OGNI gamba ne ha uno. Vedi il commento sul campo. */
  const tutteQuotate = ordinate.every((g) => g.prezzo !== null);
  const prezzo = tutteQuotate
    ? ordinate.reduce((acc, g) => acc * (g.prezzo ?? 1), 1)
    : null;

  const concluse = ordinate.filter((g) => g.uscito !== null).length;
  const esito: EsitoSchedina = ordinate.some((g) => g.uscito === false)
    ? 'non-uscita'
    : concluse === ordinate.length && ordinate.length > 0
      ? 'uscita'
      : 'in-corso';

  return {
    tipo,
    gambe: ordinate,
    p,
    prezzo,
    bersaglioP: bersaglio,
    bersaglioRaggiunto: raggiunto,
    esito,
    concluse,
  };
}

export interface SchedineDelGiorno {
  raddoppio: Schedina | null;
  multipla: Schedina | null;
  /** Su quante partite si e' scelto. Va detto: due schedine su tre partite
   *  sono un'altra cosa rispetto a due su quaranta. */
  candidate: number;
}

export function schedineDelGiorno(fixtures: Fixture[]): SchedineDelGiorno {
  const cands = gambeCandidate(fixtures);
  if (cands.length < 2) return { raddoppio: null, multipla: null, candidate: cands.length };

  /* Il bersaglio e' una quota MINIMA, quindi un prodotto MASSIMO. */
  const coppia =
    coppiaMigliore(cands, 1 / QUOTA_RADDOPPIO) ??
    /* Nessuna coppia arriva a 2,00: tutte le partite del giorno sono molto
       probabili. Si prende quella con la quota piu' alta e lo si dichiara,
       invece di non mostrare niente. */
    (() => {
      const perRischio = [...cands].sort(
        (a, b) => a.pronostico.p - b.pronostico.p || a.fixture.match_id - b.fixture.match_id,
      );
      const due = perRischio.slice(0, 2);
      return due.length === 2 ? due : null;
    })();
  const coppiaRaggiunge = coppia !== null && prodotto(coppia) <= 1 / QUOTA_RADDOPPIO;

  const molte =
    insiemeMigliore(cands, 1 / QUOTA_MULTIPLA, GAMBE_MASSIME) ??
    (() => {
      /* Nemmeno otto gambe arrivano a 5,00. Si mostrano le otto piu' rischiose,
         che sono la quota piu' alta ottenibile con quel tetto, e la pagina dice
         che il bersaglio non e' stato raggiunto. */
      const perRischio = [...cands].sort(
        (a, b) => a.pronostico.p - b.pronostico.p || a.fixture.match_id - b.fixture.match_id,
      );
      const prese = perRischio.slice(0, Math.min(GAMBE_MASSIME, perRischio.length));
      return prese.length >= 3 ? prese : null;
    })();
  const molteRaggiunge = molte !== null && prodotto(molte) <= 1 / QUOTA_MULTIPLA;

  return {
    raddoppio: coppia ? assembla('raddoppio', coppia, 1 / QUOTA_RADDOPPIO, coppiaRaggiunge) : null,
    multipla: molte ? assembla('multipla', molte, 1 / QUOTA_MULTIPLA, molteRaggiunge) : null,
    candidate: cands.length,
  };
}
