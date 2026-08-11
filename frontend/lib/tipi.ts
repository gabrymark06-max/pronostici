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
  /** `it` = operatori con licenza ADM, `eu` = mediana europea di ripiego. */
  price_scope?: string;
  price_books?: number;
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
