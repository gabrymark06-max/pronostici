import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { BarraProbabilita } from '@/components/BarraProbabilita';
import { BloccoRevisione } from '@/components/BloccoRevisione';
import { BloccoSilenzio } from '@/components/BloccoSilenzio';
import { ChipProvenienza } from '@/components/ChipProvenienza';
import { Crest } from '@/components/Crest';
import { RigaFascia } from '@/components/RigaFascia';
import { leggiAccuracy, leggiBacktest, leggiPartita, manifestoCrest, tutteLePartite } from '@/lib/dati';
import { recordDiFascia } from '@/lib/fascia';
import { dataLunga, decimale, ora, suCento, testoPulito } from '@/lib/formato';
import { famiglieAlternative, nomeFamiglia } from '@/lib/mercati';
import { nomeCompetizione, righeDefinizione, SOPRA_LA_PIEGA } from '@/lib/testi';
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

  /* Le tre transizioni che cambiano stato stanno SOPRA LA PIEGA: è la regola
     che impedisce di nasconderle. Le altre due vanno sotto la fascia storica. */
  const transizione = fixture.transition;
  const revisioneSopra =
    transizione != null && transizione !== 'first' && SOPRA_LA_PIEGA.includes(transizione);
  const revisioneSotto = transizione != null && transizione !== 'first' && !revisioneSopra;

  /* Se transition ≠ first, reasons[0] è già la frase della transizione e
     compare nel blocco di revisione: qui non va duplicata. Massimo tre voci. */
  const ragioni = (
    transizione && transizione !== 'first' ? fixture.reasons.slice(1) : fixture.reasons
  ).slice(0, 3);

  const famiglie = famiglieAlternative(fixture);

  return (
    <div className="colonna colonna--scheda">
      <p>
        <a className="scheda__ritorno" href={`/giorno/${data}/`}>
          <span aria-hidden="true">‹</span> Torna a {dataLunga(data)}
        </a>
      </p>

      <header className="scheda__testata">
        <h1 className="scheda__squadre">
          <Crest src={crest(fixture.home.crest)} tla={fixture.home.tla} />
          {fixture.home.name}
          <span aria-hidden="true">—</span>
          {fixture.away.name}
          <Crest src={crest(fixture.away.crest)} tla={fixture.away.tla} />
        </h1>
        <p className="label scheda__contesto">
          {nomeCompetizione(fixture.competition)}
          {fixture.matchday != null ? ` · giornata ${fixture.matchday}` : ''} · {dataLunga(data)},{' '}
          {ora(fixture.utc_date)}
        </p>
      </header>

      {/* ---------- SOPRA LA PIEGA. L'ordine è vincolante. ---------- */}
      {tace(fixture) ? (
        <BloccoSilenzio fixture={fixture} />
      ) : (
        <section className="blocco" aria-labelledby="titolo-pronostico">
          <h2 id="titolo-pronostico" className="label">
            Il nostro pronostico
          </h2>

          {/* ① Il pronostico: `label` così com'è. Sono nomi di mercato standard,
              già appresi: non si traducono e non si abbelliscono. */}
          <p className="scheda__mercato">{fixture.prediction.label}</p>

          {/* ② La probabilità, con la riga di definizione operativa. */}
          <BarraProbabilita pronostico={fixture.prediction} />

          <div className="scheda__chip">
            <ChipProvenienza source={fixture.source} />
          </div>
        </section>
      )}

      {revisioneSopra ? <BloccoRevisione fixture={fixture} /> : null}

      {/* ③ Il record di fascia. */}
      {!tace(fixture) ? <RigaFascia record={record} /> : null}

      {revisioneSotto ? <BloccoRevisione fixture={fixture} /> : null}

      {/* ④ Le ragioni: elenco corto, mai un paragrafo di prosa. */}
      {ragioni.length > 0 ? (
        <section className="sezione" aria-labelledby="titolo-perche">
          <h2 id="titolo-perche" className="label">
            Perché
          </h2>
          <ul className="ragioni">
            {ragioni.map((ragione) => (
              <li key={ragione}>{testoPulito(ragione)}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* ---------- SOTTO LA PIEGA ---------- */}

      {/* L'esito, quando c'è, sale sopra i mercati alternativi. */}
      {fixture.result ? <Esito fixture={fixture} /> : null}

      {famiglie.length > 0 ? (
        <section className="sezione--pesante" aria-labelledby="titolo-famiglie">
          <h2 id="titolo-famiglie" className="label">
            Altre famiglie di mercato
          </h2>
          <p className="micro" style={{ marginTop: 'var(--s-2)' }}>
            Le calcoliamo tutte, ma ne consigliamo una sola.
          </p>
          <div style={{ marginTop: 'var(--s-3)' }}>
            {famiglie.map((gruppo) => (
              /* <details> nativi: funzionano senza JavaScript, sono
                 raggiungibili da tastiera, e il contenuto è nel DOM per i
                 crawler. Chiusi di default: mostrarli aperti riconsegnerebbe
                 all'utente l'argmax che abbiamo tolto di mezzo. */
              <details className="famiglia" key={gruppo.famiglia}>
                <summary className="famiglia__somma">
                  <span>{nomeFamiglia(gruppo.famiglia)}</span>
                  <span className="famiglia__freccia" aria-hidden="true">
                    ›
                  </span>
                </summary>
                <div className="famiglia__corpo">
                  {/* Nessuna barra qui: la barra resta il linguaggio del solo
                      mercato consigliato. Solo cifre mono tabellari. */}
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
          Sono previste solo sotto un silenzio (MASTER §5.2): lì spiegano cosa
          sappiamo pur non consigliando. Qui sarebbero un cimitero di numeri
          che invita a rifare l'argmax — e i gol attesi sono già in `reasons`. */}

      {/* Le quote: solo in fase definitiva, in decimale, mai accanto al
          pronostico e mai con un link o un nome di bookmaker in evidenza. */}
      {fixture.phase === 'definitive' && fixture.odds?.devig ? (
        <section className="sezione" aria-labelledby="titolo-quote">
          <h2 id="titolo-quote" className="label">
            Quote di mercato, sgonfiate
          </h2>
          <div className="scorrevole">
            <table className="tabella">
              <caption>
                Il margine tolto dalle quote di {fixture.odds.n_bookmakers ?? '—'} operatori. Le
                usiamo per il confronto, non le pubblicizziamo.
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
          <p className="micro quote__nota">
            <a href="/come-funziona/#quote">Da dove vengono le quote →</a>
          </p>
        </section>
      ) : null}

      <section className="sezione" aria-label="Il nostro record">
        <p className="corpo">
          <a href="/come-stiamo-andando/">
            Tutti i nostri pronostici, con quanti ne abbiamo presi →
          </a>
        </p>
      </section>
    </div>
  );
}

/** Esito a partita conclusa: parola + glifo + colore, mai il colore da solo. */
function Esito({ fixture }: { fixture: Fixture }) {
  if (!fixture.result) return null;
  const uscito = fixture.outcome === 1;
  const noto = fixture.outcome === 1 || fixture.outcome === 0;

  return (
    <section
      className={`sezione--pesante esito-blocco ${uscito ? 'esito--uscito' : 'esito--non-uscito'}`}
      aria-labelledby="titolo-esito"
    >
      <h2 id="titolo-esito" className="label">
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
