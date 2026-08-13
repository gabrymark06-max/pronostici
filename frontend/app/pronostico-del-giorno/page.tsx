import type { Metadata } from 'next';

import { CorpoSchedine } from '@/components/CorpoSchedine';
import { giornoDiApertura } from '@/lib/dati';
import { MARCHIO } from '@/lib/testi';

/**
 * `/pronostico-del-giorno/` MOSTRA le schedine del giorno piu' recente.
 *
 * Non e' un rimando. La versione precedente lo era — refresh nel <head> piu' un
 * link visibile — ed era sbagliata proprio perche' questa e' la prima voce
 * della barra: chi ci clicca deve trovare i pronostici, non una pagina bianca
 * con sopra scritto dove sono. Un rimando va bene sulla radice, dove nessuno
 * arriva per leggere; qui no.
 *
 * Il canonical punta comunque alla pagina DATATA: il contenuto e' lo stesso, e
 * l'indirizzo con la data e' quello che continuera' a valere anche domani.
 * Questo indirizzo senza data resta quello da condividere e da mettere nei
 * preferiti, perche' deve voler dire «oggi» anche fra un mese.
 */
export function generateMetadata(): Metadata {
  const giorno = giornoDiApertura();
  const titolo = 'Pronostico del giorno';
  const descrizione =
    'Due schedine costruite sui pronostici di oggi: un raddoppio a due partite e una ' +
    'multipla che arriva a 5,00 con il minor numero di partite possibile. Con scritto ' +
    'quante volte su cento escono tutte intere.';

  return {
    title: titolo,
    description: descrizione,
    ...(giorno ? { alternates: { canonical: `/pronostico-del-giorno/${giorno}/` } } : {}),
    openGraph: { title: titolo, description: descrizione, type: 'website', siteName: MARCHIO },
  };
}

export default function PronosticoDelGiorno() {
  const giorno = giornoDiApertura();

  if (!giorno) {
    return (
      <div className="colonna colonna--lista">
        <div className="giorno-vuoto">
          <p>Non ci sono ancora giornate pubblicate.</p>
          <p>Le schedine compaiono qui quando il calcolo della notte ha girato.</p>
        </div>
      </div>
    );
  }

  return <CorpoSchedine data={giorno} />;
}
