import { decimale, intero } from '@/lib/formato';
import type { Accuracy } from '@/lib/tipi';

/**
 * Il numero in testa alla pagina: SKILL DICHIARATO contro REALIZZATO.
 * Non la curva di calibrazione (brief §14.6).
 *
 * Riceve SOLO `accuracy.json`. Non tocca `backtest.json`, in nessuna forma:
 * i due file non condividono un componente, una prop, una tabella o una media.
 *
 * Due barre sullo stesso asse — linguaggio A (pieno) per entrambe, perché sono
 * la stessa grandezza misurata due volte. La banda di incertezza sul
 * realizzato resta linguaggio B (tratto), come ovunque.
 */
export function SkillDichiarato({ accuracy }: { accuracy: Accuracy }) {
  const { live, progress_to_500: avanzamento } = accuracy;
  const dichiarato = live.skill_declared_mean;
  const realizzato = live.skill_realized_mean;
  const abbastanza =
    live.n >= 100 && typeof dichiarato === 'number' && typeof realizzato === 'number';

  return (
    <section className="blocco" aria-labelledby="titolo-skill">
      <h2 id="titolo-skill" className="label">
        Quanto ne sapevamo davvero
      </h2>

      {abbastanza ? (
        <BarreSkill
          dichiarato={dichiarato}
          realizzato={realizzato}
          errore={live.skill_realized_se ?? 0}
          n={live.n}
        />
      ) : (
        /* Avvio a freddo. Il blocco NON si nasconde: si sostituisce con la
           propria soglia dichiarata, stesso contenitore e stessa massa visiva.
           È lo stesso principio dello stato di silenzio, applicato a una pagina. */
        <>
          <p className="a-freddo">
            Abbiamo pubblicato {intero(avanzamento.published)} pronostici, e nessuna di quelle
            partite si è ancora conclusa.
          </p>
          <p className="a-freddo__nota">
            Il confronto fra quello che dicevamo e quello che sapevamo davvero compare da 100
            pronostici conclusi: sotto quella soglia una media direbbe più sul caso che su di noi.
            Qui sotto ci sono i numeri grezzi, senza sintesi.
          </p>
        </>
      )}
    </section>
  );
}

function BarreSkill({
  dichiarato,
  realizzato,
  errore,
  n,
}: {
  dichiarato: number;
  realizzato: number;
  errore: number;
  n: number;
}) {
  /* Le due barre condividono l'asse: stessa scala, stessa larghezza massima. */
  const massimo = Math.max(dichiarato, realizzato + 2 * errore, 0.001) * 1.15;
  const larghezza = (v: number) => `${Math.max(0, Math.min(100, (v / massimo) * 100))}%`;

  const divario = dichiarato === 0 ? 0 : (dichiarato - realizzato) / Math.abs(dichiarato);
  const commento =
    realizzato >= dichiarato
      ? 'Finora siamo stati leggermente prudenti.'
      : divario < 0.2
        ? 'Finora le due misure coincidono.'
        : 'Finora siamo stati più sicuri di quanto i risultati giustifichino.';

  return (
    <>
      <div className="skill__riga">
        <span className="skill__etichetta">Dicevamo di saperne tanto così.</span>
        <span className="skill__pista">
          <span className="skill__riempimento" style={{ width: larghezza(dichiarato) }} />
        </span>
        <span className="skill__valore">{decimale(dichiarato, 3)}</span>
      </div>

      <div className="skill__riga">
        <span className="skill__etichetta">Ne sapevamo davvero tanto così.</span>
        <span className="skill__pista">
          <span className="skill__riempimento" style={{ width: larghezza(realizzato) }} />
          {errore > 0 ? (
            <span
              className="skill__banda"
              aria-hidden="true"
              style={{
                left: larghezza(Math.max(0, realizzato - 1.96 * errore)),
                width: `${
                  ((Math.min(massimo, realizzato + 1.96 * errore) -
                    Math.max(0, realizzato - 1.96 * errore)) /
                    massimo) *
                  100
                }%`,
              }}
            />
          ) : null}
        </span>
        <span className="skill__valore">{decimale(realizzato, 3)}</span>
      </div>

      <p className="definizione">
        Le due barre misurano quanta informazione i nostri pronostici portavano rispetto alla media
        del campionato. Se il sistema è calibrato coincidono. Se la seconda resta sotto, siamo stati
        troppo sicuri di noi.
        <br />
        {commento}
      </p>
      <p className="micro" style={{ marginTop: 'var(--s-2)' }}>
        n={intero(n)}
      </p>
    </>
  );
}
