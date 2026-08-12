/**
 * Famiglie di mercato e probabilità grezze.
 *
 * Le etichette dei mercati arrivano già in italiano dal backend (`label`) e
 * NON si traducono né si abbelliscono: sono nomi standard che il pubblico ha
 * già imparato altrove (competitors.md 4). Qui si dà solo un nome alle
 * famiglie, che nel file sono chiavi tecniche.
 */
import type { Fixture, Mercato, ProbabilitaGrezze } from './tipi';

const NOMI_FAMIGLIA: Record<string, string> = {
  '1x2': 'Esito finale',
  double_chance: 'Doppia chance',
  over_under: 'Over / Under',
  team_goals: 'Gol di squadra',
  handicap_eu: 'Handicap',
  multigoal: 'Multigol',
  btts: 'Goal / NoGoal',
  combo: 'Combo esito + Over/Under',
  combo_dc: 'Combo doppia chance + Over/Under',
  combo_gol: 'Combo esito + Goal/NoGoal',
  combo_dc_gol: 'Combo doppia chance + Goal/NoGoal',
  combo_gol_ou: 'Combo Goal/NoGoal + Over/Under',
  correct_score: 'Risultato esatto',
  /* Tolto dal catalogo il 12 agosto 2026. Il nome resta perche' resta nelle
     partite di quel giorno e prima, che sono gia' state giudicate e non si
     riscrivono: senza questa riga comparirebbero come «handicap asian». */
  handicap_asian: 'Handicap asiatico',
};

export function nomeFamiglia(chiave: string): string {
  return NOMI_FAMIGLIA[chiave] ?? chiave.replace(/_/g, ' ');
}

/** I mercati alternativi raggruppati per famiglia, in ordine di probabilità. */
export function famiglieAlternative(fixture: Fixture): { famiglia: string; mercati: Mercato[] }[] {
  const runnersUp = fixture.prediction?.runners_up ?? [];
  if (runnersUp.length === 0) return [];

  const gruppi = new Map<string, Mercato[]>();
  for (const mercato of runnersUp) {
    const esistente = gruppi.get(mercato.family);
    if (esistente) esistente.push(mercato);
    else gruppi.set(mercato.family, [mercato]);
  }

  return [...gruppi.entries()]
    .map(([famiglia, mercati]) => ({
      famiglia,
      mercati: [...mercati].sort((a, b) => b.p - a.p),
    }))
    .sort((a, b) => nomeFamiglia(a.famiglia).localeCompare(nomeFamiglia(b.famiglia), 'it'));
}

/**
 * Le probabilità grezze, nell'ordine in cui si leggono.
 * Si mostrano come numeri nudi, senza barra: la barra è il linguaggio del
 * "questo lo consigliamo", e darla a numeri che non consigliamo inviterebbe
 * l'occhio a rifare l'argmax che abbiamo tolto di mezzo apposta (MASTER 5.2).
 */
const ORDINE_GREZZE: { chiave: keyof ProbabilitaGrezze; etichetta: string }[] = [
  { chiave: '1x2_home', etichetta: '1' },
  { chiave: '1x2_draw', etichetta: 'X' },
  { chiave: '1x2_away', etichetta: '2' },
  { chiave: 'over_2.5', etichetta: 'Over 2.5' },
  { chiave: 'under_2.5', etichetta: 'Under 2.5' },
  { chiave: 'btts_yes', etichetta: 'Entrambe segnano' },
];

export function grezzeInOrdine(grezze: ProbabilitaGrezze): { etichetta: string; p: number }[] {
  const fuori: { etichetta: string; p: number }[] = [];
  for (const { chiave, etichetta } of ORDINE_GREZZE) {
    const p = grezze[chiave];
    if (typeof p === 'number') fuori.push({ etichetta, p });
  }
  return fuori;
}
