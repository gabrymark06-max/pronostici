import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { etichettaPartite, VistaGiorno } from '@/components/VistaGiorno';
import { giorniDisponibili, leggiGiorno } from '@/lib/dati';
import { dataLungaMaiuscola } from '@/lib/formato';
import { fraseSilenziDelGiorno, MARCHIO } from '@/lib/testi';

/** Tutte le rotte sono pre-renderizzate: nessun runtime, deep-linking obbligatorio. */
export function generateStaticParams() {
  return giorniDisponibili().map((data) => ({ data }));
}

export const dynamicParams = false;

type Props = { params: Promise<{ data: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { data } = await params;
  const giorno = leggiGiorno(data);
  if (!giorno) return { title: `Partite del ${data}` };

  /* `etichettaPartite`, non `${total} partite`: nei giorni con una sola
     partita il titolo diceva «1 partite», e quel titolo e' anche quello che
     compare nei risultati di ricerca. */
  const titolo = `${dataLungaMaiuscola(data)}: ${etichettaPartite(giorno.total)}`;
  const descrizione = `${fraseSilenziDelGiorno(
    giorno.silence_count,
    giorno.total,
  )} Un pronostico per partita, con la probabilità, il prezzo dove l’abbiamo trovato e quante volte pronostici così si sono avverati.`;

  return {
    title: titolo,
    description: descrizione,
    alternates: { canonical: `/giorno/${data}/` },
    /* `siteName` va ripetuto qui: l'oggetto openGraph della pagina SOSTITUISCE
       quello della radice, non ci si fonde, e senza questa riga og:site_name
       non finisce nell'HTML di nessuna pagina reale. */
    openGraph: { title: titolo, description: descrizione, type: 'website', siteName: MARCHIO },
  };
}

export default async function PaginaGiorno({ params }: Props) {
  const { data } = await params;
  if (!leggiGiorno(data)) notFound();
  return <VistaGiorno data={data} />;
}
