/**
 * I campionati come STRUTTURA, non come etichetta.
 *
 * Nella v2 le partite erano raggruppate per competizione ma ordinate per
 * primo calcio d'inizio, quindi l'ordine dei campionati cambiava ogni giorno:
 * un lettore non poteva imparare dove sta il suo. Qui l'ordine e' DICHIARATO
 * e stabile, e ogni campionato porta il proprio paese — che e' cio' che lo
 * rende riconoscibile prima di leggerne il nome.
 *
 * L'ordine e' quello di un lettore italiano: la Serie A per prima, poi la
 * coppa, poi gli altri campionati maggiori, poi i minori.
 */
import { NOMI_COMPETIZIONE } from './testi';

export const ORDINE_COMPETIZIONI: readonly string[] = [
  'SA', // Serie A
  'CL', // Champions League
  'PL', // Premier League
  'PD', // La Liga
  'BL1', // Bundesliga
  'FL1', // Ligue 1
  'DED', // Eredivisie
  'PPL', // Primeira Liga
  'ELC', // Championship
  'BSA', // Brasileirão
  'EC', // Europei
  'WC', // Mondiali
];

/** La posizione nell'ordine dichiarato. Gli sconosciuti finiscono in fondo. */
export function rangoCompetizione(codice: string): number {
  const i = ORDINE_COMPETIZIONI.indexOf(codice);
  return i === -1 ? ORDINE_COMPETIZIONI.length : i;
}

/**
 * Il paese del campionato, per la bandiera e per il sottotitolo.
 * `null` per le competizioni che non appartengono a un paese solo.
 */
export const PAESE_COMPETIZIONE: Record<string, string | null> = {
  SA: 'Italia',
  PL: 'Inghilterra',
  ELC: 'Inghilterra',
  PD: 'Spagna',
  BL1: 'Germania',
  FL1: 'Francia',
  DED: 'Paesi Bassi',
  PPL: 'Portogallo',
  BSA: 'Brasile',
  CL: null,
  EC: null,
  WC: null,
};

export function paeseDi(codice: string): string | null {
  return PAESE_COMPETIZIONE[codice] ?? null;
}

export function nomeCampionato(codice: string): string {
  return NOMI_COMPETIZIONE[codice] ?? codice;
}

/**
 * LA FASE DEL TORNEO, quando la competizione ne ha una.
 *
 * Serve a non chiamare «Champions League» una Supercoppa. La Supercoppa entra
 * sotto `CL` per una ragione tecnica — è lì che vivono i parametri di attacco e
 * difesa delle due squadre, stimati sulle loro partite europee — ma il lettore
 * non deve pagare per una scelta di modellazione: vede il nome della partita
 * che sta guardando.
 *
 * Le chiavi sono quelle di football-data, più `SUPER_CUP` che è nostra (loro
 * non espongono la Supercoppa affatto).
 */
const NOMI_FASE: Record<string, string> = {
  SUPER_CUP: 'Supercoppa UEFA',
  FINAL: 'Finale',
  SEMI_FINALS: 'Semifinali',
  QUARTER_FINALS: 'Quarti di finale',
  LAST_16: 'Ottavi di finale',
  PLAYOFFS: 'Play-off',
  PLAY_OFFS: 'Play-off',
  LEAGUE_STAGE: null as unknown as string,
  GROUP_STAGE: null as unknown as string,
  REGULAR_SEASON: null as unknown as string,
};

/**
 * Come si chiama questa partita: la fase se ne ha una che valga la pena
 * nominare, altrimenti il campionato. La fase «girone» non si mostra perché
 * dire «Champions League · Fase campionato» aggiunge parole e non informazione.
 */
export function titoloCompetizione(codice: string, fase?: string | null): string {
  const nome = fase ? NOMI_FASE[fase] : undefined;
  return nome || nomeCampionato(codice);
}
