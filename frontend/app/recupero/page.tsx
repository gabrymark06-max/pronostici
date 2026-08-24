import type { Metadata } from 'next';

import { ChiediRecupero } from '@/components/PaginaRecupero';
import { soloSeProfiliAccesi } from '@/lib/guardia-profili';

/* `noindex`: sono pagine senza contenuto per chi non le sta usando, e
   un'indicizzata «Password dimenticata» sul nome del sito sarebbe il risultato
   sbagliato al posto dei pronostici. */
export const metadata: Metadata = {
  title: 'Password dimenticata',
  description: 'Chiedi un collegamento per reimpostare la password.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/recupero/' },
};

export default function Pagina() {
  soloSeProfiliAccesi();

  return (
    <div className="colonna colonna--scheda pagina-profilo">
      <ChiediRecupero />
    </div>
  );
}
