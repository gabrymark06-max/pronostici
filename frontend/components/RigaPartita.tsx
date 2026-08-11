import { fraseCortaDiFascia, type RecordFascia } from '@/lib/fascia';
import { attributoOra, ora, suCento } from '@/lib/formato';
import { formattaQuota, posizioneTacca, quoteDelPronostico } from '@/lib/quote';
import { TAG_LISTA, vesteSilenzio } from '@/lib/testi';
import { tace, type Fixture } from '@/lib/tipi';

import { Crest } from './Crest';
import { Misurino } from './Misurino';

/**
 * LA RIGA DI PARTITA — il cuore del prodotto.
 *
 * Un `<a>` che avvolge l'intera riga, su una griglia a COLONNE FISSE
 * nell'ordine in cui si legge un tabellone:
 *
 *   ora · squadre · pronostico · probabilità · quota
 *
 * Le colonne si incolonnano lungo tutta la lista: scorrere la pagina diventa
 * un confronto invece che quaranta letture separate. È la meccanica dei siti
 * di risultati, ed è l'unica cosa che se ne prende — nessun marchio, nessun
 * logotipo, nessuna identità visiva di terzi.
 *
 * LE DUE QUOTE, e perché sono due.
 *  · LA QUOTA EQUA (grande) è `1/probabilità`. C'è sempre, su ogni mercato,
 *    perché è solo un'altra forma del numero che mostriamo già. Dice: sotto
 *    questo prezzo la scommessa non conviene.
 *  · LA QUOTA DI MERCATO (piccola, sotto) è il prezzo lordo del consenso degli
 *    operatori. Esiste solo su 1X2 e Over/Under e solo dove il budget delle
 *    quote ha permesso una chiamata: sulla maggior parte delle righe non c'è,
 *    e la riga deve reggere l'assenza senza sembrare rotta. Per questo è la
 *    quota equa a occupare la posizione grande, e non il contrario.
 *
 * ALTEZZA 64px ESATTI da 768px in su, e il bersaglio COINCIDE con la riga. Non
 * 56px con un `::after` che sborda: due righe adiacenti che sbordano di 4px si
 * contendono 8px di banda, e il clic in quella banda finisce sulla riga
 * sbagliata. Un bersaglio ambiguo è peggio di uno piccolo.
 *
 * Sotto i 768px la riga passa a due livelli (92px) dentro la stessa griglia,
 * con `grid-template-areas`: un cambio di forma dichiarato, non un
 * rimescolamento. Cinque colonne a 360px si otterrebbero solo troncando il
 * nome del mercato, che è il contenuto e non si tronca mai.
 *
 * IL SILENZIO ha la STESSA ALTEZZA e lo STESSO PESO di una riga con
 * pronostico. La differenza è di FORMA, non di tinta: glifo matematico contro
 * cifra, corsivo contro tondo. Le colonne non restano mai vuote — se si
 * svuotassero, il silenzio tornerebbe a leggersi come un buco in una lista
 * fitta, che è esattamente il contrario di quello che è.
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
  const quote = quoteDelPronostico(fixture);
  const conclusa = fixture.result != null;

  return (
    <a className="riga" href={`/partita/${fixture.match_id}/`}>
      <time className="riga__ora" dateTime={attributoOra(fixture.utc_date)}>
        {ora(fixture.utc_date)}
      </time>

      <span className="squadre">
        <span className="squadra">
          <Crest src={crest(fixture.home.crest)} tla={fixture.home.tla} />
          <span className="squadra__nome" title={fixture.home.name}>
            {fixture.home.name}
          </span>
          {conclusa ? <span className="squadra__gol">{fixture.result?.home}</span> : null}
        </span>
        <span className="squadra">
          <Crest src={crest(fixture.away.crest)} tla={fixture.away.tla} />
          <span className="squadra__nome" title={fixture.away.name}>
            {fixture.away.name}
          </span>
          {conclusa ? <span className="squadra__gol">{fixture.result?.away}</span> : null}
        </span>
      </span>

      <span className="riga__mercato">
        {muta ? (
          <>
            <em className="mercato__silenzio">Nessun pronostico</em>
            <span className="mercato__prova">
              {vesteSilenzio(fixture).etichetta.toLowerCase()}
            </span>
          </>
        ) : (
          <>
            <span className="mercato__testa">
              {/* Mai troncare il nome del mercato: è il contenuto. */}
              <span className="mercato__nome">{fixture.prediction.label}</span>
              {tag ? <span className="tag">{tag}</span> : null}
            </span>

            {/* A partita conclusa l'esito prende il posto del dato di fascia:
                due righe minute sotto lo stesso pronostico si annullerebbero a
                vicenda, e com'è finita batte com'era andata in passato. */}
            {conclusa ? (
              <span
                className={`esito-riga ${
                  fixture.outcome === 1
                    ? 'esito-riga--uscito'
                    : fixture.outcome === 0
                      ? 'esito-riga--mancato'
                      : ''
                }`}
              >
                {fixture.outcome === 1 ? (
                  <>
                    <span aria-hidden="true">◤</span> uscito
                  </>
                ) : fixture.outcome === 0 ? (
                  <>
                    <span aria-hidden="true">◇</span> non uscito
                  </>
                ) : (
                  'partita conclusa'
                )}
              </span>
            ) : prova ? (
              <span className="mercato__prova">{prova}</span>
            ) : null}
          </>
        )}
      </span>

      <span className="riga__cifra">
        {muta ? (
          <span className="riga__glifo" aria-hidden="true">
            {vesteSilenzio(fixture).glifo}
          </span>
        ) : (
          <>
            <span className="cifra-riga">{suCento(fixture.prediction.p)}</span>
            <span className="riga__suCento" aria-hidden="true">
              su 100
            </span>
          </>
        )}
      </span>

      {/* LA BARRA PRENDE LO SPAZIO CHE AVANZA.
          Da 768px in su fra il pronostico e la cifra restavano quattrocento
          pixel di niente: la riga si leggeva come due gruppi lontani invece che
          come una riga. La barra occupa quella luce e ci mette dentro
          un'informazione — la probabilita' e, quando c'e', la tacca del
          mercato. Sotto i 768px scende a fondo riga, a piena larghezza. */}
      <span className="riga__barra">
        {muta ? null : (
          <Misurino p={fixture.prediction.p} mercato={quote ? posizioneTacca(quote) : null} />
        )}
      </span>

      <span className="riga__quota">
        {muta || !quote ? (
          <span className="quota__vuoto" aria-hidden="true">
            —
          </span>
        ) : (
          <>
            <span className="quota__valore">{formattaQuota(quote.equa)}</span>
            <span className="quota__nota">
              {quote.mercato !== null ? (
                <>
                  mercato <strong>{formattaQuota(quote.mercato)}</strong>
                </>
              ) : (
                'equa'
              )}
            </span>
            <span className="solo-lettori">
              Quota equa {formattaQuota(quote.equa)}
              {quote.mercato !== null
                ? `. Il mercato paga ${formattaQuota(quote.mercato)}.`
                : '. Questo mercato non è quotato dalla nostra fonte.'}
            </span>
          </>
        )}
      </span>
    </a>
  );
}
