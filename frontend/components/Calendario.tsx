'use client';

import { useEffect, useRef } from 'react';

import type { RiepilogoGiorno } from '@/lib/dati';
import { dataLunga, pezziGiorno } from '@/lib/formato';

/**
 * IL CALENDARIO — la sola superficie di controllo del prodotto, e l'unica
 * cosa appiccicata alla pagina.
 *
 * Cosa non andava nella striscia della v2:
 *  - sette caselle mono strette e tutte uguali, in cui il numero del giorno
 *    non pesava piu' dell'abbreviazione;
 *  - le due frecce spinte agli estremi opposti del contenitore, che a 1440px
 *    finivano a mezzo schermo di distanza dalle caselle e non sembravano piu'
 *    appartenere allo stesso comando;
 *  - nessuna informazione: una casella diceva solo che quel giorno esiste.
 *
 * Qui le frecce FIANCHEGGIANO il binario, il gruppo e' centrato, e ogni
 * casella porta il proprio numero di partite. Il calendario dice anche dove
 * vale la pena andare, non solo dove si puo' andare.
 *
 * Restano <a> reali verso /giorno/{data}: funzionano senza JavaScript, sono
 * condivisibili, e il back del browser fa la cosa giusta senza codice.
 * L'unico JavaScript porta in vista il giorno corrente quando il binario
 * scorre, e lo fa scrivendo `scrollLeft` invece di `scrollIntoView`: cosi'
 * scorre il binario, mai la pagina.
 */
export function Calendario({
  giorni,
  corrente,
  precedente,
  successivo,
}: {
  giorni: RiepilogoGiorno[];
  corrente: string;
  precedente: string | null;
  successivo: string | null;
}) {
  const binario = useRef<HTMLUListElement>(null);
  const attivo = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    const contenitore = binario.current;
    const voce = attivo.current;
    if (!contenitore || !voce) return;
    const centro = voce.offsetLeft - (contenitore.clientWidth - voce.offsetWidth) / 2;
    contenitore.scrollLeft = Math.max(0, centro);
  }, [corrente]);

  return (
    <nav className="rail" aria-label="Calendario">
      <div className="rail__interno colonna colonna--lista">
        <Freccia data={precedente} verso="precedente" />

        <ul className="rail__binario" ref={binario}>
          {giorni.map((giorno) => {
            const { sigla, numero } = pezziGiorno(giorno.data);
            const attuale = giorno.data === corrente;
            return (
              <li key={giorno.data}>
                <a
                  ref={attuale ? attivo : undefined}
                  className="rail__giorno"
                  href={`/giorno/${giorno.data}/`}
                  aria-current={attuale ? 'date' : undefined}
                  aria-label={`${dataLunga(giorno.data)}, ${etichettaConteggio(giorno.total)}`}
                >
                  <span className="rail__sigla" aria-hidden="true">
                    {sigla}
                  </span>
                  <span className="rail__numero" aria-hidden="true">
                    {numero}
                  </span>
                  <span className="rail__conteggio" aria-hidden="true">
                    {giorno.total}
                  </span>
                </a>
              </li>
            );
          })}
        </ul>

        <Freccia data={successivo} verso="successivo" />
      </div>
    </nav>
  );
}

function etichettaConteggio(total: number): string {
  if (total === 0) return 'nessuna partita';
  return total === 1 ? '1 partita' : `${total} partite`;
}

/**
 * L'estremo senza giorno non e' un link morto: e' un segno spento, fuori
 * dall'ordine di tabulazione e dichiarato come tale.
 */
function Freccia({ data, verso }: { data: string | null; verso: 'precedente' | 'successivo' }) {
  const glifo = verso === 'precedente' ? '‹' : '›';

  if (!data) {
    return (
      <span className="rail__freccia rail__freccia--spenta" aria-hidden="true">
        {glifo}
      </span>
    );
  }

  return (
    <a
      className="rail__freccia"
      href={`/giorno/${data}/`}
      aria-label={`Giorno ${verso}, ${dataLunga(data)}`}
    >
      <span aria-hidden="true">{glifo}</span>
    </a>
  );
}
