import { MARCHIO } from '@/lib/testi';

/**
 * IL MARCHIO — «Novanta».
 *
 * Il nome viene da due parti dello stesso prodotto: la firma numerica («90 su
 * 100», la sola forma in cui una probabilita' entra in pagina) e i novanta
 * minuti. Non e' una parola inventata per sembrare un marchio: e' l'unita' di
 * misura del sito.
 *
 * IL SEGNO e' l'elemento firma applicato a se stesso. La riga di taratura —
 * la scala a tacche che apre ogni blocco in cui il prodotto si espone — viene
 * chiusa dentro un quadro pieno e ridotta a sette graduazioni in negativo.
 * L'ultima e' alta il triplo delle altre: e' l'estremo alto della scala, il
 * solo punto in cui questo prodotto parla, ed e' la stessa geometria che sulla
 * scheda porta la cifra.
 *
 * Un solo SVG in linea: nessun raster, nessuna emoji, nessuna libreria di
 * icone. I due colori vengono dai token via classe CSS — un attributo di
 * presentazione non risolve `var()`, quindi `fill` sta nel foglio di stile e
 * non qui.
 */
export function Marchio({ href }: { href: string }) {
  return (
    <a className="marchio" href={href} aria-label={`${MARCHIO} — vai al giorno di apertura`}>
      <svg className="marchio__segno" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
        <rect className="marchio__quadro" x="0" y="0" width="32" height="32" />
        <g className="marchio__tacche">
          <rect x="3" y="13" width="2" height="6" />
          <rect x="7" y="13" width="2" height="6" />
          <rect x="11" y="13" width="2" height="6" />
          <rect x="15" y="13" width="2" height="6" />
          <rect x="19" y="13" width="2" height="6" />
          <rect x="23" y="13" width="2" height="6" />
          <rect x="27" y="7" width="2" height="18" />
        </g>
      </svg>
      <span className="marchio__nome">{MARCHIO}</span>
    </a>
  );
}
