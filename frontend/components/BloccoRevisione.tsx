import { istanteInData, suCento } from '@/lib/formato';
import { ETICHETTA_TRANSIZIONE, testoTransizione } from '@/lib/testi';
import type { Fixture, Transizione } from '@/lib/tipi';

import { ChipProvenienza } from './ChipProvenienza';

/**
 * Il blocco di rettifica — la revisione delle 36 ore.
 *
 * Riprende una convenzione che i lettori già conoscono: l'errata corrige di un
 * giornale, che è storicamente un dispositivo di FIDUCIA, non di imbarazzo.
 * È contenuto: mai un <details> chiuso, mai un tooltip, mai una nota a piè di
 * pagina, e nessuna animazione di ingresso.
 *
 * Il confronto PRIMA/ORA non è mai un barrato: il barrato dice "sbagliato", e
 * qui non c'è niente di sbagliato — ci sono due stime datate. Due righe
 * impilate, allineate sulla stessa colonna, in una <table> con <th scope="row">
 * così lo screen reader legge la coppia come una coppia.
 */
export function BloccoRevisione({ fixture }: { fixture: Fixture }) {
  const transizione = fixture.transition;
  if (!transizione || transizione === 'first') return null;

  const testo = testoTransizione(transizione, fixture.previous, fixture.prediction);
  if (!testo) return null;

  const etichetta = ETICHETTA_TRANSIZIONE[transizione as Exclude<Transizione, 'first'>];
  const precedente = fixture.previous;

  /* Il confronto ha senso solo quando c'è davvero un prima e un ora da
     affiancare, cioè quando il mercato è cambiato. */
  const mostraConfronto =
    transizione === 'changed' &&
    precedente != null &&
    precedente.market_label != null &&
    precedente.p != null &&
    fixture.prediction != null;

  return (
    <aside className="rettifica">
      <div className="rettifica__corpo">
        <p className="label">{etichetta}</p>
        <p className="rettifica__testo">{testo}</p>

        {mostraConfronto && precedente && fixture.prediction ? (
        /* Le tabelle larghe scorrono dentro il proprio contenitore:
           la pagina non scorre mai in orizzontale, a nessuna larghezza. */
        <div className="scorrevole">
        <table className="confronto">
          <caption className="micro">
            Le due stime, con la data in cui le abbiamo scritte.
          </caption>
          <tbody>
            <tr className="confronto__prima">
              <th scope="row">Prima</th>
              <td className="micro">solo modello, {istanteInData(precedente.written_at)}</td>
              <td className="confronto__mercato">{precedente.market_label}</td>
              <td className="confronto__p">{suCento(precedente.p ?? 0)} su 100</td>
              <td>
                <ChipProvenienza source="model_only" compatto />
              </td>
            </tr>
            <tr aria-hidden="true">
              <td className="confronto__freccia" colSpan={5}>
                ↓
              </td>
            </tr>
            <tr className="confronto__ora">
              <th scope="row">Ora</th>
              <td className="micro">
                con le quote, {istanteInData(fixture.utc_date)}
              </td>
              <td className="confronto__mercato">{fixture.prediction.label}</td>
              <td className="confronto__p">{suCento(fixture.prediction.p)} su 100</td>
              <td>
                <ChipProvenienza source={fixture.source} compatto />
              </td>
            </tr>
          </tbody>
        </table>
        </div>
        ) : null}
      </div>
    </aside>
  );
}
