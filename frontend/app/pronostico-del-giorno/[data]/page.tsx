import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { Calendario } from '@/components/Calendario';
import { Schedina } from '@/components/Schedina';
import {
  finestraGiorni,
  giorniDisponibili,
  giorniVicini,
  leggiGiorno,
  manifestoCrest,
  riepilogoGiorni,
} from '@/lib/dati';
import { dataLunga, dataLungaMaiuscola, suCento } from '@/lib/formato';
import { formattaQuota } from '@/lib/quote';
import { QUOTA_MULTIPLA, QUOTA_RADDOPPIO, schedineDelGiorno } from '@/lib/schedine';
import { MARCHIO } from '@/lib/testi';

/**
 * IL PRONOSTICO DEL GIORNO — due schedine, una per data.
 *
 * PERCHE' UNA PAGINA PER GIORNO e non una pagina sola che cambia. Su questo
 * sito una cosa pubblicata resta dov'e' con la sua data: e' l'intera ragione
 * per cui il registro vale qualcosa. Una schedina del giorno che si riscrive
 * ogni notte sarebbe l'unica pagina del prodotto senza memoria — e guarda caso
 * proprio quella che altrove viene usata per rivendicare risultati che nessuno
 * puo' piu' verificare. Qui le vecchie restano, con scritto com'e' andata.
 *
 * COSA E' DERIVATO E COSA E' DATO. Le due schedine non sono un pronostico
 * nuovo: sono una combinazione di pronostici gia' scritti, scelti da una
 * regola deterministica (lib/schedine.ts). Ricostruire la pagina sugli stessi
 * dati da' le stesse due schedine. Per questo si calcolano in fase di build e
 * non esiste un file `schedine.json`: non c'e' niente da congelare che non sia
 * gia' congelato nelle partite.
 */
export function generateStaticParams() {
  return giorniDisponibili().map((data) => ({ data }));
}

export const dynamicParams = false;

type Props = { params: Promise<{ data: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { data } = await params;
  const giorno = leggiGiorno(data);
  if (!giorno) return { title: `Pronostico del ${data}` };

  const titolo = `Pronostico del giorno — ${dataLungaMaiuscola(data)}`;
  const descrizione =
    'Due schedine costruite sui pronostici del giorno: un raddoppio a due partite e una ' +
    'multipla che arriva a 5,00 con il minor numero di partite possibile. Con scritto ' +
    'quante volte su cento escono tutte intere.';

  return {
    title: titolo,
    description: descrizione,
    alternates: { canonical: `/pronostico-del-giorno/${data}/` },
    openGraph: { title: titolo, description: descrizione, type: 'website', siteName: MARCHIO },
  };
}

export default async function PaginaSchedine({ params }: Props) {
  const { data } = await params;
  const giorno = leggiGiorno(data);
  if (!giorno) notFound();

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
            Due combinazioni dei pronostici di {dataLunga(data)}, scelte da una regola e non
            a mano. Il numero grande di ognuna è <strong>quante volte su cento esce tutta
            intera</strong>, non la quota: le due cose sono lo stesso numero al contrario —
            la nostra quota è uno diviso la probabilità — e fra le due abbiamo messo grande
            quella che cala quando la scommessa peggiora.
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
                altre le abbiamo lasciate in silenzio, e un silenzio non entra in una
                schedina — <strong>il raddoppio</strong> è la coppia con la probabilità più
                alta fra quelle che arrivano comunque a{' '}
                {formattaQuota(QUOTA_RADDOPPIO)}, e <strong>la multipla</strong> è il minor
                numero di partite che arriva a {formattaQuota(QUOTA_MULTIPLA)}, presa nella
                composizione più probabile di quella lunghezza.
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
