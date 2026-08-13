import {
  finestraGiorni,
  giorniVicini,
  leggiGiorno,
  manifestoCrest,
  riepilogoGiorni,
} from '@/lib/dati';
import { dataLunga } from '@/lib/formato';
import { schedineDelGiorno } from '@/lib/schedine';

import { Calendario } from './Calendario';
import { Schedina } from './Schedina';

/**
 * IL CORPO DELLA PAGINA DELLE SCHEDINE, condiviso da due rotte.
 *
 * `/pronostico-del-giorno/` e `/pronostico-del-giorno/{data}/` mostrano la
 * stessa cosa: la prima sul giorno piu' recente pubblicato, la seconda su
 * quello chiesto. Prima la rotta senza data era un rimando con un link da
 * cliccare, e il risultato era che la voce piu' importante della barra portava
 * a una pagina bianca con sopra una frase. Adesso mostra i pronostici, e resta
 * un indirizzo stabile da condividere.
 *
 * Il canonical delle due rotte punta sempre alla pagina DATATA: il contenuto
 * e' lo stesso e l'indirizzo con la data e' quello che continuera' a valere.
 */
export function CorpoSchedine({ data }: { data: string }) {
  const giorno = leggiGiorno(data);
  if (!giorno) return null;

  const { precedente, successivo } = giorniVicini(data);
  const manifesto = manifestoCrest();
  const crest = (url: string | null) => (url ? (manifesto[url] ?? url) : null);

  const { raddoppio, multipla, candidate } = schedineDelGiorno(giorno.fixtures);

  return (
    <>
      <Calendario
        giorni={riepilogoGiorni(finestraGiorni(data, 9))}
        corrente={data}
        precedente={precedente}
        successivo={successivo}
        base="/pronostico-del-giorno"
      />

      <div className="colonna colonna--lista">
        <header className="schedine__testata">
          <h1 className="titolo-sezione">Il pronostico del giorno</h1>
          <p className="schedine__lettura">
            Due combinazioni dei pronostici di {dataLunga(data)}, scelte da una regola e non a
            mano. Il numero grande di ognuna è{' '}
            <strong>quante volte su cento esce tutta intera</strong>, non la quota: le due cose
            sono lo stesso numero al contrario — la nostra quota è uno diviso la probabilità —
            e fra le due abbiamo messo grande quella che cala quando la scommessa peggiora.
          </p>
        </header>

        {raddoppio === null && multipla === null ? (
          <div className="giorno-vuoto">
            <p>
              {candidate === 0
                ? `Il ${dataLunga(data)} non ci siamo esposti su nessuna partita.`
                : `Il ${dataLunga(data)} ci siamo esposti su una partita sola.`}
            </p>
            <p>
              Una schedina ha bisogno di almeno due pronostici, e non li fabbrichiamo per
              riempire una pagina.
            </p>
          </div>
        ) : (
          <>
            {raddoppio ? <Schedina schedina={raddoppio} crest={crest} /> : null}
            {multipla ? <Schedina schedina={multipla} crest={crest} /> : null}
          </>
        )}
      </div>
    </>
  );
}
