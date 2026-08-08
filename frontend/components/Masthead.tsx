'use client';

import { usePathname } from 'next/navigation';

import { TemaToggle } from './TemaToggle';

/**
 * Tre destinazioni, sempre visibili, nessun hamburger a nessuna larghezza:
 * tre voci non si nascondono. A 375px entrano senza abbreviare.
 * Voce attiva: sottolineatura 2px + aria-current — mai il solo colore.
 */
export function Masthead({ giornoApertura }: { giornoApertura: string | null }) {
  const percorso = usePathname();

  const voci = [
    {
      etichetta: 'Oggi',
      href: giornoApertura ? `/giorno/${giornoApertura}/` : '/',
      attiva:
        percorso === '/' || percorso.startsWith('/giorno') || percorso.startsWith('/partita'),
    },
    {
      etichetta: 'Come stiamo andando',
      href: '/come-stiamo-andando/',
      attiva: percorso.startsWith('/come-stiamo-andando'),
    },
    {
      etichetta: 'Come funziona',
      href: '/come-funziona/',
      attiva: percorso.startsWith('/come-funziona'),
    },
  ];

  return (
    <header className="masthead">
      <div className="colonna">
        <div className="masthead__riga">
          <a className="masthead__testata" href="/">
            Pronostici
          </a>
          <TemaToggle />
        </div>
        <nav className="nav" aria-label="Principale">
          {voci.map((voce) => (
            <a
              key={voce.etichetta}
              className="nav__voce"
              href={voce.href}
              aria-current={voce.attiva ? 'page' : undefined}
            >
              {voce.etichetta}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
