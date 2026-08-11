/**
 * La scelta della fonte per il record di fascia.
 *
 * REGOLA ARCHITETTURALE: `accuracy.json` (il vivo) e `backtest.json` (lo
 * storico) non si incontrano mai in un componente. Qui non si
 * incontrano nemmeno: questa funzione SCEGLIE una delle due fonti e restituisce
 * un solo record, già etichettato con la propria provenienza. Non somma, non
 * media, non mette due numeri nella stessa frase. Il componente che la consuma
 * riceve un numero e una fonte, mai due serie.
 *
 * Il passaggio dal test storico al vivo è PER FASCIA, non globale, e avviene
 * automaticamente appena quella fascia raggiunge 50 osservazioni dal vivo.
 */
import { dataConAnno } from './formato';
import { etichettaFascia, fasciaDi } from './testi';
import type { Accuracy, Backtest } from './tipi';

const SOGLIA_PASSAGGIO_AL_VIVO = 50;

export type FonteFascia = 'vivo' | 'storico';

export interface RecordFascia {
  fascia: string;
  etichetta: string;
  fonte: FonteFascia;
  n: number;
  suCento: number;
  /**
   * SOLO la finestra temporale — «dal 17 agosto 2024 al 7 agosto 2026», «da
   * ieri». La FONTE non sta qui: la nomina il componente, insieme al numero,
   * dentro la frase. Quando `periodo` conteneva anche «test storico» la
   * scheda stampava «nel nostro test storico: 3182 casi, test storico dal…».
   */
  periodo: string;
}

export function recordDiFascia(
  p: number,
  accuracy: Accuracy,
  backtest: Backtest,
): RecordFascia | null {
  const chiave = fasciaDi(p);
  if (!chiave) return null;

  const dalVivo = accuracy.live.buckets?.[chiave];
  if (dalVivo && dalVivo.n >= SOGLIA_PASSAGGIO_AL_VIVO && typeof dalVivo.hit_rate === 'number') {
    return {
      fascia: chiave,
      etichetta: etichettaFascia(chiave),
      fonte: 'vivo',
      n: dalVivo.n,
      suCento: Math.round(dalVivo.hit_rate * 100),
      periodo: `da ${dataConAnno(accuracy.generated_at.slice(0, 10))}`,
    };
  }

  const daStorico = backtest.buckets[chiave];
  if (daStorico && daStorico.enough !== false && typeof daStorico.hit_rate === 'number') {
    return {
      fascia: chiave,
      etichetta: etichettaFascia(chiave),
      fonte: 'storico',
      n: daStorico.n,
      suCento: Math.round(daStorico.hit_rate * 100),
      periodo: `dal ${dataConAnno(backtest.window.from)} al ${dataConAnno(backtest.window.to)}`,
    };
  }

  return null;
}

/**
 * La forma CORTA, per la riga di lista.
 *
 * "fascia 80–100 · avverati 92 su 100 · n=3182, storico" — la fascia sta
 * dentro la frase perche' un tasso senza la sua fascia e' una media che mente:
 * gli 85 su 100 sono facili, i 55 no.
 *
 * `n` e la provenienza ci sono anche qui. La versione precedente li ometteva
 * per mancanza di spazio, ragionando che una fonte non qualificata fosse
 * peggio di nessuna. Ma e' la lista il posto piu' letto del prodotto — 388
 * occorrenze su 238 pagine contro una per scheda — e un tasso senza il suo `n`
 * e' esattamente cio' che rimproveriamo a chi scrive "accuratezza superiore al
 * 75%" senza dire su quante partite. Il posto piu' letto e' quello dove la
 * qualificazione conta di piu', non quello dove si puo' saltare.
 */
export function fraseCortaDiFascia(record: RecordFascia | null): string | null {
  if (!record) return null;
  const fonte = record.fonte === 'vivo' ? 'dal vivo' : 'storico';
  return (
    `fascia ${record.etichetta} · avverati ${record.suCento} su 100 · ` +
    `n=${record.n}, ${fonte}`
  );
}
