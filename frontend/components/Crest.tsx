'use client';

import { useRef, useState } from 'react';

/**
 * Spazio riservato con width/height espliciti: CLS zero, niente entra o si
 * sposta dopo il primo paint.
 *
 * Se il crest non carica si ripiega sul `tla` in un quadrato 24px mono con
 * filetto: mai un'icona di immagine rotta, mai uno spazio che collassa.
 * Il controllo su `naturalWidth` serve perché un errore avvenuto PRIMA
 * dell'idratazione non farebbe mai scattare `onError`.
 *
 * `alt=""`: il crest è decorativo, il nome della squadra è testo lì accanto.
 */
export function Crest({ src, tla }: { src: string | null; tla: string }) {
  const [rotto, setRotto] = useState(src === null);
  const riferimento = useRef<HTMLImageElement>(null);

  if (rotto || !src) {
    return (
      <span className="crest crest--ripiego" aria-hidden="true">
        {tla}
      </span>
    );
  }

  return (
    <span className="crest">
      <img
        ref={riferimento}
        src={src}
        alt=""
        width={24}
        height={24}
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
