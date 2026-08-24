/**
 * Con i profili spenti non deve restare in pagina nessun modulo da compilare.
 *
 * `lib/profilo.ts` promette che senza `NEXT_PUBLIC_API_PROFILI` non finiscono
 * «pagine dei profili negli indirizzi pubblicati». La voce d'accesso spariva
 * davvero, ma l'export continuava a contenere `/accedi` con due campi e un
 * bottone: un modulo che, senza un indirizzo a cui parlare, non poteva fare
 * niente. Su un sito pubblico un modulo morto e' peggio di una pagina assente,
 * perche' chi lo compila crede di aver fatto qualcosa.
 *
 * In CI i profili sono sempre spenti — `.env.local` non e' nel repository —
 * quindi li' questo controllo gira sempre, ed e' li' che serve.
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = fileURLToPath(new URL('../out', import.meta.url));
const PAGINE = [
  'accedi',
  'registrati',
  'profilo',
  'recupero',
  'recupero/conferma',
  'verifica',
];

/**
 * Se i profili siano accesi si legge dove lo legge Next.
 *
 * `NEXT_PUBLIC_API_PROFILI` arriva quasi sempre da `.env.local`, che carica
 * Next e non node: guardare solo `process.env` darebbe «spenti» su ogni build
 * locale, e il controllo fallirebbe proprio quando le pagine ci sono per
 * ragioni giuste. Dedurlo dal sito costruito non si puo': la navigazione non
 * ha nessuna voce d'accesso da cui accorgersene.
 */
function indirizzoApi() {
  if (process.env.NEXT_PUBLIC_API_PROFILI !== undefined) {
    return process.env.NEXT_PUBLIC_API_PROFILI.trim();
  }
  for (const nome of ['.env.local', '.env']) {
    const file = fileURLToPath(new URL('../' + nome, import.meta.url));
    if (!existsSync(file)) continue;
    for (const riga of readFileSync(file, 'utf8').split(/\r?\n/)) {
      const trovato = riga.match(/^\s*NEXT_PUBLIC_API_PROFILI\s*=\s*(.*)$/);
      if (trovato) return trovato[1].trim().replace(/^["']|["']$/g, '');
    }
  }
  return '';
}

if (indirizzoApi() !== '') {
  console.log('[profili] accesi: controllo saltato.');
  process.exit(0);
}

const colpevoli = [];
for (const pagina of PAGINE) {
  const file = join(OUT, pagina, 'index.html');
  if (!existsSync(file)) continue;
  const html = readFileSync(file, 'utf8');
  const campi = (html.match(/<input/g) ?? []).length;
  const invii = (html.match(/type="submit"/g) ?? []).length;
  if (campi > 0 || invii > 0) {
    colpevoli.push('/' + pagina + ' — ' + campi + ' campi, ' + invii + ' bottoni di invio');
  }
}

if (colpevoli.length > 0) {
  console.error('[profili] moduli pubblicati con i profili spenti:');
  for (const c of colpevoli) console.error('  ' + c);
  console.error('Manca `soloSeProfiliAccesi()` in cima al componente di pagina.');
  process.exit(1);
}

console.log('[profili] spenti: nessun modulo pubblicato su ' + PAGINE.length + ' pagine.');
