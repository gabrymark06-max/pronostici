/**
 * I tipi del contratto `docs/schema.md`, schema_version 1.
 *
 * Regola portante dello schema: `prediction` e `silence` sono MUTUAMENTE
 * ESCLUSIVI. Il silenzio non è un ramo `else`: è un tipo di prima classe, e
 * qui è modellato come tale (unione discriminata `Fixture`), così il
 * compilatore impedisce di scrivere un componente che li confonde.
 */

export const SCHEMA_VERSION_ATTESA = 1;

export type CodiceCompetizione =
  | 'PL' | 'SA' | 'PD' | 'BL1' | 'FL1' | 'DED'
  | 'PPL' | 'ELC' | 'BSA' | 'CL' | 'WC' | 'EC';

export type Fase = 'preliminary' | 'definitive';
export type Provenienza = 'model_only' | 'blended_with_odds';
export type MotivoSilenzio = 'S_min' | 'sigma_max' | 'p_min' | 'no_candidates';

export type Transizione =
  | 'first'
  | 'confirmed'
  | 'changed'
  | 'prediction_to_silence'
  | 'silence_to_prediction'
  | 'still_silent';

export interface Squadra {
  name: string;
  tla: string;
  crest: string | null;
}

/** Un mercato candidato. Anche i `runners_up` hanno questa forma. */
export interface Mercato {
  key: string;
  family: string;
  label: string;
  /** Probabilità DOPO shrinkage. L'unica mostrabile. */
  p: number;
  band_p5: number | null;
  band_p95: number | null;
  /* Campi di diagnostica presenti nel file e MAI mostrati:
     p_raw, sigma, shrink_alpha, reference, score. Non sono dichiarati qui
     apposta: quello che non esiste nel tipo non può finire in una pagina. */
}

export interface Pronostico extends Mercato {
  cluster_members?: string[];
  runners_up?: Mercato[];
}

export interface Diagnostica {
  n_candidates: number;
  n_clusters: number;
  filter_bites: Partial<Record<'S_min' | 'p_min' | 'sigma_max', number>>;
  truncated_mass: number;
}

export interface ProbabilitaGrezze {
  '1x2_home'?: number;
  '1x2_draw'?: number;
  '1x2_away'?: number;
  'over_2.5'?: number;
  'under_2.5'?: number;
  btts_yes?: number;
  [chiave: string]: number | undefined;
}

export interface Precedente {
  phase: Fase;
  written_at: string;
  market_key: string | null;
  market_label: string | null;
  p: number | null;
  silence_reason: MotivoSilenzio | null;
}

export interface Quote {
  devig?: Record<string, number>;
  markets?: string[];
  n_bookmakers?: number;
  fetched?: string;
  /**
   * Le quote decimali DA MOSTRARE, chiave nostra → prezzo lordo.
   *
   * Sono un'altra cosa rispetto alle probabilità sgonfiate che usa il modello:
   * qui il margine dell'operatore c'è ancora, perché è il prezzo che l'utente
   * troverebbe davvero allo sportello. Sgonfiarlo darebbe un numero che
   * nessuno può giocare, e confrontarlo con la nostra quota equa non
   * significherebbe più niente.
   *
   * Copertura reale: solo 1X2 e Over/Under, e solo sulle partite per cui il
   * budget delle quote ha permesso una chiamata. Sulla maggior parte dei
   * pronostici questo campo è assente, ed è previsto che lo sia.
   */
  prices?: Record<string, number>;
  /**
   * Le probabilità di mercato SGONFIATE, per ogni mercato che le quote
   * determinano in modo esatto.
   *
   * Sono undici chiavi a partire da cinque quote: le tre doppie chance sono
   * somme di esiti 1X2, l'handicap europeo ±1 e il multigol 0-2 hanno la
   * stessa maschera di un mercato già coperto. Nessuna approssimazione: è la
   * stessa estensione che usa il modello per scegliere.
   *
   * Serve perché il pronostico consigliato quasi mai È un 1X2 — su 21 partite
   * quotate, zero. Con la sola tabella dei prezzi la colonna «mercato» restava
   * vuota anche dove il mercato aveva parlato chiarissimo.
   */
  market_p?: Record<string, number>;
  /** `it` = operatori con licenza ADM, `eu` = mediana europea di ripiego. */
  price_scope?: string;
  price_books?: number;
}

/* ------------------------------------------------------------------ */
/* Il blocco `sofascore`: arbitro, formazioni, quote estese, giocatori. */
/*                                                                      */
/* Tutto qui dentro e' CONTORNO, mai il pronostico. Il tipo lo dice     */
/* rendendolo un campo a se': niente in `Sofascore` puo' finire dentro  */
/* `Pronostico`, e il compilatore lo impedisce.                         */
/* ------------------------------------------------------------------ */

export interface Arbitro {
  nome: string;
  paese?: string | null;
  partite?: number | null;
  gialli?: number | null;
  rossi?: number | null;
  gialli_per_partita?: number | null;
}

export interface GiocatoreInCampo {
  id?: number;
  nome: string;
  maglia?: string;
  ruolo?: string;
  titolare?: boolean;
}

export interface LatoFormazione {
  modulo?: string | null;
  titolari: GiocatoreInCampo[];
  panchina: GiocatoreInCampo[];
}

export interface Formazioni {
  confermate: boolean;
  /** Quante ore prima del fischio sono state lette. Distingue una previsione
   *  a tre giorni da una probabile di un'ora prima: stesso campo `confermate`,
   *  affidabilita' molto diversa. */
  ore_prima?: number | null;
  casa: LatoFormazione;
  ospiti: LatoFormazione;
}

export interface EsitoEsteso {
  esito: string;
  frazionaria?: string;
  decimale?: number;
  probabilita_implicita?: number;
}

export interface MercatoEsteso {
  mercato: string;
  esiti: EsitoEsteso[];
  somma_probabilita?: number;
  margine_percento?: number;
}

export interface StimaGiocatore {
  mercato: string;
  etichetta: string;
  p: number;
  /** Da quale tasso viene, in chiaro. Serve a rendere il numero verificabile. */
  base: string;
}

export interface GiocatoreStimato {
  id: number;
  nome: string;
  ruolo?: string | null;
  presenze?: number | null;
  torneo?: string | null;
  stime: StimaGiocatore[];
}

export interface StimeGiocatori {
  /** Sempre `false` oggi. Esiste perche' il giorno in cui diventasse `true`
   *  la pagina cambi da sola invece di restare a mentire. */
  misurato: boolean;
  nota: string;
  moltiplicatore_arbitro?: number;
  minuti_attesi_titolare?: number;
  casa: GiocatoreStimato[];
  ospiti: GiocatoreStimato[];
}

export interface Sofascore {
  evento_id: number;
  torneo?: string;
  letto?: string;
  stadio?: string;
  arbitro?: Arbitro;
  formazioni?: Formazioni;
  quote?: { n_mercati?: number; mercati: MercatoEsteso[] };
  /**
   * Le stesse quote tradotte nelle NOSTRE chiavi e sgonfiate del margine.
   *
   * Sta qui e non dentro `odds` apposta: le due fonti non si mescolano nello
   * stesso campo, così la pagina può sempre dire da dove viene il numero che
   * mostra. Copre le quattro famiglie che si mappano senza interpretare —
   * esito finale, doppia chance, entrambe segnano, gol totali sopra e sotto
   * 2,5 e 3,5.
   */
  market_p?: Record<string, number>;
  giocatori?: StimeGiocatori;
  parti_mancanti?: Record<string, string>;
}

export interface Risultato {
  home: number;
  away: number;
}

/** I campi comuni a una partita, indipendenti dal fatto che si parli o si taccia. */
interface FixtureBase {
  match_id: number;
  competition: CodiceCompetizione;
  utc_date: string;
  matchday: number | null;
  /** La fase del torneo, quando c'è: `SUPER_CUP`, `FINAL`, `LAST_16`… */
  stage?: string | null;
  home: Squadra;
  away: Squadra;
  phase: Fase;
  source: Provenienza;
  model_weight: number;
  expected_goals: { home: number; away: number };
  reasons: string[];
  raw_probabilities: ProbabilitaGrezze;
  diagnostics: Diagnostica;
  half_time?: Record<string, number>;
  transition?: Transizione | null;
  previous?: Precedente | null;
  odds?: Quote | null;
  sofascore?: Sofascore | null;
  result?: Risultato | null;
  outcome?: 0 | 1 | null;
}

/** Partita con un pronostico. */
export interface FixtureConPronostico extends FixtureBase {
  prediction: Pronostico;
  silence: null;
}

/** Partita su cui si tace. Il silenzio porta sempre il suo motivo. */
export interface FixtureInSilenzio extends FixtureBase {
  prediction: null;
  silence: { reason: MotivoSilenzio };
}

export type Fixture = FixtureConPronostico | FixtureInSilenzio;

/** Restringe l'unione. Da usare al posto di `f.prediction !== null` sparso. */
export function tace(f: Fixture): f is FixtureInSilenzio {
  return f.prediction === null;
}

export interface GiornoFixtures {
  schema_version: number;
  date: string;
  generated_at: string;
  silence_count: number;
  total: number;
  fixtures: Fixture[];
}

/* ------------------------------------------------------------------ */
/* accuracy.json — il registro dal vivo                                */
/* ------------------------------------------------------------------ */

export interface Fascia {
  n: number;
  hits?: number;
  mean_p?: number;
  hit_rate?: number;
  enough?: boolean;
}

export interface Accuracy {
  schema_version: number;
  generated_at: string;
  live: {
    n: number;
    skill_declared_mean?: number;
    skill_realized_mean?: number;
    skill_realized_se?: number;
    calibration_gap?: number;
    hit_rate?: number;
    buckets?: Record<string, Fascia>;
  };
  by_phase: Partial<Record<Fase, { n: number }>>;
  silence: Partial<
    Record<
      Fase,
      { n: number; silent: number; rate: number; by_reason: Partial<Record<MotivoSilenzio, number>> }
    >
  >;
  transitions: Partial<Record<Transizione, number>>;
  progress_to_500: { published: number; target: number };
}

/* ------------------------------------------------------------------ */
/* backtest.json — la prova storica. NON si mescola mai con accuracy.  */
/* ------------------------------------------------------------------ */

export interface Backtest {
  schema_version: number;
  generated_at: string;
  code_commit: string;
  configurations_tried: number;
  protocol: string;
  measures: string;
  not_measured: string;
  seconds: number;
  window: { from: string; to: string };
  parameters: Record<string, number>;
  buckets: Record<string, Fascia>;
  per_competition: Record<
    string,
    { evaluated: number; with_prediction: number; hits: number; hit_rate: number; silence_rate: number }
  >;
  silence: {
    target: number;
    band: [number, number];
    chosen_s_min: number;
    decision: string;
    by_reason: Partial<Record<MotivoSilenzio, number>>;
    curve: { s_min: number; silence_rate: number }[];
  };
  skill: {
    n: number;
    declared_mean: number;
    realized_mean: number;
    realized_se: number;
    gap: number;
    gap_in_se: number;
    hit_rate: number;
    mean_p: number;
  };
  log_loss_over_2_5: { base_rate: number; model: number; model_better: boolean; n: number };
  volume: {
    evaluated: number;
    with_prediction: number;
    refits: number;
    skipped_warmup_or_unknown_team: number;
    silence_rate_at_s_min_in_code: number;
  };
  filter_bites: Record<string, number>;
}
