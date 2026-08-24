import { MARCHIO } from '@/lib/testi';
import { interno } from '@/lib/sito';

/**
 * IL MARCHIO — «CENTRO».
 *
 * Il nome viene da «fare centro»: ciò che il prodotto promette e ciò su cui
 * accetta di essere misurato in pubblico. Il segno è la stessa cosa detta in
 * geometria — un bersaglio ridotto all'osso: quadro esterno a filetto, quadro
 * interno a filetto, centro pieno in vermiglio.
 *
 * PERCHÉ QUADRATI E NON CERCHI. Tutta la pagina è a spigolo vivo — lastre,
 * righe, celle, tag. Un bersaglio circolare sarebbe l'unica curva della
 * schermata, e un elemento firma che non appartiene alla griglia non firma
 * niente. Il quadro concentrico invece ricompare identico a due scale più
 * piccole: come punto elenco di ogni titolo di sezione, e come marca del
 * pronostico più forte della giornata.
 *
 * A 20px il quadro interno e il centro sono ancora due forme distinte: è la
 * ragione per cui gli anelli sono due e non tre.
 *
 * Un solo SVG in linea: nessun raster, nessuna emoji, nessuna libreria di
 * icone. I colori vengono dai token via classe CSS — un attributo di
 * presentazione non risolve `var()`, quindi `fill` sta nel foglio di stile.
 */
export function Marchio({ href }: { href: string }) {
  return (
    <a className="marchio" href={interno(href)} aria-label={`${MARCHIO} — vai alle partite di oggi`}>
      <svg className="marchio__segno" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
        {/* Quadro esterno: filetto di 2, quindi inset di 1 sui bordi. */}
        <rect className="marchio__anello" x="1" y="1" width="30" height="30" />
        <rect className="marchio__anello" x="8" y="8" width="16" height="16" />
        <rect className="marchio__centro" x="13" y="13" width="6" height="6" />
      </svg>
      <span className="marchio__nome">{MARCHIO}</span>
    </a>
  );
}
