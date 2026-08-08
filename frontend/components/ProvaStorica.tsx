import { dataConAnno, decimale, intero, percentuale } from '@/lib/formato';
import { etichettaFascia, nomeCompetizione, REPO } from '@/lib/testi';
import type { Backtest } from '@/lib/tipi';

import { CurvaSilenzio } from './CurvaSilenzio';

/**
 * LA PROVA STORICA.
 *
 * Riceve SOLO `backtest.json`. Nessun numero di `accuracy.json` entra qui, in
 * nessuna tabella, in nessuna barra, in nessuna media. Da questo punto la
 * pagina ha un fondo diverso, un titolo proprio e una larghezza propria:
 * visivamente è un altro documento dentro la stessa pagina.
 */

/** Le voci a cui il prodotto si è legato le mani. */
const SPIEGAZIONE_PARAMETRO: Record<string, string> = {
  p_min: 'la probabilità sotto la quale non consigliamo, qualunque cosa dica il modello',
  sigma_max: 'quanto può oscillare una stima prima che la scartiamo',
  s_min_in_code: 'quanta informazione in più deve portare un mercato per meritare un consiglio',
  model_weight: 'quanto pesa la nostra stima quando non ci sono quote',
  tau: 'di quanto riportiamo verso la media le stime incerte',
  draws: 'quante simulazioni per stimare la banda di incertezza',
  half_life_days: 'dopo quanti giorni una partita conta la metà',
  window_days: 'quanti giorni di storia guardiamo',
  min_train_matches: 'quante partite servono prima di dire qualcosa su una squadra',
  step_days: 'ogni quanti giorni riadattiamo il modello',
  rho_max: 'il tetto alla correzione sui punteggi bassi',
};

const MAI_TOCCATO = new Set(['p_min', 'sigma_max']);

export function ProvaStorica({ backtest }: { backtest: Backtest }) {
  const fasce = Object.entries(backtest.buckets);
  const competizioni = Object.entries(backtest.per_competition).sort(
    (a, b) => b[1].evaluated - a[1].evaluated,
  );
  const parametri = Object.entries(backtest.parameters);

  return (
    <section className="prova-storica" aria-labelledby="titolo-prova">
      <div className="colonna">
        <p className="label">Da qui in giù è un altro documento</p>
        <h2 id="titolo-prova" className="titolo-pagina">
          Prova storica (backtest)
        </h2>

        {/* Prima i numeri, IL LIMITE. Non un asterisco, non un <details>. */}
        <p className="prova-storica__avvertenza">
          Un backtest non è un track record: è la stessa persona che decide le regole e conta i
          punti. Per questo lo teniamo separato, e per questo abbiamo scritto le regole prima. Il
          numero che conta è quello sopra.
        </p>

        {/* La ricevuta: i campi che rendono il backtest interpretabile.
            Stampati, non messi in una FAQ. */}
        <dl className="ricevuta">
          <div>
            <dt>configurazioni provate</dt>
            <dd>{intero(backtest.configurations_tried)}</dd>
          </div>
          <div>
            <dt>commit del codice</dt>
            <dd>
              <a href={`${REPO}/commit/${backtest.code_commit}`} rel="noopener noreferrer" target="_blank">
                {backtest.code_commit.slice(0, 7)} →
              </a>
            </dd>
          </div>
          <div>
            <dt>generato il</dt>
            <dd>{dataConAnno(backtest.generated_at.slice(0, 10))}</dd>
          </div>
          <div>
            <dt>finestra</dt>
            <dd>
              dal {dataConAnno(backtest.window.from)} al {dataConAnno(backtest.window.to)}
            </dd>
          </div>
          <div>
            <dt>partite valutate</dt>
            <dd>
              {intero(backtest.volume.evaluated)}, con un pronostico su{' '}
              {intero(backtest.volume.with_prediction)}
            </dd>
          </div>
          <div>
            <dt>protocollo</dt>
            <dd>
              <a href={`${REPO}/blob/main/${backtest.protocol}`} rel="noopener noreferrer" target="_blank">
                {backtest.protocol} →
              </a>
            </dd>
          </div>
          <div>
            <dt>misura</dt>
            <dd>{backtest.measures}</dd>
          </div>
          <div>
            <dt>non misurato</dt>
            <dd>{backtest.not_measured}</dd>
          </div>
        </dl>

        {/* ONESTÀ OBBLIGATA. Nascondere il dato sfavorevole nella pagina che
            esiste per mostrare i dati sfavorevoli sarebbe l'unico errore
            fatale possibile qui. */}
        {!backtest.log_loss_over_2_5.model_better ? (
          <div className="sfavorevole">
            <p className="label">Un risultato che non ci fa comodo</p>
            <p style={{ marginTop: 'var(--s-3)' }}>
              Su Over 2.5 il nostro modello non batte il tasso base del campionato. Lo diciamo
              perché è vero, ed è una delle ragioni per cui tacciamo spesso.
            </p>
            <p className="definizione">
              Misurato con la log loss su {intero(backtest.log_loss_over_2_5.n)} partite: il nostro
              modello segna {decimale(backtest.log_loss_over_2_5.model, 5)}, il tasso base{' '}
              {decimale(backtest.log_loss_over_2_5.base_rate, 5)}. Più basso è meglio, e il nostro
              è più alto.
            </p>
          </div>
        ) : null}

        {/* Le fasce. Un'accuratezza non compare mai senza la sua fascia. */}
        <h3 className="titolo-sezione" style={{ marginTop: 'var(--s-7)' }}>
          Per fascia di probabilità
        </h3>
        <div className="scorrevole">
          <table className="tabella">
            <caption>
              Quanto spesso si sono avverati i pronostici del test storico, fascia per fascia. Mai
              una media unica: gli 85 su 100 sono facili, i 55 no.
            </caption>
            <thead>
              <tr>
                <th scope="col">Fascia</th>
                <th scope="col">Dicevamo (media)</th>
                <th scope="col">È uscito</th>
                <th scope="col">Scarto</th>
                <th scope="col">n</th>
              </tr>
            </thead>
            <tbody>
              {fasce.map(([chiave, fascia]) => {
                const scarso = fascia.enough === false;
                const dichiarato = fascia.mean_p ?? 0;
                const osservato = fascia.hit_rate ?? 0;
                return (
                  <tr key={chiave} className={scarso ? 'fascia-scarsa' : undefined}>
                    <th scope="row">
                      {etichettaFascia(chiave)}{' '}
                      {scarso ? <span className="tag-mono">Troppo pochi</span> : null}
                    </th>
                    <td className="num">{Math.round(dichiarato * 100)} su 100</td>
                    <td className="num">{Math.round(osservato * 100)} su 100</td>
                    <td>
                      {/* La barra doppia rende lo scarto un disallineamento
                          visibile, senza dover leggere due numeri.
                          Se n non basta, la barra diventa un filetto vuoto:
                          rifiutarsi di disegnare è a sua volta un dato. */}
                      {scarso ? (
                        <div className="barra-vuota" aria-hidden="true" />
                      ) : (
                        <div className="doppia" aria-hidden="true">
                          <div className="doppia__pista">
                            <div
                              className="doppia__riempimento doppia__riempimento--dichiarato"
                              style={{ width: `${dichiarato * 100}%` }}
                            />
                          </div>
                          <div className="doppia__pista">
                            <div
                              className="doppia__riempimento"
                              style={{ width: `${osservato * 100}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </td>
                    <td className="num">{intero(fascia.n)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="definizione">
          La barra chiara è quello che dicevamo, quella scura quello che è successo. Quando
          coincidono, il sistema è calibrato in quella fascia.
        </p>

        {/* Per competizione, con silence_rate accanto: sono la stessa storia. */}
        <h3 className="titolo-sezione" style={{ marginTop: 'var(--s-7)' }}>
          Per competizione
        </h3>
        <div className="scorrevole">
          <table className="tabella">
            <caption>
              Dove tacciamo di più, ci prendiamo di meno quando parliamo: sono la stessa storia
              vista da due lati.
            </caption>
            <thead>
              <tr>
                <th scope="col">Competizione</th>
                <th scope="col">Valutate</th>
                <th scope="col">Con pronostico</th>
                <th scope="col">È uscito</th>
                <th scope="col">Quanto tacciamo</th>
              </tr>
            </thead>
            <tbody>
              {competizioni.map(([codice, dati]) => (
                <tr key={codice}>
                  <th scope="row">{nomeCompetizione(codice)}</th>
                  <td className="num">{intero(dati.evaluated)}</td>
                  <td className="num">{intero(dati.with_prediction)}</td>
                  <td className="num">{Math.round(dati.hit_rate * 100)} su 100</td>
                  <td className="num">{percentuale(dati.silence_rate, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* La curva silenzio ↔ S_min. */}
        <h3 className="titolo-sezione" style={{ marginTop: 'var(--s-7)' }} id="soglia">
          Come abbiamo scelto quanto tacere
        </h3>
        <CurvaSilenzio backtest={backtest} />

        {/* I parametri. */}
        <h3 className="titolo-sezione" style={{ marginTop: 'var(--s-7)' }} id="parametri-backtest">
          I parametri del test
        </h3>
        <div className="scorrevole">
          <table className="tabella">
            <caption>Gli stessi valori che girano nei job, con il loro mestiere in italiano.</caption>
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
                  <td>{SPIEGAZIONE_PARAMETRO[nome] ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
