import { nomeCampionato, paeseDi } from '@/lib/campionati';
import type { RecordFascia } from '@/lib/fascia';
import { tace, type Fixture } from '@/lib/tipi';

import { ancoraCampionato } from './ancore';
import { Bandiera } from './Bandiera';
import { RigaPartita } from './RigaPartita';

/**
 * IL CAMPIONATO come GRUPPO RICHIUDIBILE.
 *
 * `<details>`/`<summary>` nativi, non un accordion in JavaScript. Il sito è
 * statico: un gruppo che si apre solo dopo l'idratazione sarebbe un gruppo che
 * a volte non si apre. Il nativo funziona senza JavaScript, risponde a Invio e
 * a Spazio, annuncia da solo il proprio stato, e tiene il contenuto nel DOM
 * per i motori di ricerca.
 *
 * Aperto di default: chi apre la pagina vuole le partite, non un indice.
 *
 * LE TESTATE CHIUSE STANNO ATTACCATE. Quando si richiudono due campionati di
 * fila, le due testate devono toccarsi e formare un elenco continuo: erano
 * separate da uno stacco che, senza le righe in mezzo, lasciava due strisce di
 * fondo pagina sospese. Lo stacco fra i gruppi è quindi un `border-top` sulla
 * lista delle partite, non un margine fra i blocchi — così esiste solo quando
 * ci sono partite da separare.
 *
 * La testata è appiccicata sotto il calendario: durante lo scorrimento sai
 * sempre in che campionato sei. Porta la bandiera del paese — ciò che rende un
 * campionato riconoscibile prima di leggerne il nome — il nome, il paese, e un
 * conteggio che nomina anche i silenzi: un campionato in cui taciamo su
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
  const paese = paeseDi(codice);

  /* La giornata si mostra solo se è la stessa per tutte le partite del gruppo:
     due giornate diverse nello stesso blocco renderebbero il numero una mezza
     verità. */
  const giornate = new Set(partite.map((p) => p.matchday).filter((g) => g != null));
  const giornata = giornate.size === 1 ? [...giornate][0] : null;

  return (
    <details className="lega" id={ancoraCampionato(codice)} open>
      <summary className="lega__somma">
        <span className="lega__freccia" aria-hidden="true">
          ›
        </span>
        <Bandiera competizione={codice} />
        <span className="lega__titolo">
          {paese ? <span className="lega__paese">{paese}</span> : null}
          <span className="lega__nome">{nomeCampionato(codice)}</span>
        </span>
        <span className="lega__meta">
          {giornata != null ? <span className="lega__giornata">Giornata {giornata}</span> : null}
          <span className="lega__conteggio">
            {partite.length === 1 ? '1 partita' : `${partite.length} partite`}
            {silenzi > 0 ? (
              /* Un elemento suo, non una stringa: sotto i 600px sparisce per
                 lasciare leggere il nome del campionato, e una stringa non si
                 puo' nascondere a meta'. */
              <span className="lega__silenzi"> · {silenzi} in silenzio</span>
            ) : null}
          </span>
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
