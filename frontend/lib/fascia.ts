/**
 * La scelta della fonte per il record di fascia (MASTER 7.3).
 *
 * NOTA sulla regola architetturale di come-stiamo-andando.md: `accuracy.json`
 * e `backtest.json` non si incontrano mai in un componente. Qui non si
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
      periodo: `test storico dal ${dataConAnno(backtest.window.from)} al ${dataConAnno(
        backtest.window.to,
      )}`,
    };
  }

  return null;
}
