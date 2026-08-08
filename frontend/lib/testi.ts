/**
 * I testi del prodotto, in un posto solo.
 *
 * Le frasi qui dentro sono specificate parola per parola in
 * design-system/pronostici/MASTER.md (5.3, 6, 7.3) e nelle pagine. Non sono
 * copy libero: sono la parte del design system che vive nel testo. Cambiarle
 * è una modifica al design system, non un ritocco.
 */
import { conArticolo, suCento } from './formato';
import type {
  Fixture,
  FixtureInSilenzio,
  MotivoSilenzio,
  Precedente,
  Pronostico,
  Transizione,
} from './tipi';

/* ------------------------------------------------------------------ */
/* Competizioni — i nomi, da src/pronostici/competitions.py            */
/* ------------------------------------------------------------------ */

export const NOMI_COMPETIZIONE: Record<string, string> = {
  PL: 'Premier League',
  SA: 'Serie A',
  PD: 'La Liga',
  BL1: 'Bundesliga',
  FL1: 'Ligue 1',
  DED: 'Eredivisie',
  PPL: 'Primeira Liga',
  ELC: 'Championship',
  BSA: 'Brasileirão',
  CL: 'Champions League',
  WC: 'Mondiali',
  EC: 'Europei',
};

export function nomeCompetizione(codice: string): string {
  return NOMI_COMPETIZIONE[codice] ?? codice;
}

/* ------------------------------------------------------------------ */
/* Provenienza — il badge, in due stati distinguibili senza colore     */
/* ------------------------------------------------------------------ */

export const TESTO_PROVENIENZA = {
  blended_with_odds: 'confrontato con le quote',
  model_only: 'solo modello statistico',
} as const;

/* ------------------------------------------------------------------ */
/* La banda p5–p95, qualificata a parole (MASTER 2)                    */
/* ------------------------------------------------------------------ */

export type QualificaBanda = 'stretta' | 'media' | 'larga';

export function qualificaBanda(p5: number, p95: number): QualificaBanda {
  const larghezza = p95 - p5;
  if (larghezza <= 0.08) return 'stretta';
  if (larghezza <= 0.16) return 'media';
  return 'larga';
}

export const FRASE_QUALIFICA: Record<QualificaBanda, string> = {
  stretta: 'Stima stretta.',
  media: 'Stima media.',
  larga: 'Stima larga.',
};

/**
 * Le tre righe obbligatorie sotto ogni cifra — l'ELEMENTO FIRMA.
 * L'ordine è vincolante (scheda-partita.md, blocco ②):
 * definizione operativa, banda in parole, qualifica della banda.
 */
export function righeDefinizione(pronostico: Pronostico): string[] {
  const righe = [
    `Su 100 partite come questa, in ${suCento(pronostico.p)} esce «${pronostico.label}».`,
  ];
  if (pronostico.band_p5 !== null && pronostico.band_p95 !== null) {
    righe.push(
      `Fra ${suCento(pronostico.band_p5)} e ${suCento(pronostico.band_p95)} su 100 nelle nostre simulazioni.`,
    );
    righe.push(FRASE_QUALIFICA[qualificaBanda(pronostico.band_p5, pronostico.band_p95)]);
  }
  return righe;
}

/** L'etichetta accessibile del gruppo barra+banda (MASTER 7.1). */
export function etichettaBarra(pronostico: Pronostico): string {
  const base = `${suCento(pronostico.p)} su 100.`;
  if (pronostico.band_p5 === null || pronostico.band_p95 === null) return base;
  return `${base} Banda di incertezza fra ${suCento(pronostico.band_p5)} e ${suCento(
    pronostico.band_p95,
  )} su 100.`;
}

/* ------------------------------------------------------------------ */
/* Il silenzio (MASTER 5.3)                                           */
/* ------------------------------------------------------------------ */

export interface VesteSilenzio {
  /** Glifo matematico in mono. NON è un'icona e non va sostituito con un SVG. */
  glifo: string;
  etichetta: string;
  titolo: string;
  sottotitolo: string;
}

/**
 * Il glifo e l'etichetta vengono SEMPRE dalla tabella: sono l'unica cosa che
 * distingue i tre motivi senza colore, quindi non possono dipendere dal testo
 * del backend.
 *
 * Il titolo usa `reasons[0]` quando è disponibile e non è già la frase della
 * transizione. Con una transizione, `reasons[0]` È la frase della transizione
 * (schema.md) e comparirà nel blocco di revisione: usarla anche qui la
 * duplicherebbe sopra la piega.
 */
export function vesteSilenzio(fixture: FixtureInSilenzio): VesteSilenzio {
  const motivo: MotivoSilenzio = fixture.silence.reason;
  const conQuote = fixture.model_weight !== 1.0 || fixture.source === 'blended_with_odds';
  const n = fixture.diagnostics.n_candidates;

  const daTransizione =
    typeof fixture.transition === 'string' && fixture.transition !== 'first';
  const titoloDalBackend = !daTransizione ? fixture.reasons[0] : undefined;

  if (motivo === 'sigma_max') {
    return {
      glifo: '±',
      etichetta: 'STIMA INSTABILE',
      titolo:
        titoloDalBackend ??
        'Abbiamo troppe poche partite affidabili su queste squadre per dare un numero in cui crediamo.',
      sottotitolo: 'La stessa stima oscilla troppo da una simulazione all’altra.',
    };
  }

  if (motivo === 'p_min') {
    return {
      glifo: '<',
      etichetta: 'TROPPO IMPROBABILE',
      titolo:
        titoloDalBackend ??
        'Quello che vediamo di diverso è troppo improbabile perché ve lo consigliamo.',
      sottotitolo:
        'Il mercato che si discosta di più ha meno di 50 probabilità su 100 di uscire.',
    };
  }

  // `S_min` e `no_candidates`: stesso trattamento (regola di schema.md).
  const riferimento = conQuote ? 'quello che dicono già le quote' : 'quello che dice già la media del campionato';
  return {
    glifo: '≈',
    etichetta: 'NON DISTINGUIBILE',
    titolo: titoloDalBackend ?? `Il nostro modello dice quasi esattamente ${riferimento}.`,
    sottotitolo:
      `Abbiamo esaminato ${n} mercati su questa partita. Nessuno passa il nostro criterio.` +
      (conQuote ? ' Il confronto è stato fatto con le quote.' : ''),
  };
}

/* ------------------------------------------------------------------ */
/* Le transizioni — la revisione delle 36 ore (MASTER 6)               */
/* ------------------------------------------------------------------ */

/** Dove va il blocco: sopra la piega per le tre che cambiano stato. */
export const SOPRA_LA_PIEGA: readonly Transizione[] = [
  'changed',
  'prediction_to_silence',
  'silence_to_prediction',
];

export const ETICHETTA_TRANSIZIONE: Record<Exclude<Transizione, 'first'>, string> = {
  changed: 'REVISIONE DELLE 36 ORE — CAMBIATO',
  prediction_to_silence: 'REVISIONE DELLE 36 ORE — RITIRATO',
  silence_to_prediction: 'REVISIONE DELLE 36 ORE — NUOVO',
  confirmed: 'REVISIONE DELLE 36 ORE — CONFERMATO',
  still_silent: 'REVISIONE DELLE 36 ORE — ANCORA NIENTE',
};

/** Il tag in coda alla riga della lista. `confirmed` e `still_silent` non ne hanno. */
export const TAG_LISTA: Partial<Record<Transizione, string>> = {
  changed: 'RIVISTO',
  prediction_to_silence: 'RITIRATO',
  silence_to_prediction: 'NUOVO',
};

export function testoTransizione(
  transizione: Transizione,
  precedente: Precedente | null | undefined,
  pronostico: Pronostico | null,
): string | null {
  const quando = precedente ? conArticolo(precedente.written_at) : null;

  switch (transizione) {
    case 'confirmed':
      return 'Le quote sono arrivate e confermano quello che dicevamo. Il pronostico non cambia.';

    case 'still_silent':
      return 'Anche con le quote non abbiamo niente da aggiungere su questa partita.';

    case 'changed':
      if (!precedente || !pronostico || precedente.p === null) return null;
      return (
        `Fino ${quando} dicevamo ${precedente.market_label} (${suCento(precedente.p)} su 100). ` +
        `Con l’arrivo delle quote la nostra stima è cambiata: ora diciamo ` +
        `${pronostico.label} (${suCento(pronostico.p)} su 100).`
      );

    case 'prediction_to_silence':
      if (!precedente) return null;
      return (
        `Fino ${quando} dicevamo ${precedente.market_label}. Le quote dicono più o meno quello ` +
        `che dicevamo noi: ritiriamo il pronostico. Su questa partita non abbiamo un vantaggio da raccontare.`
      );

    case 'silence_to_prediction':
      if (!pronostico) return null;
      return (
        `Fino ${quando ?? 'a ieri'} non avevamo niente da dire su questa partita. ` +
        `Con l’arrivo delle quote è emerso qualcosa: ${pronostico.label}, ${suCento(pronostico.p)} su 100.`
      );

    case 'first':
      return null;
  }
}

/* ------------------------------------------------------------------ */
/* Il conteggio del giorno (MASTER 5.5)                                */
/* ------------------------------------------------------------------ */

export function fraseSilenziDelGiorno(silenzi: number, totale: number): string {
  if (totale === 0) return 'Oggi non si gioca in nessuno dei campionati che seguiamo.';
  if (silenzi === 0) {
    return totale === 1
      ? 'Oggi abbiamo un pronostico per l’unica partita in programma.'
      : `Oggi abbiamo un pronostico per tutte e ${totale} le partite.`;
  }
  if (silenzi === 1) return `Oggi taciamo su 1 partita su ${totale}.`;
  return `Oggi taciamo su ${silenzi} partite su ${totale}.`;
}

/** La riga delle revisioni, solo se il giorno contiene almeno una transizione di stato. */
export function fraseRevisioniDelGiorno(fixtures: Fixture[]): string | null {
  let riviste = 0;
  let ritirate = 0;
  let nuove = 0;
  for (const f of fixtures) {
    if (f.transition === 'changed') riviste += 1;
    else if (f.transition === 'prediction_to_silence') ritirate += 1;
    else if (f.transition === 'silence_to_prediction') nuove += 1;
  }
  if (riviste + ritirate + nuove === 0) return null;

  /* Solo la prima voce porta il sostantivo; nelle successive lo sostituisce
     "ne" — "abbiamo rivisto 3 pronostici e ne abbiamo ritirato 1". */
  const voci: { verbo: string; quanti: number }[] = [];
  if (riviste > 0) voci.push({ verbo: 'rivisto', quanti: riviste });
  if (nuove > 0) voci.push({ verbo: 'aggiunto', quanti: nuove });
  if (ritirate > 0) voci.push({ verbo: 'ritirato', quanti: ritirate });

  const pezzi = voci.map(({ verbo, quanti }, i) =>
    i === 0
      ? `abbiamo ${verbo} ${quanti} ${quanti === 1 ? 'pronostico' : 'pronostici'}`
      : `ne abbiamo ${verbo} ${quanti}`,
  );

  if (pezzi.length === 1) return `Oggi ${pezzi[0]}.`;
  const ultimo = pezzi.pop();
  return `Oggi ${pezzi.join(', ')} e ${ultimo}.`;
}

/* ------------------------------------------------------------------ */
/* Fasce di probabilità (MASTER 7.3)                                   */
/* ------------------------------------------------------------------ */

export const FASCE = ['0.50-0.65', '0.65-0.80', '0.80-1.00'] as const;
export type ChiaveFascia = (typeof FASCE)[number];

/** La fascia in cui cade `p`, o `null` se sta sotto il pavimento p_min. */
export function fasciaDi(p: number): ChiaveFascia | null {
  if (p < 0.5) return null;
  if (p < 0.65) return '0.50-0.65';
  if (p < 0.8) return '0.65-0.80';
  return '0.80-1.00';
}

/** "65–80" — con trattino da cifre, non un meno. */
export function etichettaFascia(chiave: string): string {
  const [da, a] = chiave.split('-');
  if (da === undefined || a === undefined) return chiave;
  return `${Math.round(Number(da) * 100)}–${Math.round(Number(a) * 100)}`;
}

/* ------------------------------------------------------------------ */
/* Costanti del prodotto                                               */
/* ------------------------------------------------------------------ */

export const REPO = 'https://github.com/GabrieleMarchesini2006/pronostici';

export const GIOCO_RESPONSABILE = {
  testo: 'Telefono verde per le dipendenze da gioco d’azzardo, Istituto Superiore di Sanità: 800 558822',
  href: 'https://www.iss.it/dipendenze-da-gioco-d-azzardo',
};

export const GRATUITA =
  'Gratis, senza pubblicità, senza affiliazioni. Non guadagniamo se scommetti.';
