import { fraseCortaDiFascia, type RecordFascia } from '@/lib/fascia';
import { attributoOra, ora, suCento } from '@/lib/formato';
import { TAG_LISTA, TESTO_PROVENIENZA_RIGA, vesteSilenzio } from '@/lib/testi';
import { tace, type Fixture } from '@/lib/tipi';

import { Affidabilita } from './Affidabilita';
import { Crest } from './Crest';
import { Misurino } from './Misurino';

/**
 * LA RIGA DI PARTITA — il cuore del prodotto.
 *
 * Un <a> che avvolge l'intera riga, su una griglia a COLONNE FISSE
 * nell'ordine che chi usa un sito di risultati si aspetta:
 *
 *   ora · stemma+casa / stemma+ospite · pronostico · probabilità · affidabilità
 *
 * Le colonne si incolonnano lungo tutta la lista: scorrere la pagina diventa
 * un confronto invece che quaranta letture separate. È la meccanica dei siti
 * di risultati, ed è l'unica cosa che se ne prende — nessun marchio, nessun
 * logotipo, nessuna identità visiva di terzi.
 *
 * Le due squadre sono IMPILATE, casa sopra e ospite sotto, ognuna con il
 * proprio stemma da 18px: due righe COMPATTE dentro la stessa riga di lista,
 * non due righe alte come in v3.
 *
 * ALTEZZA 44px ESATTI da 768px in su, e il bersaglio COINCIDE con la riga.
 * Non 40px con un ::after che sborda: due righe adiacenti che sbordano di 2px
 * si contendono 4px di banda, e il clic in quella banda finisce sulla riga
 * sbagliata. Un bersaglio ambiguo è peggio di uno piccolo.
 *
 * Sotto i 768px la riga passa a due livelli (58px) dentro la stessa griglia,
 * con `grid-template-areas`: è un cambio di forma dichiarato, non un
 * rimescolamento. Cinque colonne a 375px si otterrebbero solo troncando il
 * nome del mercato, che è il contenuto e non si tronca mai.
 *
 * Il silenzio ha la STESSA ALTEZZA e lo STESSO PESO di una riga con
 * pronostico. La differenza è di FORMA, non di tinta: corsivo serif contro
 * tondo sans, glifo contro cifra. La colonna della cifra NON RESTA MAI VUOTA
 * — se si svuotasse, il silenzio tornerebbe a leggersi come un buco in una
 * lista fitta, che è esattamente il contrario di quello che è.
 */
export function RigaPartita({
  fixture,
  crest,
  record,
}: {
  fixture: Fixture;
  crest: (url: string | null) => string | null;
  /** Il tasso storico della fascia di questo pronostico. `null` se tace. */
  record: RecordFascia | null;
}) {
  const tag = fixture.transition ? TAG_LISTA[fixture.transition] : undefined;
  const prova = fraseCortaDiFascia(record);
  const muta = tace(fixture);

  return (
    <a className="riga-partita pad-lista" href={`/partita/${fixture.match_id}/`}>
      <time className="riga-partita__ora" dateTime={attributoOra(fixture.utc_date)}>
        {ora(fixture.utc_date)}
      </time>

      <span className="squadre">
        <span className="squadra">
          <Crest src={crest(fixture.home.crest)} tla={fixture.home.tla} />
          {/* `title` è il nome per esteso: da 768px la colonna tronca con
              ellissi per tenere la riga a 44px anche con i nomi lunghi. */}
          <span className="squadra__nome" title={fixture.home.name}>
            {fixture.home.name}
          </span>
        </span>
        <span className="squadra">
          <Crest src={crest(fixture.away.crest)} tla={fixture.away.tla} />
          <span className="squadra__nome" title={fixture.away.name}>
            {fixture.away.name}
          </span>
        </span>
      </span>

      <span className="riga-partita__mercato">
        {muta ? (
          <>
            <em className="mercato__silenzio">Nessun pronostico</em>
            <span className="mercato__prova">
              {vesteSilenzio(fixture).etichetta.toLowerCase()}
            </span>
          </>
        ) : (
          <>
            <span className="mercato__etichetta">
              {/* Mai troncare il nome del mercato: è il contenuto. */}
              <span className="mercato__nome">{fixture.prediction.label}</span>
              <span className="chip chip--riga chip--vuoto">
                {TESTO_PROVENIENZA_RIGA[fixture.source]}
              </span>
              {tag ? <span className="tag">{tag}</span> : null}
            </span>

            {/* IL DATO DI FASCIA — «avverati 92 su 100». È ciò che rende il
                pronostico verificabile, e resta nella riga accanto ad esso.
                A partita conclusa cede il posto all'esito: due righe di mono
                sotto lo stesso pronostico si annullerebbero a vicenda, e
                com'è finita batte com'era andata in passato. */}
            {fixture.result ? null : prova ? (
              <span className="mercato__prova">{prova}</span>
            ) : null}
          </>
        )}

        {/* Esito a partita conclusa: parola + glifo + colore, mai il colore
            da solo. Le righe concluse restano a piena opacità. */}
        {fixture.result ? (
          <span
            className={`riga-partita__esito ${
              fixture.outcome === 1
                ? 'esito-uscito'
                : fixture.outcome === 0
                  ? 'esito-non-uscito'
                  : ''
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

      <span className="riga-partita__cifra">
        {muta ? (
          <span className="riga-partita__glifo" aria-hidden="true">
            {vesteSilenzio(fixture).glifo}
          </span>
        ) : (
          <>
            <span className="cifra-riga">{suCento(fixture.prediction.p)}</span>
            <Misurino p={fixture.prediction.p} />
          </>
        )}
      </span>

      {muta ? (
        <Affidabilita p5={null} p95={null} />
      ) : (
        <Affidabilita p5={fixture.prediction.band_p5} p95={fixture.prediction.band_p95} />
      )}
    </a>
  );
}
