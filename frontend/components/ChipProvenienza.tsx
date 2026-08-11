import { TESTO_PROVENIENZA, TESTO_PROVENIENZA_RIGA } from '@/lib/testi';
import type { Provenienza } from '@/lib/tipi';

/**
 * Il badge di provenienza. Due stati distinguibili a colpo d'occhio E SENZA
 * COLORE: pieno contro tratteggiato. La differenza sopravvive a monocromia, a
 * daltonismo e alla stampa.
 *
 * Il testo è sempre presente — mai un pallino, mai solo un'icona. Nella riga
 * di lista è abbreviato, perché lì la colonna è stretta e il nome del mercato
 * non si tronca mai.
 *
 * Resta l'UNICO elemento arrotondato dell'intero prodotto: essendo l'unica
 * cosa con un raggio, si stacca da solo. Non è interattivo: nessun hover,
 * nessun cursore a mano (MASTER §7.2).
 */
export function ChipProvenienza({
  source,
  compatto = false,
}: {
  source: Provenienza;
  compatto?: boolean;
}) {
  const pieno = source === 'blended_with_odds';
  return (
    <span
      className={[
        'chip',
        pieno ? 'chip--pieno' : 'chip--vuoto',
        compatto ? 'chip--riga' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {compatto ? TESTO_PROVENIENZA_RIGA[source] : TESTO_PROVENIENZA[source]}
    </span>
  );
}
