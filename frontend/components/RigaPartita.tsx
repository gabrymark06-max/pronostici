
import { attributoOra, ora, suCento } from '@/lib/formato';
import { TAG_LISTA, vesteSilenzio } from '@/lib/testi';
import { tace, type Fixture } from '@/lib/tipi';

import { MiniBanda } from './BarraProbabilita';
import { ChipProvenienza } from './ChipProvenienza';
import { Crest } from './Crest';

/**
 * Un <a> che avvolge l'intera riga, min-height 48px, divisore 1px fra le righe.
 * Hover: solo tinta di fondo in 180ms — mai transform, mai ombra, nessuno
 * spostamento di layout.
 *
 * Il silenzio ha la STESSA ALTEZZA e lo STESSO PESO di una riga con pronostico.
 * La differenza è di FORMA, non di tinta: corsivo serif contro tondo + cifra.
 * Il testo resta --ink pieno — attenuarlo sarebbe dire che quella riga vale meno.
 */
export function RigaPartita({
  fixture,
  crest,
}: {
  fixture: Fixture;
  crest: (url: string | null) => string | null;
}) {
  const tag = fixture.transition ? TAG_LISTA[fixture.transition] : undefined;
  const concluso = fixture.result != null;

  return (
    <a className="row-partita" href={`/partita/${fixture.match_id}/`}>
      <span className="row-partita__squadre">
        <span className="crest-coppia">
          <Crest src={crest(fixture.home.crest)} tla={fixture.home.tla} />
          <Crest src={crest(fixture.away.crest)} tla={fixture.away.tla} />
        </span>
        <time className="row-partita__ora" dateTime={attributoOra(fixture.utc_date)}>
          {ora(fixture.utc_date)}
        </time>
        <span className="row-partita__nomi">
          {fixture.home.name} — {fixture.away.name}
        </span>
      </span>

      <span className="row-partita__consiglio">
        {tace(fixture) ? (
          <>
            <span className="row-partita__silenzio">nessun pronostico</span>
            <span className="row-partita__glifo" aria-hidden="true">
              {vesteSilenzio(fixture).glifo}
            </span>
          </>
        ) : (
          <>
            {/* Mai troncare il nome del mercato: è il contenuto. */}
            <span className="row-partita__mercato">{fixture.prediction.label}</span>
            <span className="row-partita__cifra">{suCento(fixture.prediction.p)}</span>
            {fixture.prediction.band_p5 !== null && fixture.prediction.band_p95 !== null ? (
              <MiniBanda p5={fixture.prediction.band_p5} p95={fixture.prediction.band_p95} />
            ) : null}
            <ChipProvenienza source={fixture.source} compatto />
          </>
        )}

        {tag ? <span className="row-partita__tag">{tag}</span> : null}

        {/* Esito: parola + glifo + colore, mai il colore da solo.
            Le righe concluse restano a piena opacità: il registro è il prodotto. */}
        {concluso && fixture.result ? (
          <span
            className={`row-partita__esito ${
              fixture.outcome === 1 ? 'esito-uscito' : fixture.outcome === 0 ? 'esito-non-uscito' : ''
            }`}
          >
            <span>
              {fixture.result.home}–{fixture.result.away}
            </span>
            {fixture.outcome === 1 ? (
              <span>· uscito ▪</span>
            ) : fixture.outcome === 0 ? (
              <span>· non uscito ▫</span>
            ) : null}
          </span>
        ) : null}
      </span>
    </a>
  );
}
