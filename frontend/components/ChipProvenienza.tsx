import { TESTO_PROVENIENZA } from '@/lib/testi';
import type { Provenienza } from '@/lib/tipi';

/**
 * Il badge di provenienza. Due stati distinguibili a colpo d'occhio E SENZA
 * COLORE: pieno contro tratteggiato. La differenza sopravvive a monocromia, a
 * daltonismo e alla stampa.
 *
 * Il testo è sempre presente — mai un pallino, mai solo un'icona.
 * Non è interattivo: nessun hover, nessun cursore a mano (MASTER 7.2).
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
      {TESTO_PROVENIENZA[source]}
    </span>
  );
}
