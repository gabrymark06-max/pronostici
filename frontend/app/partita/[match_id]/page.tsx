import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { Bandiera } from '@/components/Bandiera';
import { BarraProbabilita } from '@/components/BarraProbabilita';
import { BloccoRevisione } from '@/components/BloccoRevisione';
import { BloccoSilenzio } from '@/components/BloccoSilenzio';
import { ChipProvenienza } from '@/components/ChipProvenienza';
import { Crest } from '@/components/Crest';
import { QuadroNumeri, ragioniResidue } from '@/components/QuadroNumeri';
import { nomeCampionato } from '@/lib/campionati';
import {
  leggiAccuracy,
  leggiBacktest,
  leggiPartita,
  manifestoCrest,
  tutteLePartite,
} from '@/lib/dati';
import { recordDiFascia } from '@/lib/fascia';
import { dataLunga, decimale, ora, suCento, testoPulito } from '@/lib/formato';
import { famiglieAlternative, nomeFamiglia } from '@/lib/mercati';
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

  /* La description e' la definizione operativa: la frase che rende il numero
     falsificabile e' anche quella che descrive meglio la pagina. */
  const descrizione = tace(fixture)
    ? `Su ${fixture.home.name} — ${fixture.away.name} non abbiamo un pronostico. Abbiamo esaminato ${fixture.diagnostics.n_candidates} mercati: nessuno passa il nostro criterio.`
    : (righeDefinizione(fixture.prediction)[0] ?? titolo);

  return {
    title: titolo,
    description: descrizione,
    alternates: { canonical: `/partita/${fixture.match_id}/` },
    /* `siteName` va ripetuto qui: l'oggetto openGraph della pagina SOSTITUISCE
       quello della radice, non ci si fonde. */
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

  /* Le tre transizioni che cambiano stato stanno SOPRA LA PIEGA: e' la regola
     che impedisce di nasconderle. */
  const transizione = fixture.transition;
  const revisioneSopra =
    transizione != null && transizione !== 'first' && SOPRA_LA_PIEGA.includes(transizione);
  const revisioneSotto = transizione != null && transizione !== 'first' && !revisioneSopra;

  /* `reasons[0]` e' gia' comparso sopra la piega in DUE casi, e in nessuno dei
     due va ripetuto qui:
       - con una transizione e' la frase della revisione (schema.md);
       - su una partita in silenzio senza transizione e' il titolo del blocco
         di silenzio, perche' `vesteSilenzio` lo usa come tale.
     Senza questo controllo la scheda di un silenzio stampava la stessa frase
     due volte, a quattro centimetri di distanza.
     `ragioniResidue` toglie poi le voci che il quadro dei numeri mostra gia'
     come dato (i gol attesi) o che la riga di definizione dice gia' sopra la
     piega (la banda): il contenuto resta, la ripetizione no. Massimo tre. */
  const conTransizione = transizione != null && transizione !== 'first';
  const ragioni = ragioniResidue(
    conTransizione || tace(fixture) ? fixture.reasons.slice(1) : fixture.reasons,
    fixture.prediction,
  );

  const famiglie = famiglieAlternative(fixture);
  const conQuote = fixture.phase === 'definitive' && fixture.odds?.devig != null;

  /* SOTTO LA PIEGA PUO' NON ESSERCI NIENTE. Su un silenzio senza transizione,
     senza esito e senza mercati alternativi il blocco di silenzio e' tutta la
     pagina: la riga di taratura che apre la seconda parte non deve comparire
     ad aprire il vuoto. */
  const contenutoSotto =
    revisioneSopra ||
    revisioneSotto ||
    !tace(fixture) ||
    ragioni.length > 0 ||
    fixture.result != null ||
    famiglie.length > 0 ||
    conQuote;

  return (
    <>
      <div className="colonna colonna--scheda">
        {/* Nessun «torna al giorno» in cima: il ritorno e' il tasto indietro
            del browser, e la testata porta «Oggi». Una riga di navigazione
            sopra il titolo rimandava indietro chi era appena arrivato. */}
        <header className="scheda__testata">
          {/* Il contesto porta la bandiera del campionato: e' la stessa marca
              che identifica il blocco nella lista, quindi chi arriva da li'
              riconosce dove si trova prima di leggere. */}
          <p className="scheda__contesto">
            <Bandiera competizione={fixture.competition} />
            <span className="label">
              {nomeCampionato(fixture.competition)}
              {fixture.matchday != null ? ` · Giornata ${fixture.matchday}` : ''}
            </span>
            <span className="micro">
              {dataLunga(data)}, {ora(fixture.utc_date)}
            </span>
          </p>

          {/* Le squadre impilate, come nella lista ma con gli stemmi a 52px:
              la stessa forma a due scale. */}
          <h1 className="scheda__squadre">
            <span className="scheda__squadra">
              <Crest src={crest(fixture.home.crest)} tla={fixture.home.tla} grande />
              <span className="scheda__nome">{fixture.home.name}</span>
              <span className="scheda__lato">casa</span>
            </span>
            <span className="scheda__squadra">
              <Crest src={crest(fixture.away.crest)} tla={fixture.away.tla} grande />
              <span className="scheda__nome">{fixture.away.name}</span>
              <span className="scheda__lato">ospite</span>
            </span>
          </h1>
        </header>
      </div>

      {/* ---------- SOPRA LA PIEGA. L'ordine è vincolante. ----------
          Pronostico e silenzio stanno nella STESSA LASTRA, con la stessa riga
          di taratura, lo stesso padding e la stessa posizione: è lo stesso
          contenitore riempito diversamente. */}
      <div className="lastra lastra--scheda">
        <span className="taratura taratura--forte" aria-hidden="true" />
        <div className="colonna colonna--scheda">
          {tace(fixture) ? (
            <BloccoSilenzio fixture={fixture} />
          ) : (
            <section className="blocco" aria-labelledby="titolo-pronostico">
              <h2 id="titolo-pronostico" className="label">
                Il nostro pronostico
              </h2>

              {/* ① Il pronostico: `label` così com'è. Sono nomi di mercato
                  standard, già appresi: non si traducono e non si
                  abbelliscono. */}
              <p className="scheda__mercato">{fixture.prediction.label}</p>

              {/* ② La probabilità, con la riga di definizione operativa. */}
              <BarraProbabilita pronostico={fixture.prediction} />

              <div className="scheda__chip">
                <ChipProvenienza source={fixture.source} />
              </div>
            </section>
          )}
        </div>
      </div>

      {/* ---------- SOTTO LA PIEGA ----------
          Una sola riga di taratura alta apre la seconda parte del documento.
          Prima ce n'era una per blocco: ripetuta cinque volte smetteva di
          segnare un confine e diventava un motivo a righe, e i cinque blocchi
          pesavano tutti uguale. Qui il confine e' uno, e le sezioni sotto si
          separano con un filetto. */}
      <div className="colonna colonna--scheda">
        {contenutoSotto ? (
          <span className="taratura taratura--alta sotto-la-piega" aria-hidden="true" />
        ) : null}

        {revisioneSopra ? <BloccoRevisione fixture={fixture} /> : null}

        {/* IL QUADRO DEI NUMERI: gol attesi, record della fascia, lavoro
            fatto, e le sole ragioni che non siano gia' scritte altrove. */}
        {!tace(fixture) ? (
          <QuadroNumeri fixture={fixture} record={record} ragioni={ragioni} />
        ) : ragioni.length > 0 ? (
          <section className="sezione" aria-labelledby="titolo-perche">
            <h2 id="titolo-perche" className="label sezione__titolo">
              Perché
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

        {/* L'esito, quando c'è, sale sopra i mercati alternativi. */}
        {fixture.result ? <Esito fixture={fixture} /> : null}

        {famiglie.length > 0 ? (
          <section className="sezione" aria-labelledby="titolo-famiglie">
            <h2 id="titolo-famiglie" className="label sezione__titolo">
              Altre famiglie di mercato
            </h2>
            {/* La riga «le calcoliamo tutte, ma ne consigliamo una sola» sta
                nel quadro qui sopra, con il numero accanto. Qui sarebbe la
                stessa frase per la terza volta nella stessa schermata. */}
            <div className="famiglie">
              {famiglie.map((gruppo) => (
                /* <details> nativi: funzionano senza JavaScript, sono
                   raggiungibili da tastiera, e il contenuto è nel DOM per i
                   crawler. Chiusi di default: mostrarli aperti
                   riconsegnerebbe all'utente l'argmax che abbiamo tolto di
                   mezzo. */
                <details className="famiglia" key={gruppo.famiglia}>
                  <summary className="famiglia__somma">
                    <span>{nomeFamiglia(gruppo.famiglia)}</span>
                    <span className="famiglia__freccia" aria-hidden="true">
                      ›
                    </span>
                  </summary>
                  <div className="famiglia__corpo">
                    {/* Nessuna barra qui: la barra resta il linguaggio del
                        solo mercato consigliato. */}
                    {gruppo.mercati.map((mercato) => (
                      <p className="mercato-riga" key={mercato.key}>
                        <span>{mercato.label}</span>
                        <span className="mercato-riga__p">{suCento(mercato.p)} su 100</span>
                      </p>
                    ))}
                  </div>
                </details>
              ))}
            </div>
          </section>
        ) : null}

        {/* Le probabilità grezze NON compaiono su una scheda con pronostico.
            Sono previste solo sotto un silenzio: lì spiegano cosa sappiamo pur
            non consigliando. Qui sarebbero un cimitero di numeri che invita a
            rifare l'argmax — e i gol attesi sono già in `reasons`. */}

        {/* Le quote: solo in fase definitiva, in decimale, mai accanto al
            pronostico e mai con un link o un nome di operatore in evidenza. */}
        {conQuote && fixture.odds?.devig ? (
          <section className="sezione" aria-labelledby="titolo-quote">
            <h2 id="titolo-quote" className="label sezione__titolo">
              Quote di mercato, sgonfiate
            </h2>
            <div className="scorrevole">
              <table className="tabella">
                <caption>
                  Il margine tolto dalle quote di {fixture.odds.n_bookmakers ?? '—'} operatori.
                  Le usiamo per il confronto, non le pubblicizziamo.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Mercato</th>
                    <th scope="col">Margine rilevato</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(fixture.odds.devig).map(([chiave, valore]) => (
                    <tr key={chiave}>
                      <th scope="row">{chiave}</th>
                      <td className="num">{decimale(valore, 3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
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
      className={`sezione ${uscito ? 'esito--uscito' : 'esito--non-uscito'}`}
      aria-labelledby="titolo-esito"
    >
      <h2 id="titolo-esito" className="label sezione__titolo">
        Com’è finita
      </h2>
      <div className="esito">
        <span className="esito__punteggio">
          {fixture.result.home}–{fixture.result.away}
        </span>
        {noto && !tace(fixture) ? (
          <span className="esito__verdetto">
            Il nostro pronostico {fixture.prediction.label}{' '}
            {uscito ? 'è uscito' : 'non è uscito'}{' '}
            <span className="esito__marca" aria-hidden="true">
              {uscito ? '▪' : '▫'}
            </span>
          </span>
        ) : null}
      </div>
    </section>
  );
}
