import type { Metadata } from 'next';

import { ScegliPassword } from '@/components/Recupero';

export const metadata: Metadata = {
  title: 'Scegli la password nuova',
  description: 'Scegli una password nuova per il tuo profilo.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/recupero/conferma/' },
};

export default function PaginaConfermaRecupero() {
  return (
    <div className="colonna colonna--scheda pagina-profilo">
      <ScegliPassword />
    </div>
  );
}
