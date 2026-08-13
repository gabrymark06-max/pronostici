import type { Metadata } from 'next';

import { ModuloConto } from '@/components/ModuloConto';

export const metadata: Metadata = {
  title: 'Crea un conto',
  description: 'Crea un conto sul sito.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/registrati/' },
};

export default function PaginaRegistrazione() {
  return (
    <div className="colonna colonna--scheda pagina-conto">
      <ModuloConto modo="registrazione" />
    </div>
  );
}
