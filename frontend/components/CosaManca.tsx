'use client';

import { usePassato } from '@/lib/orologio';
import type { Fixture } from '@/lib/tipi';
import { contornoDi } from '@/lib/contorno';

/**
 * QUELLO CHE NON C'E' ANCORA, e quando arrivera'.
 *
 * IL PROBLEMA CHE RISOLVE, misurato. Su 261 partite future il blocco delle
 * formazioni c'e' su 11 su 100, l'arbitro su 5, le stime sui giocatori su 1.
 * Non e' un guasto — quelle cose la fonte le pubblica avvicinandosi al fischio
 * — ma la pagina non lo diceva: chi apriva una partita di dopodomani vedeva
 * una scheda a meta' senza sapere se mancava qualcosa, se era rotto, o se non
 * ci sarebbe mai stato niente.
 *
 * Tre stati indistinguibili, e il lettore lasciato a indovinare quale fosse.
 * Questo blocco ne fa uno solo: «non c'e' ancora, e di solito arriva cosi'».
 *
 * NON COMPARE SU UNA PARTITA GIA' GIOCATA. Li' quello che manca non arrivera'
 * piu', e prometterlo sarebbe peggio del silenzio.
 *
 * NON COMPARE QUANDO C'E' TUTTO. Un blocco che dice «non manca niente» e'
 * rumore: la sua assenza e' gia' il messaggio.
 *
 * I TEMPI SONO MISURATI, NON STIMATI. La mediana delle formazioni lette e' 56
 * ore prima del fischio, il minimo 5 e il massimo 108: si dice «due o tre
 * giorni», che e' vero, invece di «un'ora prima», che sarebbe la risposta di
 * pancia e sarebbe falsa. Sul resto si e' piu' vaghi apposta, perche' su
 * quello non abbiamo ancora una misura.
 */

interface Mancante {
  cosa: string;
  quando: string;
}

export function CosaManca({
  fixture,
  /* L'ora della costruzione, passata dalla pagina: qui dentro non si puo'
     leggere, perche' `lib/dati` e' `server-only` e questo e' un componente
     che gira nel browser. */
  costruzione,
}: {
  fixture: Fixture;
  costruzione: number;
}) {
  /* DUE CONTROLLI, E NON E' UNO DI TROPPO: rispondono a due domande diverse.

     Il RISULTATO e' un fatto scritto nel file, e non ha bisogno di sapere che
     ore sono: se c'e', la partita e' finita e archiviata, e questo blocco non
     compare gia' nell'HTML. Sono la stragrande maggioranza dei casi.

     L'OROLOGIO copre la sola finestra che il risultato non copre: le poche ore
     fra il fischio d'inizio e il momento in cui il risultato entra nei dati.
     Li' il file dice ancora «partita futura» ed e' l'ora a smentirlo. Il
     confronto va fatto NEL BROWSER: qui in pagina un `Date.now()` darebbe
     l'ora della costruzione notturna, non adesso, e una partita in corso
     continuerebbe a promettere una formazione che non arrivera' piu'. */
  const fischio = new Date(fixture.utc_date).getTime();
  const giocata = usePassato(fischio, fischio <= costruzione);
  if (fixture.result || giocata) return null;

  const s = contornoDi(fixture);
  const mancano: Mancante[] = [];

  if (!s?.formazioni) {
    mancano.push({
      cosa: 'Le probabili formazioni',
      quando: 'di solito compaiono due o tre giorni prima della partita',
    });
  }
  // L'ARBITRO NON SI PROMETTE PIU'. Diceva «la designazione esce a pochi
  // giorni dal fischio», ed era una promessa che quasi mai si mantiene: la
  // fonte gratuita lo pubblica DOPO la partita. Misurato il 25 agosto 2026 su
  // La Liga: zero su tutte le partite in programma, undici su sedici fra
  // quelle gia' giocate. Elencarlo fra le cose in arrivo faceva aspettare a
  // vuoto qualcosa che arriva quando non serve piu'.
  if (!s?.giocatori) {
    mancano.push({
      cosa: 'Le stime sui singoli giocatori',
      quando: 'arrivano insieme alle formazioni: senza sapere chi gioca non si possono fare',
    });
  }
  if (!s?.quote?.mercati?.length) {
    mancano.push({
      cosa: 'Gli altri mercati',
      quando: 'gli operatori li aprono avvicinandosi alla partita',
    });
  }

  if (mancano.length === 0) return null;

  return (
    <section className="sezione manca" aria-labelledby="titolo-manca">
      <h2 id="titolo-manca" className="label sezione__titolo">
        <span className="bersaglio" aria-hidden="true" /> Non c’è ancora
      </h2>

      <p className="sezione__lettura">
        Il pronostico qui sopra è completo: si calcola da subito e non cambia perché arriva
        una formazione. Quello che segue è <strong>contorno</strong>, e compare avvicinandosi
        al fischio d’inizio.
      </p>

      <ul className="manca__elenco">
        {mancano.map((m) => (
          <li key={m.cosa} className="manca__voce">
            <span className="manca__cosa">{m.cosa}</span>
            <span className="manca__quando">{m.quando}</span>
          </li>
        ))}
      </ul>

      <p className="sezione__nota">
        Non c’è niente da aspettare a schermo: la pagina si ricostruisce ogni notte, e
        riaprendola più avanti quello che manca sarà qui.
      </p>
    </section>
  );
}
