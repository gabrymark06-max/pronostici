import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { BloccoCampionato } from '@/components/BloccoCampionato';
import { Calendario } from '@/components/Calendario';
import { ComeSiLegge } from '@/components/ComeSiLegge';
import { rangoCompetizione } from '@/lib/campionati';
import {
  finestraGiorni,
  giorniDisponibili,
  giorniVicini,
  leggiAccuracy,
  leggiBacktest,
  leggiGiorno,
  manifestoCrest,
  riepilogoGiorni,
} from '@/lib/dati';
import { recordDiFascia } from '@/lib/fascia';
import { dataLunga, dataLungaMaiuscola } from '@/lib/formato';
import { fraseRevisioniDelGiorno, fraseSilenziDelGiorno, MARCHIO } from '@/lib/testi';
import { tace, type Fixture } from '@/lib/tipi';

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
  const descrizione = `${fraseSilenziDelGiorno(
    giorno.silence_count,
    giorno.total,
  )} Un pronostico per partita, con la probabilità e quante volte pronostici così si sono avverati.`;

  return {
    title: titolo,
    description: descrizione,
    alternates: { canonical: `/giorno/${data}/` },
    /* `siteName` va ripetuto qui: l'oggetto openGraph della pagina SOSTITUISCE
       quello della radice, non ci si fonde, e senza questa riga og:site_name
       non finisce nell'HTML di nessuna pagina reale. */
    openGraph: { title: titolo, description: descrizione, type: 'website', siteName: MARCHIO },
  };
}

/**
 * Raggruppa per campionato, nell'ORDINE DICHIARATO in lib/campionati.ts.
 *
 * Nella v2 l'ordine era quello del primo calcio d'inizio, quindi cambiava
 * ogni giorno: un lettore non poteva imparare dove sta il suo campionato.
 * Un ordine stabile e' meta' dell'organizzazione per campionati.
 */
function perCampionato(fixtures: Fixture[]): { codice: string; partite: Fixture[] }[] {
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
    .sort(
      (a, b) =>
        rangoCompetizione(a.codice) - rangoCompetizione(b.codice) ||
        a.codice.localeCompare(b.codice),
    );
}

/** "14 partite" / "1 partita" / "nessuna partita" — per il titolo non visibile. */
function etichettaPartite(totale: number): string {
  if (totale === 0) return 'nessuna partita';
  return totale === 1 ? '1 partita' : `${totale} partite`;
}

export default async function PaginaGiorno({ params }: Props) {
  const { data } = await params;
  const giorno = leggiGiorno(data);
  if (!giorno) notFound();

  const { precedente, successivo } = giorniVicini(data);
  const manifesto = manifestoCrest();
  const crest = (url: string | null) => (url ? (manifesto[url] ?? url) : null);

  /* Il record di fascia si calcola una volta per riga, qui: i due file
     (accuracy e backtest) si leggono una sola volta per pagina, e nella riga
     arriva gia' un solo record etichettato con la propria provenienza. */
  const accuracy = leggiAccuracy();
  const backtest = leggiBacktest();
  const record = (fixture: Fixture) =>
    tace(fixture) ? null : recordDiFascia(fixture.prediction.p, accuracy, backtest);

  const gruppi = perCampionato(giorno.fixtures);
  const revisioni = fraseRevisioniDelGiorno(giorno.fixtures);
  const silenzi = giorno.silence_count;

  return (
    <>
      <Calendario
        giorni={riepilogoGiorni(finestraGiorni(data))}
        corrente={data}
        precedente={precedente}
        successivo={successivo}
      />

      {/* IL TITOLO NON SI VEDE, ma esiste.
          La data e il conteggio erano stampati subito sotto il calendario, che
          li dice gia' entrambi: la striscia porta la sigla, il numero del
          giorno, il totale delle partite, e segna il giorno corrente. Ripeterli
          in prosa era un titolo che spiegava il controllo che gli stava sopra.
          Resta l'<h1> per i motori e per chi ascolta — nascosto alla vista, MAI
          `display:none`, che lo toglierebbe anche a loro. */}
      <h1 className="solo-lettori">
        {dataLungaMaiuscola(data)} — {etichettaPartite(giorno.total)}
        {silenzi > 0 ? `, ${silenzi} in silenzio` : ''}
      </h1>

      {giorno.total === 0 ? (
        /* Un giorno senza partite NON e' un silenzio e non deve somigliargli:
           niente tacche, niente lastra. */
        <div className="colonna colonna--lista">
          <div className="giorno-vuoto">
            <p>Il {dataLunga(data)} non si gioca in nessuno dei campionati che seguiamo.</p>
            <p>Il calendario qui sopra porta ai giorni in cui si gioca.</p>
          </div>
        </div>
      ) : (
        <>
          {/* LA FASCIA DELLA LEGENDA. Attaccata alla striscia dei giorni —
              stesso fondo, nessuno stacco: fra il calendario e cio' che segue
              non deve restare una banda di fondo pagina. Il respiro sta DENTRO
              la fascia, sopra e sotto i riquadri, e la fascia e' larga quanto
              la lista perche' e' la stessa superficie. */}
          <div className="fascia">
            <div className="colonna colonna--lista fascia__interno">
              <ComeSiLegge />
            </div>
          </div>

          {/* LA LASTRA. Sotto i 1024px esce dalla colonna e tocca i bordi dello
              schermo: un documento ha i margini, uno schermo no. */}
          <div className="lastra">
            <div className="colonna colonna--lista lista-lastra">
              {/* La riga delle revisioni descrive la LISTA, non la giornata:
                  sta qui, in testa a cio' che descrive, e compare solo nei
                  giorni in cui qualcosa e' davvero cambiato. */}
              {revisioni ? <p className="lista__revisioni">{revisioni}</p> : null}

              {gruppi.map((gruppo) => (
                <BloccoCampionato
                  key={gruppo.codice}
                  codice={gruppo.codice}
                  partite={gruppo.partite}
                  crest={crest}
                  record={record}
                />
              ))}
            </div>
          </div>
        </>
      )}
    </>
  );
}
