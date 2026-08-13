import type { Metadata } from 'next';

import { ChiediRecupero } from '@/components/Recupero';

export const metadata: Metadata = {
  title: 'Password dimenticata',
  description: 'Reimposta la password del tuo profilo.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/recupero/' },
};

export default function PaginaRecupero() {
  return (
    <div className="colonna colonna--scheda pagina-profilo">
      <ChiediRecupero />
    </div>
  );
}
