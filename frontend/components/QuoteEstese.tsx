import {
  copertura,
  linea as scriviLinea,
  nomeEsito,
  nomeMercato,
  suCento,
} from '@/lib/mercati-esteso';
/* La stessa funzione che formatta le quote nella tavola dei pronostici. Qui
   arrivavano con il punto — `1.02` — mentre due sezioni piu' su le stesse
   quote si leggevano `1,31`: due modi di scrivere un decimale nella stessa
   pagina, e il lettore non ha modo di sapere che sono la stessa cosa. */
import { formattaQuota } from '@/lib/quote';
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
 *
 * ------------------------------------------------------------------------
 * DUE FORME DI TABELLA, perche' la fonte manda due forme di mercato.
 *
 * Un mercato SENZA linea — esito finale, doppia chance — ha esiti che si
 * nominano da soli: `1`, `X`, `1X`. Una riga per esito, e si legge.
 *
 * Un mercato CON linea no. «Gol totali» arriva NOVE volte, identico nel nome,
 * con esiti che si chiamano sempre e solo «Oltre» e «Sotto». Stampato come gli
 * altri diventava nove tabelle indistinguibili in cui la sola cosa che conta —
 * sopra cosa? — non era scritta da nessuna parte. Non era un dettaglio
 * estetico: era un prezzo senza la domanda a cui risponde.
 *
 * Qui quei nove tornano UNA tabella, con la linea in prima colonna e gli esiti
 * come colonne. E' la forma in cui il mercato esiste davvero — una scala di
 * linee — e quella in cui chiunque abbia visto una lavagna di quote la sa gia'
 * leggere.
 */

/** Quanti mercati restano aperti prima di piegare il resto. */
const APERTI = 3;

type Riga = { esito: string; decimale: number; implicita: number | null };

type MercatoPronto = {
  nome: string;
  /** `null` quando il mercato non ha linea: e' quello che sceglie la forma. */
  linea: string | null;
  righe: Riga[];
  /** Gia' riportata alla copertura: e' un margine confrontabile con gli altri. */
  somma: number | null;
  /** 1 quasi ovunque, 2 sulla doppia chance. Cambia come si dice il margine. */
  copertura: number;
};

/** Un gruppo di mercati con lo stesso nome. Uno solo se il mercato e' unico. */
type Gruppo = {
  nome: string;
  /** Le colonne, nell'ordine del primo mercato letto. */
  esiti: string[];
  /** Una riga per linea. `linea` e' `null` sui mercati che non ne hanno. */
  linee: { linea: string | null; per: Map<string, Riga>; somma: number | null }[];
  conLinea: boolean;
  copertura: number;
};

/**
 * Il margine, detto in modo che chi legge possa VERIFICARLO sui numeri che ha
 * davanti.
 *
 * Su un mercato normale la verifica e' una somma: le probabilita' in colonna
 * fanno 108, e quegli 8 sono il margine. Su una doppia chance quella stessa
 * somma fa 210, perche' ogni esito ne contiene due — dire «somma 105» sarebbe
 * scrivere un numero che il lettore non ritrova sommando. Quindi si dice
 * un'altra cosa, e si dice perche'.
 */
function fraseMargine(somma: number | null, cop: number): string | null {
  if (somma === null || somma <= 100) return null;
  if (cop > 1) {
    return `ogni esito ne contiene due — il margine è ${somma - 100} su 100`;
  }
  return `somma ${somma} su 100 — ${somma - 100} è il margine`;
}

function preparaMercato(m: MercatoEsteso): MercatoPronto | null {
  const nome = nomeMercato(m.mercato);
  if (!nome) return null;

  const righe = m.esiti
    .map((e): Riga | null => {
      const esito = nomeEsito(e.esito);
      if (!esito || typeof e.decimale !== 'number' || e.decimale <= 0) return null;
      return {
        esito,
        decimale: e.decimale,
        implicita: typeof e.probabilita_implicita === 'number' ? e.probabilita_implicita : null,
      };
    })
    .filter((r): r is Riga => r !== null);

  if (righe.length === 0) return null;

  const grezza = (m.linea ?? '').trim();
  /* La somma si legge PER COPERTURA: su una doppia chance il 100 su 100 di
     riferimento e' 200, e dividere e' l'unico modo di ottenere un margine
     confrontabile con quello degli altri mercati. */
  const cop = copertura(m.mercato);
  const somma =
    typeof m.somma_probabilita === 'number'
      ? Math.round((m.somma_probabilita / cop) * 100)
      : null;
  return { nome, linea: grezza === '' ? null : grezza, righe, somma, copertura: cop };
}

/**
 * I mercati raggruppati per nome, nell'ordine in cui la fonte li manda.
 *
 * L'ordine e' della fonte e non alfabetico apposta: mette per primi i mercati
 * principali, ed e' l'ordine che decide quali tre restano aperti.
 */
function raggruppa(pronti: MercatoPronto[]): Gruppo[] {
  const per = new Map<string, Gruppo>();
  for (const m of pronti) {
    let g = per.get(m.nome);
    if (!g) {
      g = { nome: m.nome, esiti: [], linee: [], conLinea: false, copertura: m.copertura };
      per.set(m.nome, g);
    }
    for (const r of m.righe) {
      if (!g.esiti.includes(r.esito)) g.esiti.push(r.esito);
    }
    g.linee.push({
      linea: m.linea,
      per: new Map(m.righe.map((r) => [r.esito, r])),
      somma: m.somma,
    });
    if (m.linea !== null) g.conLinea = true;
  }
  return [...per.values()];
}

/** La forma a scala: una riga per linea, gli esiti in colonna. */
function TabellaConLinee({ g }: { g: Gruppo }) {
  return (
    <div className="mercato">
      <p className="mercato__testa">
        <span className="mercato__nome">{g.nome}</span>
        <span className="mercato__margine">
          {g.linee.length} {g.linee.length === 1 ? 'linea' : 'linee'}
        </span>
      </p>
      <table className="tabella tabella--linee">
        <thead>
          <tr>
            {/* `num` porta l'allineamento a destra: senza, l'intestazione resta
                a sinistra mentre le linee stanno a destra, e la colonna smette
                di leggersi come colonna. */}
            <th scope="col" className="num">
              Linea
            </th>
            {g.esiti.map((e) => (
              <th key={e} scope="col" className="num">
                {e}
              </th>
            ))}
            <th scope="col" className="num">
              Margine
            </th>
          </tr>
        </thead>
        <tbody>
          {g.linee.map((l) => (
            <tr key={l.linea ?? '—'}>
              <th scope="row" className="num linee__linea">
                {l.linea !== null ? scriviLinea(l.linea) : '—'}
              </th>
              {g.esiti.map((e) => {
                const r = l.per.get(e);
                return (
                  <td key={e} className="num" data-etichetta={e}>
                    {r ? (
                      <>
                        <span className="linee__quota">{formattaQuota(r.decimale)}</span>
                        {r.implicita !== null ? (
                          <span className="linee__implicita">{suCento(r.implicita)}</span>
                        ) : null}
                      </>
                    ) : (
                      <span aria-hidden="true">—</span>
                    )}
                  </td>
                );
              })}
              <td className="num mercato__implicita" data-etichetta="Margine">
                {l.somma !== null && l.somma > 100 ? `${l.somma - 100} su 100` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** La forma classica: una riga per esito. Per i mercati che linea non hanno. */
function TabellaMercato({ g }: { g: Gruppo }) {
  const sola = g.linee[0];
  if (!sola) return null;
  return (
    <div className="mercato">
      <p className="mercato__testa">
        <span className="mercato__nome">{g.nome}</span>
        {fraseMargine(sola.somma, g.copertura) !== null ? (
          <span className="mercato__margine">{fraseMargine(sola.somma, g.copertura)}</span>
        ) : null}
      </p>
      <table className="tabella tabella--mercato">
        <thead>
          <tr>
            <th scope="col">Esito</th>
            <th scope="col" className="num">
              Quota
            </th>
            <th scope="col" className="num">
              Quanto la dà il prezzo
            </th>
          </tr>
        </thead>
        <tbody>
          {g.esiti.map((e) => {
            const r = sola.per.get(e);
            if (!r) return null;
            return (
              <tr key={e}>
                <th scope="row">{e}</th>
                <td className="num" data-etichetta="Quota">
                  {formattaQuota(r.decimale)}
                </td>
                <td className="num mercato__implicita" data-etichetta="Quanto la dà il prezzo">
                  {r.implicita !== null ? suCento(r.implicita) : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Blocco({ g }: { g: Gruppo }) {
  return g.conLinea ? <TabellaConLinee g={g} /> : <TabellaMercato g={g} />;
}

export function QuoteEstese({ mercati }: { mercati: MercatoEsteso[] }) {
  const pronti = mercati
    .map(preparaMercato)
    .filter((m): m is MercatoPronto => m !== null);

  const scartati = mercati.length - pronti.length;
  if (pronti.length === 0) return null;

  const gruppi = raggruppa(pronti);
  const primi = gruppi.slice(0, APERTI);
  const resto = gruppi.slice(APERTI);

  return (
    <section className="sezione mercati" id="altri-mercati" aria-labelledby="titolo-mercati">
      <h2 id="titolo-mercati" className="label sezione__titolo">
        <span className="bersaglio" aria-hidden="true" /> Altri mercati
      </h2>

      <p className="sezione__lettura">
        Prezzi da una fonte diversa da quella che usiamo per i pronostici, sui mercati che quella
        non copre. Il numero sotto la quota è quanto la dà il prezzo, margine dell’operatore
        incluso: <strong>non è la nostra stima</strong>, e su questi mercati il nostro modello non
        si pronuncia. Dove il mercato ha una scala di linee, la linea è la prima colonna: «Oltre
        2,5» vuol dire tre gol o più.
      </p>

      {primi.map((g) => (
        <Blocco key={g.nome} g={g} />
      ))}

      {resto.length > 0 ? (
        <details className="mercati__altri">
          <summary>
            Altri {resto.length} {resto.length === 1 ? 'mercato' : 'mercati'}
          </summary>
          {resto.map((g) => (
            <Blocco key={g.nome} g={g} />
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
