/**
 * LA BANDIERA DEL CAMPIONATO.
 *
 * Il secondo elemento figurativo del prodotto dopo gli stemmi, e la ragione
 * per cui un campionato si riconosce prima di leggerne il nome. In un
 * prodotto la cui interfaccia e' acromatica per scelta, bandiere e stemmi
 * sono l'unico colore della pagina — e non e' un caso: sono l'unica cosa
 * che appartiene al calcio e non a noi.
 *
 * SVG in linea, geometrie piene, nessun file da scaricare e nessuna
 * dipendenza: sono undici forme, e disegnarle costa meno che servirle.
 *
 * Decorative: il nome del campionato sta accanto, in testo reale. Quindi
 * `aria-hidden` e nessun titolo — una bandiera annunciata da uno screen
 * reader accanto al nome che gia' la dice sarebbe una ripetizione.
 */

/** Stella a cinque punte, raggio 1, centrata nell'origine. */
const STELLA =
  'M0,-1 L0.2245,-0.3091 L0.9511,-0.309 L0.3633,0.118 L0.5878,0.809 ' +
  'L0,0.382 L-0.5878,0.809 L-0.3633,0.118 L-0.9511,-0.309 L-0.2245,-0.3091 Z';

function Stella({ x, y, r, colore }: { x: number; y: number; r: number; colore: string }) {
  return <path d={STELLA} fill={colore} transform={`translate(${x} ${y}) scale(${r})`} />;
}

/** Le geometrie, una per competizione. viewBox 24×16 per tutte. */
const DISEGNI: Record<string, React.ReactNode> = {
  /* Italia */
  SA: (
    <>
      <rect width="8" height="16" fill="#008C45" />
      <rect x="8" width="8" height="16" fill="#F4F5F0" />
      <rect x="16" width="8" height="16" fill="#CD212A" />
    </>
  ),

  /* Inghilterra — croce di San Giorgio */
  PL: (
    <>
      <rect width="24" height="16" fill="#FFFFFF" />
      <rect x="10" width="4" height="16" fill="#CE1124" />
      <rect y="6" width="24" height="4" fill="#CE1124" />
    </>
  ),

  /* Spagna */
  PD: (
    <>
      <rect width="24" height="16" fill="#AA151B" />
      <rect y="4" width="24" height="8" fill="#F1BF00" />
    </>
  ),

  /* Germania */
  BL1: (
    <>
      <rect width="24" height="5.34" fill="#111111" />
      <rect y="5.34" width="24" height="5.33" fill="#DD0000" />
      <rect y="10.67" width="24" height="5.33" fill="#FFCE00" />
    </>
  ),

  /* Francia */
  FL1: (
    <>
      <rect width="8" height="16" fill="#002654" />
      <rect x="8" width="8" height="16" fill="#F4F5F0" />
      <rect x="16" width="8" height="16" fill="#ED2939" />
    </>
  ),

  /* Paesi Bassi */
  DED: (
    <>
      <rect width="24" height="5.34" fill="#AE1C28" />
      <rect y="5.34" width="24" height="5.33" fill="#F4F5F0" />
      <rect y="10.67" width="24" height="5.33" fill="#21468B" />
    </>
  ),

  /* Portogallo */
  PPL: (
    <>
      <rect width="24" height="16" fill="#DA291C" />
      <rect width="9.6" height="16" fill="#046A38" />
      <circle cx="9.6" cy="8" r="3.4" fill="#FFE900" />
      <circle cx="9.6" cy="8" r="2" fill="#DA291C" />
    </>
  ),

  /* Brasile */
  BSA: (
    <>
      <rect width="24" height="16" fill="#009C3B" />
      <path d="M12 1.6 L22.4 8 L12 14.4 L1.6 8 Z" fill="#FFDF00" />
      <circle cx="12" cy="8" r="3.1" fill="#002776" />
    </>
  ),

  /* Champions League — il pallone stellato, ridotto all'osso */
  CL: (
    <>
      <rect width="24" height="16" fill="#08194F" />
      <circle cx="12" cy="8" r="5.4" fill="none" stroke="#F4F5F0" strokeWidth="1.1" />
      <Stella x={12} y={8} r={2.6} colore="#F4F5F0" />
    </>
  ),

  /* Europei — il cerchio di stelle, in cinque invece che in dodici: a 24px
     dodici stelle diventano una macchia gialla. */
  EC: (
    <>
      <rect width="24" height="16" fill="#003399" />
      <Stella x={12} y={3.4} r={1.5} colore="#FFCC00" />
      <Stella x={16.9} y={6.6} r={1.5} colore="#FFCC00" />
      <Stella x={15} y={12.2} r={1.5} colore="#FFCC00" />
      <Stella x={9} y={12.2} r={1.5} colore="#FFCC00" />
      <Stella x={7.1} y={6.6} r={1.5} colore="#FFCC00" />
    </>
  ),

  /* Mondiali — il globo */
  WC: (
    <>
      <rect width="24" height="16" fill="#1B3A63" />
      <circle cx="12" cy="8" r="6" fill="none" stroke="#F4F5F0" strokeWidth="1" />
      <ellipse cx="12" cy="8" rx="2.6" ry="6" fill="none" stroke="#F4F5F0" strokeWidth="1" />
      <line x1="6" y1="8" x2="18" y2="8" stroke="#F4F5F0" strokeWidth="1" />
    </>
  ),
};

/* La Championship e' inglese quanto la Premier: stessa bandiera. */
DISEGNI.ELC = DISEGNI.PL;

export function Bandiera({ competizione }: { competizione: string }) {
  const disegno = DISEGNI[competizione];

  return (
    <svg
      className="bandiera"
      viewBox="0 0 24 16"
      width={24}
      height={16}
      aria-hidden="true"
      focusable="false"
    >
      {disegno ?? <rect width="24" height="16" fill="currentColor" opacity="0.25" />}
      {/* Il filetto interno: senza, una bandiera quasi bianca (Inghilterra)
          scompare sul tema chiaro. */}
      <rect
        x="0.5"
        y="0.5"
        width="23"
        height="15"
        fill="none"
        stroke="currentColor"
        strokeOpacity="0.45"
        strokeWidth="1"
      />
    </svg>
  );
}
