import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { AvvisoOverUnder } from '@/components/AvvisoOverUnder';
import { Bandiera } from '@/components/Bandiera';
import { BloccoArbitro } from '@/components/BloccoArbitro';
import { CosaManca } from '@/components/CosaManca';
import { CampoFormazioni } from '@/components/CampoFormazioni';
import { QuoteEstese } from '@/components/QuoteEstese';
import { SezioneGiocatori } from '@/components/SezioneGiocatori';
import { BarraProbabilita } from '@/components/BarraProbabilita';
import { BloccoRevisione } from '@/components/BloccoRevisione';
import { BloccoSilenzio } from '@/components/BloccoSilenzio';
import { ChipProvenienza } from '@/components/ChipProvenienza';
import { Crest } from '@/components/Crest';
import { QuadroNumeri, ragioniResidue } from '@/components/QuadroNumeri';
import { TuttiIPronostici } from '@/components/TuttiIPronostici';
import { titoloCompetizione } from '@/lib/campionati';
import {
  leggiAccuracy,
  leggiBacktest,
  leggiPartita,
  manifestoCrest,
  tutteLePartite,
} from '@/lib/dati';
import { recordDiFascia } from '@/lib/fascia';
import { dataLunga, ora, testoPulito } from '@/lib/formato';
import {
  formattaQuota,
  fraseConfronto,
  fraseSportello,
  quoteDelPronostico,
} from '@/lib/quote';
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
              {titoloCompetizione(fixture.competition, fixture.stage)}
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

              {fixture.prediction.family === 'over_under' ? <AvvisoOverUnder /> : null}

              {/* ② La probabilità, con la riga di definizione operativa. */}
              <BarraProbabilita pronostico={fixture.prediction} />

              {/* ③ LE DUE QUOTE, PARI A PARI. La nostra c'è sempre; quella del
                  mercato c'è sugli undici mercati che le quote determinano in
                  modo esatto. Il confronto è fra due quote EQUE — la loro col
                  margine tolto — perché confrontare la nostra quota equa con
                  un prezzo lordo farebbe sembrare il mercato sistematicamente
                  piu' avaro di quanto sia. Il prezzo lordo compare sotto, come
                  terza riga, quando lo conosciamo: e' l'unico dei tre numeri
                  che qualcuno puo' davvero giocare. */}
              {quote ? (
                <div className="quote">
                  <div className="quote__cella">
                    <p className="label">La nostra quota equa</p>
                    <p className="quote__valore">{formattaQuota(quote.nostra)}</p>
                    <p className="quote__nota">
                      È 1 diviso la probabilità che diamo noi. Sotto questo prezzo la
                      scommessa perde valore, sopra lo guadagna.
                    </p>
                  </div>

                  <div className="quote__cella">
                    <p className="label">La stessa, secondo il mercato</p>
                    {quote.mercato !== null ? (
                      <>
                        <p className="quote__valore">{formattaQuota(quote.mercato)}</p>
                        <p className="quote__nota">{fraseConfronto(quote)}</p>
                        {quote.prezzo !== null ? (
                          <p className="quote__nota quote__nota--sportello">
                            {fraseSportello(quote)}
                          </p>
                        ) : null}
                      </>
                    ) : (
                      <>
                        <p className="quote__valore quote__valore--assente" aria-hidden="true">
                          —
                        </p>
                        <p className="quote__nota">
                          Le quote gratuite che leggiamo — esito finale e over/under —
                          determinano in modo esatto undici scommesse, e questa non è fra
                          quelle. Un numero derivato per somiglianza sarebbe inventato, e
                          non lo inventiamo.
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

        {/* LA BARRA DEI BLOCCHI.
            Sotto il pronostico la scheda è diventata lunga: mercati, campo,
            arbitro, quote di un'altra fonte, giocatori. Scorrerla tutta per
            capire cosa c'è dentro è il modo peggiore di scoprirlo.
            Questi sono ancoraggi, non schede: nessun JavaScript, ogni blocco
            resta nella pagina e raggiungibile, e chi arriva da una ricerca
            trova il testo comunque. Le voci compaiono solo se il blocco che
            indicano esiste per QUESTA partita — una voce che porta al vuoto è
            peggio di una voce in meno. */}
        {(() => {
          const voci: { id: string; testo: string }[] = [
            { id: 'pronostici', testo: 'Tutti i mercati' },
          ];
          if (fixture.sofascore?.formazioni) voci.push({ id: 'formazioni', testo: 'Formazioni' });
          if (fixture.sofascore?.arbitro) voci.push({ id: 'arbitro', testo: 'Arbitro' });
          if (fixture.sofascore?.quote?.mercati?.length)
            voci.push({ id: 'altri-mercati', testo: 'Altri mercati' });
          if (fixture.sofascore?.giocatori) voci.push({ id: 'giocatori', testo: 'Giocatori' });
          if (voci.length < 2) return null;
          return (
            <nav className="blocchi" aria-label="I blocchi di questa partita">
              <ul className="blocchi__lista">
                {voci.map((v) => (
                  <li key={v.id}>
                    <a className="blocchi__voce" href={`#${v.id}`}>
                      {v.testo}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          );
        })()}

        <TuttiIPronostici fixture={fixture} />

        {/* IL CONTORNO, DOPO I PRONOSTICI E MAI PRIMA. Arbitro e mercati di
            un'altra fonte sono informazione utile, non nostre stime: stanno
            sotto tutto cio' su cui ci facciamo misurare, cosi' l'ordine della
            pagina dice da solo che peso hanno. */}
        {fixture.sofascore?.formazioni ? (
          <CampoFormazioni
            formazioni={fixture.sofascore.formazioni}
            casa={fixture.home.name}
            ospiti={fixture.away.name}
            siglaCasa={fixture.home.tla}
            siglaOspiti={fixture.away.tla}
          />
        ) : null}

        {fixture.sofascore?.arbitro ? (
          <BloccoArbitro
            arbitro={fixture.sofascore.arbitro}
            stadio={fixture.sofascore.stadio}
          />
        ) : null}

        {fixture.sofascore?.quote?.mercati?.length ? (
          <QuoteEstese mercati={fixture.sofascore.quote.mercati} />
        ) : null}

        {fixture.sofascore?.giocatori ? (
          <SezioneGiocatori
            stime={fixture.sofascore.giocatori}
            casa={fixture.home.name}
            ospiti={fixture.away.name}
          />
        ) : null}

        {/* IN FONDO, e non in cima: e' un'assenza, e un'assenza non deve
            prendere il posto di quello che c'e'. Chi scorre trova prima tutto
            il contorno disponibile e poi la spiegazione di cosa manca. */}
        <CosaManca fixture={fixture} />
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
