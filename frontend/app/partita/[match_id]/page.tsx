import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { Bandiera } from '@/components/Bandiera';
import { BarraProbabilita } from '@/components/BarraProbabilita';
import { BloccoRevisione } from '@/components/BloccoRevisione';
import { BloccoSilenzio } from '@/components/BloccoSilenzio';
import { ChipProvenienza } from '@/components/ChipProvenienza';
import { Crest } from '@/components/Crest';
import { QuadroNumeri, ragioniResidue } from '@/components/QuadroNumeri';
import { TuttiIPronostici } from '@/components/TuttiIPronostici';
import { nomeCampionato } from '@/lib/campionati';
import {
  leggiAccuracy,
  leggiBacktest,
  leggiPartita,
  manifestoCrest,
  tutteLePartite,
} from '@/lib/dati';
import { recordDiFascia } from '@/lib/fascia';
import { dataLunga, ora, testoPulito } from '@/lib/formato';
import { formattaQuota, fraseConfronto, quoteDelPronostico } from '@/lib/quote';
import { MARCHIO, righeDefinizione, SOPRA_LA_PIEGA } from '@/lib/testi';
import { tace, type Fixture } from '@/lib/tipi';

export function generateStaticParams() {
  return [...tutteLePartite().keys()].map((id) => ({ match_id: String(id) }));
}

export const dynamicParams = false;

type Props = { params: Promise<{ match_id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { match_id } = await params;
  const trovata = leggiPartita(Number(match_id));
  if (!trovata) return { title: 'Partita' };

  const { fixture } = trovata;
  const titolo = `${fixture.home.name} — ${fixture.away.name}: il nostro pronostico`;

  /* La description è la definizione operativa: la frase che rende il numero
     falsificabile è anche quella che descrive meglio la pagina. */
  const descrizione = tace(fixture)
    ? `Su ${fixture.home.name} — ${fixture.away.name} non abbiamo un pronostico. Abbiamo esaminato ${fixture.diagnostics.n_candidates} mercati: nessuno passa il nostro criterio.`
    : (righeDefinizione(fixture.prediction)[0] ?? titolo);

  return {
    title: titolo,
    description: descrizione,
    alternates: { canonical: `/partita/${fixture.match_id}/` },
    openGraph: {
      title: titolo,
      description: descrizione,
      type: 'article',
      locale: 'it_IT',
      siteName: MARCHIO,
    },
  };
}

export default async function PaginaPartita({ params }: Props) {
  const { match_id } = await params;
  const trovata = leggiPartita(Number(match_id));
  if (!trovata) notFound();

  const { fixture, data } = trovata;
  const manifesto = manifestoCrest();
  const crest = (url: string | null) => (url ? (manifesto[url] ?? url) : null);

  const accuracy = leggiAccuracy();
  const backtest = leggiBacktest();
  const record = tace(fixture) ? null : recordDiFascia(fixture.prediction.p, accuracy, backtest);
  const quote = quoteDelPronostico(fixture);

  /* Le tre transizioni che cambiano stato stanno SOPRA LA PIEGA: è la regola
     che impedisce di nasconderle. */
  const transizione = fixture.transition;
  const revisioneSopra =
    transizione != null && transizione !== 'first' && SOPRA_LA_PIEGA.includes(transizione);
  const revisioneSotto = transizione != null && transizione !== 'first' && !revisioneSopra;

  /* `reasons[0]` è già comparso sopra la piega in due casi — con una
     transizione è la frase della revisione, su un silenzio è il titolo del
     blocco — e in nessuno dei due va ripetuto qui. `ragioniResidue` toglie poi
     ciò che il quadro dei numeri mostra già come dato. */
  const conTransizione = transizione != null && transizione !== 'first';
  const ragioni = ragioniResidue(
    conTransizione || tace(fixture) ? fixture.reasons.slice(1) : fixture.reasons,
    fixture.prediction,
  );

  const conclusa = fixture.result != null;

  return (
    <>
      {/* ---------------------------------------------------------------- */}
      {/* LA TESTA DELLA PARTITA                                            */}
      {/* ---------------------------------------------------------------- */}
      <div className="lastra lastra--testa">
        <div className="colonna colonna--scheda">
          <p className="partita__contesto">
            <Bandiera competizione={fixture.competition} />
            <span className="label">
              {nomeCampionato(fixture.competition)}
              {fixture.matchday != null ? ` · Giornata ${fixture.matchday}` : ''}
            </span>
            <span className="partita__quando">
              {dataLunga(data)}, {ora(fixture.utc_date)}
            </span>
          </p>

          <h1 className="partita__squadre">
            <span className="partita__squadra">
              <Crest src={crest(fixture.home.crest)} tla={fixture.home.tla} grande />
              <span className="partita__nome">{fixture.home.name}</span>
              {conclusa ? (
                <span className="partita__gol">{fixture.result?.home}</span>
              ) : (
                <span className="partita__lato">casa</span>
              )}
            </span>
            <span className="partita__squadra">
              <Crest src={crest(fixture.away.crest)} tla={fixture.away.tla} grande />
              <span className="partita__nome">{fixture.away.name}</span>
              {conclusa ? (
                <span className="partita__gol">{fixture.result?.away}</span>
              ) : (
                <span className="partita__lato">ospite</span>
              )}
            </span>
          </h1>
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* IL PRONOSTICO (o il silenzio). L'ordine è vincolante.             */}
      {/* ---------------------------------------------------------------- */}
      <div className="lastra lastra--pronostico">
        <div className="colonna colonna--scheda">
          {tace(fixture) ? (
            <BloccoSilenzio fixture={fixture} />
          ) : (
            <section className="blocco" aria-labelledby="titolo-pronostico">
              <h2 id="titolo-pronostico" className="label">
                <span className="bersaglio" aria-hidden="true" /> Il nostro pronostico
              </h2>

              {/* ① Il pronostico: `label` così com'è. Sono nomi di mercato
                  standard, già appresi altrove: non si traducono e non si
                  abbelliscono. */}
              <p className="partita__mercato">{fixture.prediction.label}</p>

              {/* ② La probabilità, con la riga di definizione operativa. */}
              <BarraProbabilita pronostico={fixture.prediction} />

              {/* ③ Le quote. La equa c'è sempre; quella di mercato quasi mai,
                  e quando c'è porta il confronto in parole. */}
              {quote ? (
                <div className="quote">
                  <div className="quote__cella">
                    <p className="label">Quota equa</p>
                    <p className="quote__valore">{formattaQuota(quote.equa)}</p>
                    <p className="quote__nota">
                      È 1 diviso la probabilità. Sotto questo prezzo la scommessa perde
                      valore, sopra lo guadagna.
                    </p>
                  </div>

                  <div className="quote__cella">
                    <p className="label">Quota di mercato</p>
                    {quote.mercato !== null ? (
                      <>
                        <p className="quote__valore">{formattaQuota(quote.mercato)}</p>
                        <p className="quote__nota">{fraseConfronto(quote)}</p>
                      </>
                    ) : (
                      <>
                        <p className="quote__valore quote__valore--assente" aria-hidden="true">
                          —
                        </p>
                        <p className="quote__nota">
                          La nostra fonte gratuita di quote copre solo esito finale e
                          over/under. Su questo tipo di scommessa non abbiamo un prezzo, e
                          non ne inventiamo uno.
                        </p>
                      </>
                    )}
                  </div>
                </div>
              ) : null}

              <div className="partita__chip">
                <ChipProvenienza source={fixture.source} />
              </div>
            </section>
          )}
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* IL RESTO                                                          */}
      {/* ---------------------------------------------------------------- */}
      <div className="colonna colonna--scheda">
        {revisioneSopra ? <BloccoRevisione fixture={fixture} /> : null}

        {/* L'esito, quando c'è, sta prima di tutto il resto: com'è finita batte
            come ci siamo arrivati. */}
        {conclusa ? <Esito fixture={fixture} /> : null}

        {/* IL QUADRO DEI NUMERI: gol attesi, record della fascia, lavoro fatto,
            e le sole ragioni che non siano già scritte altrove. */}
        {!tace(fixture) ? (
          <QuadroNumeri fixture={fixture} record={record} ragioni={ragioni} />
        ) : ragioni.length > 0 ? (
          <section className="sezione" aria-labelledby="titolo-perche">
            <h2 id="titolo-perche" className="label sezione__titolo">
              <span className="bersaglio" aria-hidden="true" /> Perché
            </h2>
            <ul className="ragioni">
              {ragioni.map((ragione) => (
                <li key={ragione}>
                  <span>{testoPulito(ragione)}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {revisioneSotto ? <BloccoRevisione fixture={fixture} /> : null}

        <TuttiIPronostici fixture={fixture} />
      </div>
    </>
  );
}

/** Esito a partita conclusa: parola + glifo + colore, mai il colore da solo. */
function Esito({ fixture }: { fixture: Fixture }) {
  if (!fixture.result) return null;
  const uscito = fixture.outcome === 1;
  const noto = fixture.outcome === 1 || fixture.outcome === 0;

  return (
    <section
      className={`sezione esito ${uscito ? 'esito--uscito' : 'esito--mancato'}`}
      aria-labelledby="titolo-esito"
    >
      <h2 id="titolo-esito" className="label sezione__titolo">
        Com’è finita
      </h2>
      <p className="esito__punteggio">
        {fixture.result.home}–{fixture.result.away}
      </p>
      {noto && !tace(fixture) ? (
        <p className="esito__verdetto">
          <span className="esito__marca" aria-hidden="true">
            {uscito ? '◤' : '◇'}
          </span>{' '}
          Il nostro pronostico <strong>{fixture.prediction.label}</strong>{' '}
          {uscito ? 'è uscito' : 'non è uscito'}.
        </p>
      ) : null}
    </section>
  );
}
