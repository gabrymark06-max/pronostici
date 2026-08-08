import type { Metadata } from 'next';

import { giornoDiApertura } from '@/lib/dati';
import { dataLunga } from '@/lib/formato';

/**
 * `/` è un rimando statico al giorno più recente disponibile.
 *
 * In export statico non esiste un redirect di server: si usa il refresh nel
 * <head>, che funziona senza JavaScript, più un link visibile che è il ripiego
 * per chiunque il refresh non raggiunga. Il canonical punta al giorno, così
 * non si crea contenuto duplicato.
 */
export function generateMetadata(): Metadata {
  const giorno = giornoDiApertura();
  if (!giorno) return { title: 'Pronostici' };
  return {
    alternates: { canonical: `/giorno/${giorno}/` },
    other: { refresh: `0; url=/giorno/${giorno}/` },
  };
}

export default function Home() {
  const giorno = giornoDiApertura();

  if (!giorno) {
    return (
      <div className="colonna colonna--lista">
        <div className="giorno-vuoto">
          <p>Non ci sono ancora giornate pubblicate.</p>
          <p>
            I pronostici compaiono qui quando il calcolo della notte ha girato.{' '}
            <a href="/come-funziona/">Come funziona</a>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="colonna colonna--lista">
      <div className="giorno-vuoto">
        <p>
          <a href={`/giorno/${giorno}/`}>Vai alle partite di {dataLunga(giorno)} →</a>
        </p>
      </div>
    </div>
  );
}
