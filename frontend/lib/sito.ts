/**
 * DOVE VIVE IL SITO, deciso in fase di build.
 *
 * Prima era `https://pronostici.example` cablato in tre punti — `sitemap.ts`,
 * `robots.ts` e `metadataBase` nel layout. Finche' il sito girava solo in
 * locale non si notava, ma pubblicandolo cosi' il sitemap avrebbe dichiarato
 * ai motori di ricerca che l'indirizzo canonico e' un dominio che non esiste:
 * il modo piu' efficace di non farsi trovare, e silenzioso.
 *
 * `NEXT_PUBLIC_SITO` lo decide chi pubblica. Il valore predefinito resta il
 * segnaposto apposta: se qualcuno pubblica senza impostarlo, l'errore si vede
 * subito nel sitemap invece di sembrare un indirizzo plausibile e sbagliato.
 */
export const SITO = (process.env.NEXT_PUBLIC_SITO ?? 'https://pronostici.example').replace(
  /\/+$/,
  '',
);

/**
 * Il prefisso quando il sito non sta alla radice del dominio.
 *
 * GitHub Pages serve da `utente.github.io/nome-repo/`, quindi ogni percorso
 * assoluto — fogli di stile, script, collegamenti interni — va spostato sotto
 * quel prefisso, altrimenti si ottiene una pagina bianca con tutti i 404.
 * Su un dominio dedicato resta vuoto e non cambia niente.
 */
export const PREFISSO = (process.env.NEXT_PUBLIC_PREFISSO ?? '').replace(/\/+$/, '');

/** L'indirizzo pubblico completo di un percorso interno. */
export function indirizzo(percorso: string): string {
  const p = percorso.startsWith('/') ? percorso : `/${percorso}`;
  return `${SITO}${PREFISSO}${p}`;
}

/**
 * Un collegamento interno, col prefisso davanti quando serve.
 *
 * Il sito non usa `next/link`: sono `<a>` normali, coerenti con un export
 * statico che non ha routing lato client. Ma `basePath` di Next prefissa da
 * solo soltanto i suoi `<Link>` e gli asset — un `<a href="/progressi/">`
 * resta com'e' e, servito da `utente.github.io/nome-repo/`, porta fuori dal
 * sito. Senza prefisso questa funzione non fa niente.
 */
export function interno(percorso: string): string {
  // Passa intatto tutto cio' che non e' un percorso interno: indirizzi
  // assoluti, ancore, `mailto:` e `tel:`. Cosi' si puo' applicare a ogni
  // `href` senza distinguere caso per caso — ed e' importante, perche' un
  // collegamento dimenticato non si vede in locale: si vede in produzione,
  // come un 404.
  if (!percorso.startsWith('/') || percorso.startsWith('//')) return percorso;
  // Idempotente: un percorso gia' prefissato torna com'e'. Serve davvero —
  // `Marchio` applica il prefisso al valore che riceve, e chi lo chiama glielo
  // passa gia' prefissato: senza questa riga esce `/pronostici/pronostici/`,
  // che e' un 404 trovato percorrendo il sito, non leggendolo.
  if (PREFISSO && (percorso === PREFISSO || percorso.startsWith(`${PREFISSO}/`))) {
    return percorso;
  }
  return `${PREFISSO}${percorso}`;
}
