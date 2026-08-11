/**
 * I token hanno UNA fonte di verità: design-system/pronostici/tokens.css.
 * Questo script li copia in styles/tokens.css (per il bundler) e, con --check,
 * fallisce se le due copie hanno divergito. Il build non parte se sono diverse:
 * è l'unico modo perché "nessun hex grezzo nei componenti" resti vero nel tempo.
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const here = fileURLToPath(new URL('.', import.meta.url));
const sorgente = new URL('../../design-system/pronostici/tokens.css', import.meta.url);
const destinazione = new URL('../styles/tokens.css', import.meta.url);

const intestazione = `/* GENERATO da scripts/sync-tokens.mjs — non modificare a mano.
   Fonte di verità: design-system/pronostici/tokens.css */\n`;

if (!existsSync(sorgente)) {
  console.error(`[token] sorgente mancante: ${fileURLToPath(sorgente)}`);
  process.exit(1);
}

const atteso = intestazione + readFileSync(sorgente, 'utf8');
const controlla = process.argv.includes('--check');

/**
 * Il confronto ignora la forma dei fine riga.
 *
 * Con `core.autocrlf = true` — il default di Git su Windows — la copia di
 * lavoro ha CRLF mentre questo script costruisce l'intestazione con `\n`.
 * I due file avevano contenuto IDENTICO e differivano di due byte: bastava a
 * far uscire `npm run build` con 1 su qualunque clone Windows, cioe' sulla
 * piattaforma primaria del progetto. Su Linux il checkout e' LF e passava,
 * quindi nessuna macchina di integrazione lo avrebbe mai visto.
 *
 * Quello che il controllo deve garantire e' che i token spediti al bundler
 * siano gli stessi del design system: un a-capo non e' un token.
 */
const normalizza = (testo) => testo.replace(/\r\n/g, '\n');

if (controlla) {
  const attuale = existsSync(destinazione) ? readFileSync(destinazione, 'utf8') : '';
  if (normalizza(attuale) !== normalizza(atteso)) {
    console.error(
      '[token] styles/tokens.css non corrisponde al design system.\n' +
        '        Esegui: npm run sync:tokens',
    );
    process.exit(1);
  }
  console.log('[token] styles/tokens.css allineato al design system.');
} else {
  writeFileSync(destinazione, atteso, 'utf8');
  console.log(`[token] scritto ${fileURLToPath(destinazione).replace(here, '../')}`);
}
