import type { Metadata } from 'next';

import { ConfermaRecupero } from '@/components/PaginaRecupero';
import { soloSeProfiliAccesi } from '@/lib/guardia-profili';

/* `noindex`: sono pagine senza contenuto per chi non le sta usando, e
   un'indicizzata «Password dimenticata» sul nome del sito sarebbe il risultato
   sbagliato al posto dei pronostici. */
export const metadata: Metadata = {
  title: 'Scegli una password nuova',
  description: 'Scegli una password nuova con il collegamento ricevuto.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/recupero/conferma/' },
};

export default function Pagina() {
  soloSeProfiliAccesi();

  return (
    <div className="colonna colonna--scheda pagina-profilo">
      <ConfermaRecupero />
    </div>
  );
}
