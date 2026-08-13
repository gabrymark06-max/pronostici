import type { Metadata } from 'next';

import { ModuloProfilo } from '@/components/ModuloProfilo';

export const metadata: Metadata = {
  title: 'Crea un profilo',
  description: 'Crea un profilo sul sito.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/registrati/' },
};

export default function PaginaRegistrazione() {
  return (
    <div className="colonna colonna--scheda pagina-profilo">
      <ModuloProfilo modo="registrazione" />
    </div>
  );
}
