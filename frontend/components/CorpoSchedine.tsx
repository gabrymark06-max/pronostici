import {
  finestraGiorni,
  giorniVicini,
  leggiGiorno,
  manifestoCrest,
  riepilogoGiorni,
} from '@/lib/dati';
import { dataLunga, suCento } from '@/lib/formato';
import { formattaQuota } from '@/lib/quote';
import { QUOTA_MULTIPLA, QUOTA_RADDOPPIO, schedineDelGiorno } from '@/lib/schedine';

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

            <section className="schedine__regola">
              <h2 className="label">
                <span className="bersaglio" aria-hidden="true" /> Come sono scelte
              </h2>
              <p>
                Fra le {candidate} partite di {dataLunga(data)} su cui ci siamo esposti — le
                altre le abbiamo lasciate in silenzio, e un silenzio non entra in una schedina
                — <strong>il raddoppio</strong> è la coppia con la probabilità più alta fra
                quelle che arrivano comunque a {formattaQuota(QUOTA_RADDOPPIO)}, e{' '}
                <strong>la multipla</strong> è il minor numero di partite che arriva a{' '}
                {formattaQuota(QUOTA_MULTIPLA)}, presa nella composizione più probabile di
                quella lunghezza.
              </p>
              <p>
                <strong>Perché il minor numero.</strong> A parità di quota la probabilità è
                identica: una multipla a {formattaQuota(QUOTA_MULTIPLA)} vale{' '}
                {suCento(1 / QUOTA_MULTIPLA)} su 100 con due partite rischiose come con dieci
                sicure — è aritmetica, non bravura. Quello che cambia con le gambe in più è
                l’errore del modello che si accumula, e le cose che possono andare storte in
                modi che il modello non vede. Quindi meno gambe, a parità di tutto il resto.
              </p>
              <p className="schedine__ipotesi">
                Moltiplicare le probabilità vale se le partite sono indipendenti. Sono partite
                diverse — mai due mercati della stessa, che indipendenti non sarebbero per
                niente — ma restano la stessa giornata e a volte lo stesso campionato. È
                un’ipotesi ragionevole, non un fatto, ed è giusto che tu lo sappia leggendo il
                numero grande.
              </p>
            </section>
          </>
        )}
      </div>
    </>
  );
}
