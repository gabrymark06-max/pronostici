import type { Metadata } from 'next';

import { BarraVerso500 } from '@/components/BarraVerso500';
import { ProvaStorica } from '@/components/ProvaStorica';
import { Registro } from '@/components/Registro';
import { SkillDichiarato } from '@/components/SkillDichiarato';
import { TassoSilenzio } from '@/components/TassoSilenzio';
import { leggiAccuracy, leggiBacktest, leggiRegistro } from '@/lib/dati';
import { intero } from '@/lib/formato';

export const metadata: Metadata = {
  title: 'Come stiamo andando',
  description:
    'Il registro di ogni pronostico che abbiamo pubblicato prima della partita, quanto stiamo tacendo, e la prova storica tenuta separata — compresi i risultati che non ci fanno comodo.',
  alternates: { canonical: '/come-stiamo-andando/' },
};

/**
 * L'ORDINE È IL MESSAGGIO: il registro dal vivo viene prima, anche quando è
 * quasi vuoto. La cosa vera precede la cosa grande.
 *
 * `accuracy.json` e `backtest.json` sono letti qui e passati a componenti
 * DIVERSI. Non condividono una prop, una tabella, una barra o una media.
 */
export default function PaginaComeStiamoAndando() {
  const accuracy = leggiAccuracy();
  const backtest = leggiBacktest();
  const registro = leggiRegistro();

  const conclusi = accuracy.live.n;
  const mancanti = Math.max(0, 500 - conclusi);
  const abbastanzaPerFasce = conclusi >= 150;

  return (
    <>
      <div className="colonna colonna--lista">
        <header className="pagina__intestazione">
          <span className="label pagina__occhiello">Il nostro record</span>
          <h1 className="titolo-pagina">Come stiamo andando</h1>
          <p className="pagina__sommario">
            Qui sotto c’è tutto quello che abbiamo pubblicato, compreso quello che non ci fa
            comodo. Il registro dal vivo viene prima della prova storica, anche quando è quasi
            vuoto: la cosa vera precede la cosa grande.
          </p>
        </header>

        {/* 1. Il numero in testa — skill dichiarato contro realizzato. */}
        <SkillDichiarato accuracy={accuracy} />

        {/* 2. Il registro dal vivo, nudo. Compare da n ≥ 1. */}
        {registro.length > 0 ? (
          <Registro righe={registro} />
        ) : (
          <section className="sezione--pesante">
            <h2 className="titolo-sezione">Il registro</h2>
            <p className="a-freddo__nota">
              Non abbiamo ancora pubblicato nessun pronostico. La prima riga comparirà qui il
              giorno in cui ne pubblicheremo uno, e non verrà più cancellata.
            </p>
          </section>
        )}

        {/* 3. Hit rate per fascia — dal vivo. Compare da n ≥ 150.
              Sotto la soglia si dichiara la soglia: non si riempie il buco con
              i numeri del backtest, che stanno sotto e sono un'altra cosa. */}
        <section className="sezione--pesante" aria-labelledby="titolo-fasce-vivo">
          <h2 id="titolo-fasce-vivo" className="titolo-sezione">
            Quanto ci prendiamo, per fascia
          </h2>
          {abbastanzaPerFasce && accuracy.live.buckets ? (
            <FasceDalVivo buckets={accuracy.live.buckets} />
          ) : (
            <>
              <p className="a-freddo__nota">
                Questa tabella compare da 150 pronostici conclusi. Ne abbiamo{' '}
                {intero(conclusi)}. Non la riempiamo con i numeri del test storico: quelli stanno
                più sotto, sono un’altra cosa, e mescolarli renderebbe entrambi inutili.
              </p>
              <p className="definizione">
                La curva di calibrazione compare da 500 pronostici. Ne mancano {intero(mancanti)}.
              </p>
            </>
          )}
        </section>

        {/* 4. Tasso di silenzio contro la banda dichiarata. */}
        <TassoSilenzio accuracy={accuracy} banda={backtest.silence.band} />

        {/* 5. La barra verso i 500. */}
        <BarraVerso500
          pubblicati={accuracy.progress_to_500.published}
          obiettivo={accuracy.progress_to_500.target}
        />

        <p className="corpo" style={{ marginTop: 'var(--s-6)' }}>
          <a href="/come-funziona/">Come scegliamo cosa dire, e quando tacere →</a>
        </p>
      </div>

      {/* 6 e 7. La separazione, e la prova storica. Fondo diverso, titolo
          proprio, larghezza propria: un altro documento nella stessa pagina. */}
      <ProvaStorica backtest={backtest} />
    </>
  );
}

/** Solo `accuracy.json`. Nessun numero del backtest entra in questa tabella. */
function FasceDalVivo({ buckets }: { buckets: NonNullable<import('@/lib/tipi').Accuracy['live']['buckets']> }) {
  const righe = Object.entries(buckets);
  return (
    <div className="scorrevole">
      <table className="tabella">
        <caption>Fra i pronostici che abbiamo pubblicato, fascia per fascia.</caption>
        <thead>
          <tr>
            <th scope="col">Fascia</th>
            <th scope="col">Dicevamo (media)</th>
            <th scope="col">È uscito</th>
            <th scope="col">n</th>
          </tr>
        </thead>
        <tbody>
          {righe.map(([chiave, fascia]) => {
            const scarso = fascia.enough === false;
            return (
              <tr key={chiave} className={scarso ? 'fascia-scarsa' : undefined}>
                <th scope="row">
                  {chiave} {scarso ? <span className="tag-mono">Troppo pochi</span> : null}
                </th>
                <td className="num">
                  {fascia.mean_p != null ? `${Math.round(fascia.mean_p * 100)} su 100` : '—'}
                </td>
                <td className="num">
                  {fascia.hit_rate != null ? `${Math.round(fascia.hit_rate * 100)} su 100` : '—'}
                </td>
                <td className="num">{intero(fascia.n)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
