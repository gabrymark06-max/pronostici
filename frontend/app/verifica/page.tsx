import type { Metadata } from 'next';

import { PaginaVerifica } from '@/components/PaginaVerifica';

/* `noindex`: sono pagine senza contenuto per chi non le sta usando, e
   un'indicizzata «Password dimenticata» sul nome del sito sarebbe il risultato
   sbagliato al posto dei pronostici. */
export const metadata: Metadata = {
  title: 'Conferma dell’indirizzo',
  description: 'Conferma il tuo indirizzo email.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/verifica/' },
};

export default function Pagina() {
  return (
    <div className="colonna colonna--scheda pagina-profilo">
      <PaginaVerifica />
    </div>
  );
}
