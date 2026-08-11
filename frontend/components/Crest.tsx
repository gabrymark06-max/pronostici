'use client';

import { useRef, useState } from 'react';

/**
 * LO STEMMA.
 *
 * E' l'unico raster del prodotto e l'unico elemento figurativo: in una lista
 * di calcio e' cio' che fa fermare l'occhio su una riga invece che su
 * un'altra, quindi va letto, non intuito.
 *
 * Storia delle dimensioni, perche' e' una decisione e non un default: 24px
 * con una lastra piena dietro (la lastra li trasformava in tasselli mal
 * ritagliati), poi 30px affiancati a coppie — e affiancati due stemmi da
 * 30px si toccano e le due squadre diventano una macchia sola. Adesso sono
 * 28px nella lista e 52px sulla scheda, ma soprattutto sono IMPILATI: uno
 * per riga, accanto al proprio nome. E' la forma che da' a ognuno il suo
 * spazio, ed e' anche quella che chi guarda il calcio conosce gia'.
 *
 * Spazio riservato con width/height espliciti: CLS zero, niente entra o si
 * sposta dopo il primo paint.
 *
 * Se lo stemma non carica si ripiega sulla sigla della squadra in un
 * quadrato con filetto: mai un'icona di immagine rotta, mai uno spazio che
 * collassa. Il controllo su `naturalWidth` serve perche' un errore avvenuto
 * PRIMA dell'idratazione non farebbe mai scattare `onError`.
 *
 * `alt=""`: lo stemma e' decorativo, il nome della squadra e' testo lì
 * accanto.
 */
export function Crest({
  src,
  tla,
  grande = false,
}: {
  src: string | null;
  tla: string;
  grande?: boolean;
}) {
  const [rotto, setRotto] = useState(src === null);
  const riferimento = useRef<HTMLImageElement>(null);

  const classe = grande ? 'crest crest--scheda' : 'crest';
  const lato = grande ? 52 : 28;

  if (rotto || !src) {
    return (
      <span className={`${classe} crest--ripiego`} aria-hidden="true">
        {tla}
      </span>
    );
  }

  return (
    <span className={classe}>
      <img
        ref={riferimento}
        src={src}
        alt=""
        width={lato}
        height={lato}
        loading="lazy"
        decoding="async"
        onError={() => setRotto(true)}
        onLoad={() => {
          if (riferimento.current && riferimento.current.naturalWidth === 0) setRotto(true);
        }}
      />
    </span>
  );
}
