/**
 * Voce della lista di controllo di MASTER.md §11:
 * "Nessuna delle parole vietate compare nel bundle".
 *
 * Se una di queste parole finisce in pagina non hai rotto lo stile: hai rotto
 * il prodotto. Il controllo gira dopo il build, sul testo visibile dell'export
 * (script e stili esclusi: lì "edge" e "score" appartengono al framework).
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = fileURLToPath(new URL('../out', import.meta.url));

/** Parole che non devono mai comparire nel testo visibile. */
const VIETATE = [
  /\bvalue bet\b/i,
  /\bedge\b/i,
  /\bROI\b/,
  /\brendiment\w*/i,
  /\bquota consigliata\b/i,
  /\bpuntat[ae]\b/i,
  /\bstake\b/i,
  /\bprofitt\w*/i,
  /\bscommetti su\b/i,
  // Identificatori delle grandezze diagnostiche.
  /\bp_raw\b/i,
  /\bshrink_alpha\b/i,
  /\bsigma\b/i,
  /\bscore\b/i,
];

/**
 * Il guardiano cercava solo i NOMI, e questo lasciava passare la cosa che
 * doveva fermare. `shrink_alpha` non compariva da nessuna parte, ma il suo
 * valore si': «peso della stima 69%» su 21 schede, che e' esattamente la
 * glossa che docs/schema.md da' a quel campo. Un identificatore non e' il
 * problema — nessuno scriverebbe mai `shrink_alpha` in una frase italiana.
 * Il problema e' la GRANDEZZA, comunque la si dica.
 *
 * Di qui la seconda lista: forme, non parole.
 */
const FORME_VIETATE = [
  // La glossa di `shrink_alpha`, in tutte le sue declinazioni.
  /peso della stima/i,
  // Le probabilita' si dicono «N su 100», mai in percentuale: una percentuale
  // in pagina e' quasi sempre una grandezza interna che e' sfuggita.
  // Eccezione legittima: nessuna, oggi.
  /\d+\s*%/,
];

/** Il testo visibile: via script, style, e i tag. */
function testoVisibile(html) {
  return html
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&[a-z]+;/gi, ' ')
    .replace(/\s+/g, ' ');
}

function* htmlDentro(cartella) {
  for (const voce of readdirSync(cartella)) {
    const percorso = join(cartella, voce);
    if (statSync(percorso).isDirectory()) yield* htmlDentro(percorso);
    else if (voce.endsWith('.html')) yield percorso;
  }
}

let trovate = 0;
let pagine = 0;

for (const file of htmlDentro(OUT)) {
  pagine += 1;
  const testo = testoVisibile(readFileSync(file, 'utf8'));
  for (const regola of [...VIETATE, ...FORME_VIETATE]) {
    const trovato = regola.exec(testo);
    if (trovato) {
      const i = Math.max(0, trovato.index - 60);
      console.error(
        `[vietate] ${file.replace(OUT, 'out')}\n` +
          `          «${trovato[0]}» in: …${testo.slice(i, trovato.index + 80).trim()}…`,
      );
      trovate += 1;
    }
  }
}

if (trovate > 0) {
  console.error(`\n[vietate] ${trovate} occorrenze su ${pagine} pagine. Il build non passa.`);
  process.exit(1);
}

console.log(`[vietate] nessuna parola vietata nel testo di ${pagine} pagine.`);
