/**
 * COME SI LEGGE — tre riquadri con icona, in cima alla giornata.
 *
 * Sostituisce il paragrafo di prosa che spiegava il metodo in cinque righe di
 * testo corrente. Un blocco di testo in cima a uno strumento di consultazione
 * non viene letto: viene scavalcato. Tre riquadri con un'icona, un titolo
 * corto e una riga sola si guardano invece di leggersi, ed e' l'unica forma in
 * cui una spiegazione sopravvive in cima a una lista.
 *
 * Le icone sono SVG in linea con `stroke` a --icon-stroke: nessuna libreria,
 * nessuna emoji, nessun raster. Sono decorative (`aria-hidden`), perche' il
 * titolo accanto dice gia' tutto a chi ascolta.
 */

function IconaPunteggio() {
  return (
    <svg
      className="riquadro__icona"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="var(--icon-stroke)"
      strokeLinecap="square"
      aria-hidden="true"
    >
      <path d="M3 17h18" />
      <path d="M3 17V7" />
      <path d="M8 17v-4" />
      <path d="M13 17V9" />
      <path d="M18 17v-6" />
    </svg>
  );
}

function IconaSilenzio() {
  return (
    <svg
      className="riquadro__icona"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="var(--icon-stroke)"
      strokeLinecap="square"
      aria-hidden="true"
    >
      <path d="M4 12h5" />
      <path d="M15 12h5" />
      <path d="M11 9v6" />
      <path d="M13 9v6" />
    </svg>
  );
}

function IconaStorico() {
  return (
    <svg
      className="riquadro__icona"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="var(--icon-stroke)"
      strokeLinecap="square"
      aria-hidden="true"
    >
      <path d="M4 20V4" />
      <path d="M4 20h16" />
      <path d="M8 16l4-6 4 3 4-7" />
    </svg>
  );
}

export function ComeSiLegge() {
  return (
    <section className="spiegazione" aria-label="Come si legge questa pagina">
      <div className="riquadro">
        <IconaPunteggio />
        <h2 className="riquadro__titolo">Il punteggio va da 0 a 100</h2>
        <p className="riquadro__testo">
          È la probabilità che il pronostico si avveri, non un voto. <b>90</b> vuol dire
          novanta volte su cento. Sotto la cifra, il tratto mostra quanto siamo sicuri di
          quella stima.
        </p>
      </div>

      <div className="riquadro">
        <IconaSilenzio />
        <h2 className="riquadro__titolo">A volte non diciamo niente</h2>
        <p className="riquadro__testo">
          Su circa una partita su quattro nessun mercato supera il criterio che abbiamo
          scritto <b>prima</b> di guardare le partite. In quel caso tacere è la risposta, non
          un buco da riempire.
        </p>
      </div>

      <div className="riquadro">
        <IconaStorico />
        <h2 className="riquadro__titolo">Accanto c&rsquo;è quanto ci prendiamo</h2>
        <p className="riquadro__testo">
          Ogni pronostico porta la sua fascia e quante volte, storicamente, pronostici di
          quella fascia si sono avverati. Il dato viene da un test su migliaia di partite
          passate.
        </p>
      </div>
    </section>
  );
}
