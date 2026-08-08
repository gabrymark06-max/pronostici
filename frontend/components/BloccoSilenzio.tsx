
import { suCento, testoPulito } from '@/lib/formato';
import { grezzeInOrdine } from '@/lib/mercati';
import { vesteSilenzio } from '@/lib/testi';
import type { FixtureInSilenzio } from '@/lib/tipi';

import { ChipProvenienza } from './ChipProvenienza';

/**
 * Lo stato di silenzio. Il 26% delle partite non ha un pronostico, e quel
 * silenzio è la funzionalità: deve leggersi come SEVERITÀ, non come guasto.
 *
 * Le tre regole strutturali che lo tengono in piedi (MASTER 5.1):
 *  1. stesso contenitore del pronostico — stesso filetto di testata 2px
 *     --rule-accent, stessa larghezza, stesso padding, stesso colore di testo;
 *  2. il messaggio occupa lo SLOT DELLA CIFRA (24px al posto di 56px):
 *     la massa visiva è conservata, ed è la regola che da sola impedisce al
 *     silenzio di sembrare un vuoto;
 *  3. si mostra il lavoro fatto, con `diagnostics.n_candidates`: converte
 *     un'assenza in uno sforzo.
 *
 * Vietati qui: icone o triangoli di avviso, bordo tratteggiato del
 * contenitore, testo in --ink-muted, sfondo grigio, skeleton o shimmer, e le
 * parole "errore", "nessun dato", "non disponibile", "N/D".
 *
 * I tre motivi si distinguono per GLIFO + ETICHETTA, mai per colore: un segno
 * matematico dice "misurato", non "guasto".
 */
export function BloccoSilenzio({ fixture }: { fixture: FixtureInSilenzio }) {
  const veste = vesteSilenzio(fixture);
  const grezze = grezzeInOrdine(fixture.raw_probabilities);

  return (
    <section className="blocco" aria-labelledby="titolo-silenzio">
      <div className="silenzio__testata">
        <h2 id="titolo-silenzio" className="label">
          Nessun pronostico
        </h2>
        <div className="silenzio__motivo">
          <span className="silenzio__glifo" aria-hidden="true">
            {veste.glifo}
          </span>
          <span className="label silenzio__etichetta">{veste.etichetta}</span>
        </div>
      </div>

      <p className="silenzio__messaggio">{testoPulito(veste.titolo)}</p>
      <p className="silenzio__lavoro">{veste.sottotitolo}</p>

      <div className="silenzio__chip">
        <ChipProvenienza source={fixture.source} />
      </div>

      {grezze.length > 0 ? (
        <div className="silenzio__grezze">
          <h3 className="label">Le probabilità, senza consiglio</h3>
          {/* Numeri NUDI, senza barra: la barra è il linguaggio del "questo lo
              consigliamo", e darla a numeri che non consigliamo inviterebbe
              l'occhio a scegliere la più alta — cioè a ricostruire l'argmax
              che abbiamo tolto di mezzo apposta. */}
          <div className="grezze">
            {grezze.map((voce) => (
              <span className="grezze__voce" key={voce.etichetta}>
                <span className="grezze__etichetta">{voce.etichetta}</span>
                <span className="grezze__valore">{suCento(voce.p)}</span>
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <p className="silenzio__rimando">
        <a href="/come-funziona/#silenzio">Perché a volte non diciamo niente →</a>
      </p>
    </section>
  );
}
