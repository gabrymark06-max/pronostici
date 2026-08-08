import type { Metadata } from 'next';

import { ChipProvenienza } from '@/components/ChipProvenienza';
import { leggiBacktest, leggiBudgetQuote } from '@/lib/dati';
import { dataConAnno, decimale, intero, percentuale } from '@/lib/formato';
import { GIOCO_RESPONSABILE, REPO } from '@/lib/testi';

export const metadata: Metadata = {
  title: 'Come funziona',
  description:
    'Il criterio con cui scegliamo un pronostico per partita, perché a volte non diciamo niente, la tabella dei parametri e il protocollo scritto prima dei numeri.',
  alternates: { canonical: '/come-funziona/' },
};

const SPIEGAZIONE: Record<string, string> = {
  p_min: 'la probabilità sotto la quale non consigliamo, qualunque cosa dica il modello',
  sigma_max: 'quanto può oscillare una stima prima che la scartiamo',
  s_min_in_code: 'quanta informazione in più deve portare un mercato per meritare un consiglio',
  model_weight: 'quanto pesa la nostra stima quando non ci sono quote',
  tau: 'di quanto riportiamo verso la media le stime incerte',
  draws: 'quante simulazioni facciamo per stimare la banda di incertezza',
  half_life_days: 'dopo quanti giorni una partita passata conta la metà',
  window_days: 'quanti giorni di storia guardiamo',
  min_train_matches: 'quante partite servono prima di dire qualcosa su una squadra',
  step_days: 'ogni quanti giorni riadattiamo il modello',
  rho_max: 'il tetto alla correzione sui punteggi bassi',
};

const MAI_TOCCATO = new Set(['p_min', 'sigma_max']);

const SEZIONI = [
  { id: 'criterio', titolo: 'Il criterio, in un paragrafo' },
  { id: 'silenzio', titolo: 'Perché a volte non diciamo niente' },
  { id: 'revisione', titolo: 'Le due versioni dello stesso pronostico' },
  { id: 'quote', titolo: 'Da dove vengono i dati, e le quote' },
  { id: 'parametri', titolo: 'La tabella dei parametri' },
  { id: 'protocollo', titolo: 'Il protocollo pre-registrato' },
  { id: 'cosa-non-facciamo', titolo: 'Cosa non facciamo' },
];

/**
 * DEROGA TIPOGRAFICA DICHIARATA: qui il corpo è Newsreader 19/1.7, non Public
 * Sans. Questa pagina è un articolo; le altre sono un bollettino. È densità
 * deliberata, non incoerenza — ed è l'unica pagina del prodotto che si legge
 * invece di consultarsi.
 */
export default function PaginaComeFunziona() {
  const backtest = leggiBacktest();
  const budget = leggiBudgetQuote();
  const parametri = Object.entries(backtest.parameters);
  const [bandaDa, bandaA] = backtest.silence.band;

  return (
    <div className="colonna colonna--prosa articolo">
      <h1 className="titolo-pagina">Come funziona</h1>

      {/* L'indice sta SOPRA il testo, in posizione statica: non è una colonna
          laterale, perché una colonna laterale è la forma di uno slot
          pubblicitario e il layout non deve avere il posto dove metterla. */}
      <nav className="indice" aria-label="Indice della pagina">
        <p className="label">In questa pagina</p>
        <ol>
          {SEZIONI.map((s) => (
            <li key={s.id}>
              <a href={`#${s.id}`}>{s.titolo}</a>
            </li>
          ))}
        </ol>
      </nav>

      <section id="criterio">
        <h2>Il criterio, in un paragrafo</h2>
        <p>
          Per ogni partita calcoliamo la probabilità di undici tipi di mercato a partire dalla
          stessa stima dei gol attesi. Poi cerchiamo quale di quei mercati dice qualcosa che la
          media del campionato — o le quote, quando ci sono — non dicono già. Fra i candidati non
          scegliamo quello con il vantaggio più grande: scegliamo quello che unisce un vantaggio
          reale a una probabilità alta di uscire davvero e a una stima in cui abbiamo fiducia. Se
          nessuno ce la fa, non diciamo niente.
        </p>
        <p className="definizione">
          Il criterio è scritto nel codice, in un repository pubblico. Chiunque può leggerlo e
          rieseguirlo.{' '}
          <a href={REPO} rel="noopener noreferrer" target="_blank">
            Il codice →
          </a>
        </p>
      </section>

      <section id="silenzio">
        <h2>Perché a volte non diciamo niente</h2>
        <p>
          Su circa una partita su quattro non pubblichiamo nessun pronostico. Non è un guasto e non
          è pigrizia: è il risultato di tre filtri che una stima deve superare per meritare di
          essere detta. Quando ne fallisce uno, quel che resta da dire è che non abbiamo niente da
          dire.
        </p>
        <p>
          Nel prodotto ogni silenzio porta il glifo del filtro che ha morso. Sono questi tre, e
          sono sempre gli stessi:
        </p>
        <ul className="legenda-glifi">
          <li>
            <span className="legenda-glifi__glifo" aria-hidden="true">
              ≈
            </span>
            <span>
              <span className="label">Non distinguibile</span> — quello che diciamo noi coincide
              quasi esattamente con quello che dice già la media del campionato, o con quello che
              dicono le quote. Ripeterlo non aggiungerebbe niente.
            </span>
          </li>
          <li>
            <span className="legenda-glifi__glifo" aria-hidden="true">
              ±
            </span>
            <span>
              <span className="label">Stima instabile</span> — la stessa stima oscilla troppo da
              una simulazione all’altra. Di solito succede quando su una delle due squadre abbiamo
              poche partite affidabili.
            </span>
          </li>
          <li>
            <span className="legenda-glifi__glifo" aria-hidden="true">
              &lt;
            </span>
            <span>
              <span className="label">Troppo improbabile</span> — quello che vediamo di diverso ha
              meno di {Math.round((backtest.parameters.p_min ?? 0.5) * 100)} probabilità su 100 di
              uscire. Un vantaggio su un esito raro resta un esito raro.
            </span>
          </li>
        </ul>
        <p>
          Ci siamo dati una banda: tacere fra il {percentuale(bandaDa)} e il {percentuale(bandaA)}{' '}
          delle partite, con un limite duro al 40%. Se un giorno tacessimo di più, lo diciamo in
          testa alla pagina invece di abbassare la soglia per riempire il sito.
        </p>
        <p>
          La soglia è l’unica manopola del sistema, e l’abbiamo girata una volta sola: scelta sul
          test storico e poi congelata. Il valore e la curva con cui l’abbiamo scelta sono{' '}
          <a href="/come-stiamo-andando/#soglia">nella pagina del record</a>.
        </p>
      </section>

      <section id="revisione">
        <h2>Le due versioni dello stesso pronostico</h2>
        <p>
          Di ogni partita scriviamo due volte. La prima circa una settimana prima, con il solo
          modello statistico. La seconda circa 36 ore prima, quando arrivano le quote e le usiamo
          per correggere la nostra stima.
        </p>
        <div className="scorrevole">
          <table className="tabella">
            <caption>Le due scritture, e cosa cambia fra l’una e l’altra.</caption>
            <thead>
              <tr>
                <th scope="col">Quando</th>
                <th scope="col">Con che cosa</th>
                <th scope="col">Peso della nostra stima</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">7 giorni prima</th>
                <td>solo il modello statistico</td>
                <td className="num">1,0</td>
              </tr>
              <tr>
                <th scope="row">36 ore prima</th>
                <td>modello e quote insieme</td>
                <td className="num">0,35</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* I due chip alla loro dimensione reale, affiancati: è la legenda del
            linguaggio B. Pieno contro tratteggiato — la differenza sopravvive
            alla monocromia. */}
        <ul className="legenda-chip">
          <li>
            <ChipProvenienza source="model_only" />
            <p>Il pronostico viene dal nostro modello, e basta. Le quote non erano ancora uscite.</p>
          </li>
          <li>
            <ChipProvenienza source="blended_with_odds" />
            <p>
              Abbiamo confrontato la nostra stima con le quote di mercato, e il numero che vedete
              tiene conto di entrambe.
            </p>
          </li>
        </ul>

        <p>
          Una sola revisione, annunciata in anticipo, sempre visibile. Al fischio d’inizio non
          tocchiamo più niente. Il pronostico precedente non viene mai cancellato: resta sulla
          scheda, con la sua data, accanto a quello nuovo.
        </p>
      </section>

      <section id="quote">
        <h2>Da dove vengono i dati, e le quote</h2>
        <p>
          I calendari, le formazioni e i risultati vengono da football-data.org. Le quote vengono
          da the-odds-api, e le usiamo solo per il confronto: non le pubblichiamo come consiglio,
          non le mettiamo accanto al pronostico, e non c’è nessun link a un operatore in nessun
          punto del sito.
        </p>
        <p>
          Il nostro piano delle quote ha un tetto mensile. Quando lo avviciniamo, riduciamo le
          chiamate invece di far pagare qualcuno: il sito è fatto di file statici, quindi il
          traffico non consuma crediti — solo i job notturni lo fanno.
        </p>

        {budget ? (
          <div className="crediti">
            <p>
              crediti quote usati questo mese{' '}
              <span className="crediti__valore">
                {intero(budget.used)} / {intero(budget.cap)}
              </span>
            </p>
            <div
              className="crediti__pista"
              role="img"
              aria-label={`${budget.used} crediti usati su ${budget.cap} disponibili questo mese.`}
            >
              <div
                className="crediti__riempimento"
                style={{ width: `${Math.min(100, (budget.used / budget.cap) * 100)}%` }}
              />
            </div>
            <p style={{ marginTop: 'var(--s-3)' }}>
              {budget.paused
                ? `In pausa: ${budget.pause_reason ?? 'tetto raggiunto'}. Fino al mese prossimo pubblichiamo solo il pronostico preliminare.`
                : budget.degradation_step != null
                  ? `Degradazione attiva (${budget.degradation_step}): stiamo chiamando meno campionati per restare dentro il tetto.`
                  : 'Nessuna degradazione attiva: stiamo chiamando tutti i campionati previsti.'}
            </p>
          </div>
        ) : null}
      </section>

      <section id="parametri">
        <h2>La tabella dei parametri</h2>
        <p>
          Sono i numeri che governano il sistema. Li pubblichiamo perché un criterio che non si può
          leggere non è un criterio.
        </p>
        <div className="scorrevole">
          <table className="tabella">
            <caption>I parametri del sistema, con il loro mestiere in italiano.</caption>
            <thead>
              <tr>
                <th scope="col">Parametro</th>
                <th scope="col">Valore</th>
                <th scope="col">A cosa serve</th>
              </tr>
            </thead>
            <tbody>
              {parametri.map(([nome, valore]) => (
                <tr key={nome}>
                  <th scope="row">
                    <span className="num">{nome}</span>{' '}
                    {MAI_TOCCATO.has(nome) ? (
                      <span className="tag-mono tag-mono--accento">Mai toccato</span>
                    ) : null}
                    {nome === 's_min_in_code' ? (
                      <span className="tag-mono tag-mono--accento">
                        Congelato il {dataConAnno(backtest.generated_at.slice(0, 10))}
                      </span>
                    ) : null}
                  </th>
                  <td className="num">
                    {Number.isInteger(valore) ? intero(valore) : decimale(valore, 3)}
                  </td>
                  <td>{SPIEGAZIONE[nome] ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="protocollo">
        <h2>Il protocollo pre-registrato</h2>
        <p>
          Le regole sono state scritte prima dei numeri. La data del commit lo dimostra, e non
          possiamo cambiarla.
        </p>
        <p className="definizione">
          Protocollo:{' '}
          <a
            href={`${REPO}/blob/main/${backtest.protocol}`}
            rel="noopener noreferrer"
            target="_blank"
          >
            {backtest.protocol} →
          </a>
          <br />
          Commit del test: {backtest.code_commit.slice(0, 7)} ·{' '}
          {dataConAnno(backtest.generated_at.slice(0, 10))}
        </p>
      </section>

      <section id="cosa-non-facciamo">
        <h2>Cosa non facciamo</h2>
        <ul className="elenco-netto">
          <li>Non vendiamo niente. Non abbiamo pubblicità.</li>
          <li>Non abbiamo link a operatori di scommesse, di nessun tipo.</li>
          <li>Non c’è login e non raccogliamo dati su di te.</li>
          <li>Non guadagniamo se scommetti.</li>
          <li>Non diciamo mai quanto giocare, e non parliamo di guadagni.</li>
          <li>
            Non pubblichiamo punteggi in diretta: i risultati arrivano con il calcolo della notte.
          </li>
        </ul>
        <p style={{ marginTop: 'var(--s-6)' }}>
          Il gioco d’azzardo può creare dipendenza. Se pensi che sia un problema per te o per
          qualcuno che conosci, il servizio pubblico esiste ed è gratuito:{' '}
          <a href={GIOCO_RESPONSABILE.href} rel="noopener noreferrer" target="_blank">
            {GIOCO_RESPONSABILE.testo}
          </a>
          .
        </p>
      </section>
    </div>
  );
}
