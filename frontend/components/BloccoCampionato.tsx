import { nomeCampionato } from '@/lib/campionati';
import type { RecordFascia } from '@/lib/fascia';
import { tace, type Fixture } from '@/lib/tipi';

import { Bandiera } from './Bandiera';
import { RigaPartita } from './RigaPartita';
import { ancoraCampionato } from './ancore';

/**
 * IL CAMPIONATO come GRUPPO RICHIUDIBILE.
 *
 * `<details>`/`<summary>` nativi, non un accordion in JavaScript. Il sito è
 * statico: un gruppo che si apre solo dopo l'idratazione sarebbe un gruppo
 * che a volte non si apre. Il nativo funziona senza JavaScript, risponde a
 * Invio e a Spazio, annuncia da solo il proprio stato («compresso» /
 * «espanso») e tiene il contenuto nel DOM per i motori di ricerca.
 *
 * Aperto di default: chi apre la pagina vuole le partite, non un indice.
 * Chiuderlo è per chi non segue quel campionato, ed è una scelta che dura
 * quanto la visita — non la persistiamo, perché persistere una preferenza
 * senza un posto dove dirlo è una sorpresa al ritorno.
 *
 * La testata è appiccicata sotto la barra dei giorni: durante lo scorrimento
 * sai sempre in che campionato sei. Porta la bandiera del paese — il secondo
 * elemento figurativo del prodotto dopo gli stemmi, e ciò che rende un
 * campionato riconoscibile prima di leggerne il nome — il nome in Newsreader,
 * e il conteggio, che nomina anche i silenzi: un campionato in cui taciamo su
 * quattro partite su sette lo dice in testa, non lo fa scoprire riga per riga.
 */
export function BloccoCampionato({
  codice,
  partite,
  crest,
  record,
}: {
  codice: string;
  partite: Fixture[];
  crest: (url: string | null) => string | null;
  record: (fixture: Fixture) => RecordFascia | null;
}) {
  const silenzi = partite.filter(tace).length;

  /* La giornata si mostra solo se è la stessa per tutte le partite del
     gruppo: due giornate diverse nello stesso blocco renderebbero il numero
     una mezza verità. */
  const giornate = new Set(partite.map((p) => p.matchday).filter((g) => g != null));
  const giornata = giornate.size === 1 ? [...giornate][0] : null;

  return (
    <details className="lega" id={ancoraCampionato(codice)} open>
      <summary className="lega__somma pad-lista">
        <span className="lega__freccia" aria-hidden="true">
          ›
        </span>
        <Bandiera competizione={codice} />
        <span className="lega__nome">{nomeCampionato(codice)}</span>
        <span className="lega__meta">
          {giornata != null ? (
            <span className="lega__giornata">Giornata {giornata}</span>
          ) : null}
          <span className="lega__conteggio">{conteggio(partite.length, silenzi)}</span>
        </span>
      </summary>

      <ul className="lega__partite">
        {partite.map((fixture) => (
          <li key={fixture.match_id}>
            <RigaPartita fixture={fixture} crest={crest} record={record(fixture)} />
          </li>
        ))}
      </ul>
    </details>
  );
}

function conteggio(totale: number, silenzi: number): string {
  const partite = totale === 1 ? '1 partita' : `${totale} partite`;
  if (silenzi === 0) return partite;
  return `${partite} · ${silenzi} in silenzio`;
}
