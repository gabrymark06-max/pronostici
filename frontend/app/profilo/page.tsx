import type { Metadata } from 'next';

import { PannelloProfilo } from '@/components/PannelloProfilo';

export const metadata: Metadata = {
  title: 'Il tuo profilo',
  description: 'I dati del tuo profilo.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/profilo/' },
};

export default function PaginaConto() {
  return (
    <div className="colonna colonna--scheda pagina-profilo">
      <PannelloProfilo />
    </div>
  );
}
