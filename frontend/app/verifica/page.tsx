import type { Metadata } from 'next';

import { Verifica } from '@/components/Verifica';

export const metadata: Metadata = {
  title: 'Conferma dell’indirizzo',
  description: 'Conferma il tuo indirizzo email.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/verifica/' },
};

export default function PaginaVerifica() {
  return (
    <div className="colonna colonna--scheda pagina-profilo">
      <Verifica />
    </div>
  );
}
