import type { Metadata } from 'next';

import { PannelloConto } from '@/components/PannelloConto';

export const metadata: Metadata = {
  title: 'Il tuo conto',
  description: 'I dati del tuo conto.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/conto/' },
};

export default function PaginaConto() {
  return (
    <div className="colonna colonna--scheda pagina-conto">
      <PannelloConto />
    </div>
  );
}
