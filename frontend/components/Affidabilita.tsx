import { qualificaBanda } from '@/lib/testi';

/**
 * L'AFFIDABILITÀ — la propria colonna nella riga di lista, e la quarta scala
 * dell'elemento firma.
 *
 * Disegna la banda p5–p95 come un TRATTO lungo quanto la banda, con due
 * grazie agli estremi, su un asse largo quanto la colonna. Tratto corto =
 * stima stretta; tratto lungo = stima larga. Due righe si confrontano a colpo
 * d'occhio perché l'asse è lo stesso per tutte, ed è la ragione per cui
 * l'affidabilità merita una colonna invece di stare appesa sotto la cifra
 * come faceva in v3: incolonnata si legge di sfuggita, sotto la cifra andava
 * cercata.
 *
 * LINGUAGGIO B: solo tratto, mai un pieno. La probabilità è un pieno
 * numerico, l'affidabilità è un tratto — le due marche restano distinguibili
 * in monocromia, in stampa e per chi non distingue i colori.
 *
 * L'asse copre 40 punti di banda: oltre quella larghezza il tratto satura.
 * Non è un valore inventato — è la larghezza oltre la quale una stima non
 * viene comunque consigliata, quindi al massimo dell'asse corrisponde il
 * caso peggiore che può comparire in lista.
 *
 * Per chi ascolta il tratto non esiste: la parola («stima stretta») c'è
 * sempre in `.solo-lettori`. Una geometria che porta un significato senza
 * un'alternativa testuale è un'informazione persa, non un dettaglio.
 */
const ASSE = 0.4;
const MINIMO = 0.1;

export function Affidabilita({ p5, p95 }: { p5: number | null; p95: number | null }) {
  if (p5 === null || p95 === null) {
    return (
      <span className="affid">
        <span className="affid__muto" aria-hidden="true" />
        <span className="solo-lettori">Banda di incertezza non calcolata.</span>
      </span>
    );
  }

  const larghezza = Math.max(MINIMO, Math.min(1, (p95 - p5) / ASSE));
  const qualifica = qualificaBanda(p5, p95);

  return (
    <span className="affid">
      <span
        className="affid__tratto"
        style={{ width: `${(larghezza * 100).toFixed(1)}%` }}
        aria-hidden="true"
      >
        <i className="affid__grazia affid__grazia--sx" />
        <i className="affid__grazia affid__grazia--dx" />
      </span>
      <span className="solo-lettori">Stima {qualifica}.</span>
    </span>
  );
}
