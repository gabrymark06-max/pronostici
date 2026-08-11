import { suCento, testoPulito } from '@/lib/formato';
import { grezzeInOrdine } from '@/lib/mercati';
import { vesteSilenzio } from '@/lib/testi';
import type { FixtureInSilenzio } from '@/lib/tipi';

import { ChipProvenienza } from './ChipProvenienza';

/**
 * LO STATO DI SILENZIO.
 *
 * Circa tre partite su dieci non hanno un pronostico, e quel silenzio e' la
 * funzionalita': deve leggersi come SEVERITÀ, non come guasto.
 *
 * Le tre regole strutturali che lo tengono in piedi:
 *  1. STESSA LASTRA del pronostico — stessa riga di taratura, stesso fondo,
 *     stessa larghezza, stesso padding, stesso colore di testo. E' lo stesso
 *     contenitore riempito diversamente, e infatti lastra e taratura le mette
 *     la pagina, non questo componente;
 *  2. il messaggio occupa lo SLOT DELLA CIFRA, alla stessa dimensione ottica:
 *     la massa visiva e' conservata, ed e' la regola che da sola impedisce al
 *     silenzio di sembrare un vuoto;
 *  3. si mostra il lavoro fatto, con `diagnostics.n_candidates`: converte
 *     un'assenza in uno sforzo.
 *
 * Vietati qui: icone o triangoli di avviso, bordo tratteggiato del
 * contenitore, testo in --ink-3, fondo diverso da --surface, opacita'
 * ridotta, skeleton o shimmer, e le parole "errore", "nessun dato", "non
 * disponibile".
 *
 * I motivi si distinguono per GLIFO + ETICHETTA, mai per colore: un segno
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
          {/* Numeri NUDI, senza barra: la barra e' il linguaggio del "questo
              lo consigliamo", e darla a numeri che non consigliamo
              inviterebbe l'occhio a scegliere la piu' alta — cioe' a
              ricostruire l'argmax che abbiamo tolto di mezzo apposta. */}
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
    </section>
  );
}
