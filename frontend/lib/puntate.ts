/**
 * IL CONTO DELLE SCHEDINE — quanto si sarebbe messo, e quanto sarebbe tornato.
 *
 * Le puntate le ha decise il proprietario il 25 agosto 2026: dieci euro sul
 * raddoppio, tre sulla multipla. Non sono un esempio e non sono modificabili
 * dal lettore: sono la scommessa che questo sito dichiara di fare, e l'unico
 * modo perché il conto significhi qualcosa è che il numero sia lo stesso ogni
 * giorno, deciso prima e non dopo.
 *
 * SOLO PREZZI VERI, come dappertutto qui dentro. Una schedina entra nel conto
 * quando OGNI gamba ha un prezzo che qualcuno espone davvero. Se ne manca uno,
 * quella schedina non era giocabile a nessuna cifra: metterci il prodotto delle
 * nostre quote eque darebbe un incasso che nessuno avrebbe mai pagato, e il
 * conto diventerebbe una simulazione travestita da rendiconto.
 *
 * IL NUMERO CHE CONTA È IL NETTO, e comprende le perdite. Un conto che mostra
 * solo le vincite è la cosa che fanno i siti che vivono di questo, e sarebbe
 * l'esatto contrario del motivo per cui questa pagina esiste. Su una multipla
 * a 3,01 di prezzo si perde tre euro quattro volte su cinque, e deve vedersi.
 *
 * PERCHÉ IL CONTO COMINCIA TARDI. Le schedine pescano i mercati più probabili
 * — gol di squadra, handicap, combo — e fino al 25 agosto 2026 nessuna fonte
 * gratuita li quotava: su 51 gambe concluse, zero avevano un prezzo. Il record
 * in probabilità esiste da agosto, quello in euro comincia da lì.
 */
import type { Fixture } from './tipi';
import { schedineDelGiorno, type Schedina } from './schedine';

/** Quanto si mette su ognuna delle due. Deciso, non suggerito. */
export const PUNTATE: Record<Schedina['tipo'], number> = {
  raddoppio: 10,
  multipla: 3,
};

export interface Denaro {
  /** Quanto ci si mette. C'è sempre. */
  puntata: number;
  /**
   * Quanto tornerebbe se uscisse tutta intera. `null` quando almeno una gamba
   * è su un mercato che nessuno quota: lì non c'è una giocata possibile, e un
   * numero al suo posto sarebbe inventato.
   */
  ritorno: number | null;
  /** Il guadagno netto: ritorno meno puntata. `null` per la stessa ragione. */
  guadagno: number | null;
  /**
   * Quanto è già successo: il ritorno vero a schedina conclusa — zero se non è
   * uscita — e `null` finché si gioca.
   */
  incasso: number | null;
}

/** I soldi di UNA schedina, con la puntata decisa per il suo tipo. */
export function denaroDi(schedina: Schedina): Denaro {
  const puntata = PUNTATE[schedina.tipo];
  const ritorno = schedina.prezzo === null ? null : puntata * schedina.prezzo;
  const conclusa = schedina.esito !== 'in-corso';
  return {
    puntata,
    ritorno,
    guadagno: ritorno === null ? null : ritorno - puntata,
    incasso:
      ritorno === null || !conclusa ? null : schedina.esito === 'uscita' ? ritorno : 0,
  };
}

export interface Giocata {
  data: string;
  tipo: Schedina['tipo'];
  puntata: number;
  prezzo: number;
  incasso: number;
  uscita: boolean;
}

export interface Conto {
  giocate: Giocata[];
  /** Quante schedine concluse non erano giocabili: mancava un prezzo. */
  senzaPrezzo: number;
  speso: number;
  incassato: number;
  /** Incassato meno speso. Negativo quando si è in perdita, ed è il caso normale. */
  netto: number;
  vinte: number;
  /** Il primo giorno che entra nel conto, o `null` se non ce n'è ancora uno. */
  dal: string | null;
}

/**
 * Il conto su tutti i giorni pubblicati.
 *
 * Prende i giorni già letti invece di leggerli da sé: così questo file resta
 * puro — niente `server-only`, niente filesystem — e la stessa funzione serve
 * la pagina delle schedine, quella dei progressi e un test.
 *
 * Le schedine non stanno nell'archivio: nascono da `schedineDelGiorno` a ogni
 * build. Ricomposte adesso danno quelle dell'ultima build di ogni giorno, che
 * è ciò che il lettore aveva davanti il giorno della partita — i prezzi in
 * archivio sono gli ultimi scritti prima del fischio d'inizio, perché dopo non
 * si scrive più.
 */
export function conto(giorni: { data: string; fixtures: Fixture[] }[]): Conto {
  const giocate: Giocata[] = [];
  let senzaPrezzo = 0;

  for (const giorno of [...giorni].sort((a, b) => a.data.localeCompare(b.data))) {
    const { raddoppio, multipla } = schedineDelGiorno(giorno.fixtures);
    for (const schedina of [raddoppio, multipla]) {
      if (schedina === null || schedina.esito === 'in-corso') continue;
      const soldi = denaroDi(schedina);
      if (soldi.incasso === null) {
        senzaPrezzo += 1;
        continue;
      }
      giocate.push({
        data: giorno.data,
        tipo: schedina.tipo,
        puntata: soldi.puntata,
        prezzo: schedina.prezzo ?? 0,
        incasso: soldi.incasso,
        uscita: schedina.esito === 'uscita',
      });
    }
  }

  const speso = giocate.reduce((acc, g) => acc + g.puntata, 0);
  const incassato = giocate.reduce((acc, g) => acc + g.incasso, 0);

  return {
    giocate,
    senzaPrezzo,
    speso,
    incassato,
    netto: incassato - speso,
    vinte: giocate.filter((g) => g.uscita).length,
    dal: giocate[0]?.data ?? null,
  };
}
