import type { Metadata } from 'next';

import { PannelloProfilo } from '@/components/PannelloProfilo';
import { soloSeProfiliAccesi } from '@/lib/guardia-profili';

export const metadata: Metadata = {
  title: 'Il tuo profilo',
  description: 'I dati del tuo profilo.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/profilo/' },
};

export default function PaginaConto() {
  soloSeProfiliAccesi();

  return (
    <div className="colonna colonna--scheda pagina-profilo">
      <PannelloProfilo />
    </div>
  );
}
