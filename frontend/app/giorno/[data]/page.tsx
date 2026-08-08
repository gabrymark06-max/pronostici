import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { RigaPartita } from '@/components/RigaPartita';
import { giorniDisponibili, giorniVicini, leggiGiorno, manifestoCrest } from '@/lib/dati';
import { dataBreve, dataLunga, dataLungaMaiuscola } from '@/lib/formato';
import {
  fraseRevisioniDelGiorno,
  fraseSilenziDelGiorno,
  nomeCompetizione,
} from '@/lib/testi';
import type { Fixture } from '@/lib/tipi';

/** Tutte le rotte sono pre-renderizzate: nessun runtime, deep-linking obbligatorio. */
export function generateStaticParams() {
  return giorniDisponibili().map((data) => ({ data }));
}

export const dynamicParams = false;

type Props = { params: Promise<{ data: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { data } = await params;
  const giorno = leggiGiorno(data);
  if (!giorno) return { title: `Partite del ${data}` };

  const titolo = `${dataLungaMaiuscola(data)}: ${giorno.total} partite`;
  const descrizione =
    giorno.silence_count > 0
      ? `${fraseSilenziDelGiorno(giorno.silence_count, giorno.total)} Un pronostico per partita, con la probabilità e la sua definizione.`
      : `${fraseSilenziDelGiorno(giorno.silence_count, giorno.total)} Ogni pronostico con la probabilità e la sua definizione.`;

  return {
    title: titolo,
    description: descrizione,
    alternates: { canonical: `/giorno/${data}/` },
    openGraph: { title: titolo, description: descrizione, type: 'website' },
  };
}

/** Raggruppa per competizione, in ordine di primo calcio d'inizio. */
function perCompetizione(fixtures: Fixture[]): { codice: string; partite: Fixture[] }[] {
  const gruppi = new Map<string, Fixture[]>();
  for (const f of fixtures) {
    const esistente = gruppi.get(f.competition);
    if (esistente) esistente.push(f);
    else gruppi.set(f.competition, [f]);
  }
  return [...gruppi.entries()]
    .map(([codice, partite]) => ({
      codice,
      partite: [...partite].sort((a, b) => a.utc_date.localeCompare(b.utc_date)),
    }))
    .sort((a, b) => (a.partite[0]?.utc_date ?? '').localeCompare(b.partite[0]?.utc_date ?? ''));
}

export default async function PaginaGiorno({ params }: Props) {
  const { data } = await params;
  const giorno = leggiGiorno(data);
  if (!giorno) notFound();

  const { precedente, successivo } = giorniVicini(data);
  const manifesto = manifestoCrest();
  const crest = (url: string | null) => (url ? (manifesto[url] ?? url) : null);

  const gruppi = perCompetizione(giorno.fixtures);
  const revisioni = fraseRevisioniDelGiorno(giorno.fixtures);
  const quotaSilenzi = giorno.total > 0 ? giorno.silence_count / giorno.total : 0;

  return (
    <div className="colonna colonna--lista">
      <nav className="giorno__navigazione" aria-label="Cambia giorno">
        {precedente ? (
          <a
            className="freccia-giorno"
            href={`/giorno/${precedente}/`}
            aria-label={`Giorno precedente, ${dataLunga(precedente)}`}
          >
            <span aria-hidden="true">‹</span> {dataBreve(precedente)}
          </a>
        ) : (
          <span className="freccia-giorno freccia-giorno--spenta" aria-disabled="true">
            <span aria-hidden="true">‹</span> —
          </span>
        )}

        <h1 className="titolo-pagina giorno__titolo">{dataLungaMaiuscola(data)}</h1>

        {successivo ? (
          <a
            className="freccia-giorno"
            href={`/giorno/${successivo}/`}
            aria-label={`Giorno successivo, ${dataLunga(successivo)}`}
          >
            {dataBreve(successivo)} <span aria-hidden="true">›</span>
          </a>
        ) : (
          <span className="freccia-giorno freccia-giorno--spenta" aria-disabled="true">
            — <span aria-hidden="true">›</span>
          </span>
        )}
      </nav>

      {giorno.total === 0 ? (
        /* Un giorno senza partite non è un silenzio e non deve somigliargli:
           niente cornice, niente filetto carminio. */
        <div className="giorno-vuoto">
          <p>Il {dataLunga(data)} non si gioca in nessuno dei campionati che seguiamo.</p>
          <p>Le frecce qui sopra portano al primo giorno con partite.</p>
        </div>
      ) : (
        <>
          {/* Il conteggio c'è SEMPRE, anche a zero: è il rituale del prodotto.
              Un sito che conta i propri silenzi in prima pagina sembra severo. */}
          <p className="giorno__conteggio">
            {ripartisciConCifre(fraseSilenziDelGiorno(giorno.silence_count, giorno.total))}
          </p>

          {/* Senza cifre in carminio: l'accento tocca solo il conteggio dei
              silenzi, che non è una stima ma una rivendicazione. */}
          {revisioni ? <p className="giorno__revisioni">{revisioni}</p> : null}

          <p className="definizione">
            Tacere è una risposta: la diamo quando nessun mercato supera il nostro criterio.{' '}
            <a href="/come-funziona/#silenzio">Perché →</a>
          </p>

          {/* Valvola del 40%: una nota, non un banner d'allarme.
              Non è un role="alert": non è un errore. */}
          {quotaSilenzi > 0.4 ? (
            <p className="valvola">
              Oggi è una giornata insolita: taciamo su più di quattro partite su dieci. Non
              abbassiamo la soglia per riempire la pagina —{' '}
              <a href="/come-funziona/#silenzio">spieghiamo perché</a>.
            </p>
          ) : null}

          {gruppi.map((gruppo) => (
            <section className="gruppo-competizione" key={gruppo.codice}>
              <h2 className="label gruppo-competizione__titolo">
                {nomeCompetizione(gruppo.codice)}
              </h2>
              <ul className="lista-partite">
                {gruppo.partite.map((fixture) => (
                  <li key={fixture.match_id}>
                    <RigaPartita fixture={fixture} crest={crest} />
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </>
      )}
    </div>
  );
}

/**
 * Le cifre del conteggio vanno in Newsreader 600 --accent: è l'unica cifra che
 * il carminio ha il permesso di toccare, perché non è una stima — è una
 * rivendicazione.
 */
function ripartisciConCifre(frase: string) {
  return frase.split(/(\d+)/).map((pezzo, i) =>
    /^\d+$/.test(pezzo) ? (
      <span className="cifra" key={`${i}-${pezzo}`}>
        {pezzo}
      </span>
    ) : (
      pezzo
    ),
  );
}
