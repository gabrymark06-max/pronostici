import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { CorpoSchedine } from '@/components/CorpoSchedine';
import { giorniDisponibili, leggiGiorno } from '@/lib/dati';
import { dataLungaMaiuscola } from '@/lib/formato';
import { MARCHIO } from '@/lib/testi';

/**
 * IL PRONOSTICO DEL GIORNO — due schedine, una pagina per data.
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
  if (!leggiGiorno(data)) notFound();
  return <CorpoSchedine data={data} />;
}
