import type { Metadata } from 'next';

import { ModuloProfilo } from '@/components/ModuloProfilo';

/**
 * `noindex` su tutte e tre le pagine dei profili.
 *
 * Non e' pudore: sono pagine senza contenuto per chi non le sta usando, e
 * lasciarle indicizzare significa che una ricerca sul nome del sito puo'
 * restituire «Entra» invece dei pronostici. Il valore del sito e' pubblico e
 * sta altrove.
 */
export const metadata: Metadata = {
  title: 'Entra',
  description: 'Entra nel tuo profilo.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/accedi/' },
};

export default function PaginaAccesso() {
  return (
    <div className="colonna colonna--scheda pagina-profilo">
      <ModuloProfilo modo="accesso" />
    </div>
  );
}
