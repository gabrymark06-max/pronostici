import { nomeEsito, nomeMercato, suCento } from '@/lib/mercati-esteso';
import type { MercatoEsteso } from '@/lib/tipi';

/**
 * I MERCATI CHE LA FONTE PRINCIPALE NON COPRE.
 *
 * Le quote gia' cablate nel sito arrivano da operatori con licenza italiana e
 * coprono esito finale e over/under. Questa tabella arriva da un'altra fonte e
 * porta i mercati che quella non ha: cartellini nella partita, calci d'angolo,
 * prima squadra a segnare, primo tempo.
 *
 * DUE COSE CHE NON VANNO CONFUSE, ed e' il motivo per cui questo blocco sta
 * dopo i pronostici e non accanto:
 *
 *  1. la probabilita' qui accanto e' quella che il PREZZO esprime, e contiene
 *     ancora il margine dell'operatore. Non e' la nostra, e non e' nemmeno
 *     quella del mercato depurata;
 *  2. su questi mercati il nostro modello non dice niente. Non c'e' un nostro
 *     numero da confrontare, quindi non c'e' un confronto.
 *
 * IL MARGINE SI DICE COME SOMMA, non come percentuale. Su un mercato equo le
 * probabilita' sommano a 100 su 100; se sommano a 108, quegli 8 sono il
 * margine. Detto cosi' il lettore vede da dove esce il numero invece di
 * doversi fidare.
 *
 * Quello che non sappiamo tradurre non si mostra, e si dice quanti sono: vedi
 * `lib/mercati-esteso.ts`.
 */

/** Quanti mercati restano aperti prima di piegare il resto. */
const APERTI = 3;

type MercatoPronto = {
  nome: string;
  righe: { esito: string; decimale: number; implicita: number | null }[];
  somma: number | null;
};

function preparaMercato(m: MercatoEsteso): MercatoPronto | null {
  const nome = nomeMercato(m.mercato);
  if (!nome) return null;

  const righe = m.esiti
    .map((e) => {
      const esito = nomeEsito(e.esito);
      if (!esito || typeof e.decimale !== 'number' || e.decimale <= 0) return null;
      return {
        esito,
        decimale: e.decimale,
        implicita: typeof e.probabilita_implicita === 'number' ? e.probabilita_implicita : null,
      };
    })
    .filter((r): r is NonNullable<typeof r> => r !== null);

  if (righe.length === 0) return null;

  const somma =
    typeof m.somma_probabilita === 'number' ? Math.round(m.somma_probabilita * 100) : null;
  return { nome, righe, somma };
}

function TabellaMercato({ m }: { m: MercatoPronto }) {
  return (
    <div className="mercato">
      <p className="mercato__testa">
        <span className="mercato__nome">{m.nome}</span>
        {m.somma !== null && m.somma > 100 ? (
          <span className="mercato__margine">
            somma {m.somma} su 100 — {m.somma - 100} è il margine
          </span>
        ) : null}
      </p>
      <div className="scorrevole">
        <table className="tabella tabella--mercato">
          <thead>
            <tr>
              <th scope="col">Esito</th>
              <th scope="col">Quota</th>
              <th scope="col">Quanto la dà il prezzo</th>
            </tr>
          </thead>
          <tbody>
            {m.righe.map((r) => (
              <tr key={r.esito}>
                <th scope="row">{r.esito}</th>
                <td className="num">{r.decimale.toFixed(2)}</td>
                <td className="num mercato__implicita">
                  {r.implicita !== null ? suCento(r.implicita) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function QuoteEstese({ mercati }: { mercati: MercatoEsteso[] }) {
  const pronti = mercati
    .map(preparaMercato)
    .filter((m): m is MercatoPronto => m !== null);

  const scartati = mercati.length - pronti.length;
  if (pronti.length === 0) return null;

  const primi = pronti.slice(0, APERTI);
  const resto = pronti.slice(APERTI);

  return (
    <section className="sezione mercati" aria-labelledby="titolo-mercati">
      <h2 id="titolo-mercati" className="label sezione__titolo">
        <span className="bersaglio" aria-hidden="true" /> Altri mercati
      </h2>

      <p className="sezione__lettura">
        Prezzi da una fonte diversa da quella che usiamo per i pronostici, sui mercati che quella
        non copre. Il numero accanto alla quota è quanto la dà il prezzo, margine dell’operatore
        incluso: <strong>non è la nostra stima</strong>, e su questi mercati il nostro modello non
        si pronuncia.
      </p>

      {primi.map((m) => (
        <TabellaMercato key={m.nome} m={m} />
      ))}

      {resto.length > 0 ? (
        <details className="mercati__altri">
          <summary>
            Altri {resto.length} {resto.length === 1 ? 'mercato' : 'mercati'}
          </summary>
          {resto.map((m) => (
            <TabellaMercato key={m.nome} m={m} />
          ))}
        </details>
      ) : null}

      {scartati > 0 ? (
        <p className="sezione__nota">
          {scartati} {scartati === 1 ? 'mercato non è mostrato' : 'mercati non sono mostrati'}:
          la fonte li nomina in un modo che non sappiamo ancora tradurre, e preferiamo non
          mostrarli piuttosto che mostrarli in inglese.
        </p>
      ) : null}
    </section>
  );
}
