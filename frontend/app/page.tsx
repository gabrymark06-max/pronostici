import type { Metadata } from 'next';

import { etichettaPartite, VistaGiorno } from '@/components/VistaGiorno';
import { giornoDiApertura, leggiGiorno } from '@/lib/dati';
import { dataLungaMaiuscola } from '@/lib/formato';
import { fraseSilenziDelGiorno, MARCHIO } from '@/lib/testi';

/**
 * `/` MOSTRA LE PARTITE, non un rimando.
 *
 * Fino al 25 agosto 2026 questa pagina era un `<meta refresh>` verso
 * `/giorno/<data>/` con un link sotto come ripiego: in export statico non
 * esiste un redirect di server, e quella sembrava l'unica strada. Ma il costo
 * lo pagava chi apriva il sito — una schermata quasi bianca con una riga sola,
 * per il tempo che il browser ci metteva a seguire il refresh. La prima cosa
 * che il prodotto diceva era «qui non c'e' niente».
 *
 * Il contenuto e' lo stesso a due indirizzi, e questo va dichiarato: il
 * canonical punta al giorno, che resta l'originale. La data e' quella della
 * COSTRUZIONE — su un sito statico non ce n'e' un'altra — e si sposta ogni
 * notte, insieme al resto.
 */
export function generateMetadata(): Metadata {
  const data = giornoDiApertura();
  const giorno = data ? leggiGiorno(data) : null;
  if (!data || !giorno) return { title: MARCHIO };

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
    openGraph: { title: titolo, description: descrizione, type: 'website', siteName: MARCHIO },
  };
}

export default function Home() {
  const data = giornoDiApertura();

  if (!data) {
    return (
      <div className="colonna colonna--lista">
        <div className="giorno-vuoto">
          <p>Non ci sono ancora giornate pubblicate.</p>
          <p>I pronostici compaiono qui quando il calcolo della notte ha girato.</p>
        </div>
      </div>
    );
  }

  return <VistaGiorno data={data} />;
}
