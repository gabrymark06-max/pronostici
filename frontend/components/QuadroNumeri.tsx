import type { RecordFascia } from '@/lib/fascia';
import { decimale, intero, suCento, testoPulito } from '@/lib/formato';
import type { FixtureConPronostico, Pronostico } from '@/lib/tipi';

/**
 * COME CI SIAMO ARRIVATI — il quadro dei numeri della scheda.
 *
 * SOSTITUISCE quattro blocchi che erano tutti la stessa cosa: una riga di
 * taratura, un occhiello, e sotto un paragrafo di prosa. Uno dopo l'altro
 * pesavano uguale, quindi non c'era gerarchia; ed erano prosa, quindi non si
 * guardavano, si leggevano — o piu' spesso non si leggevano affatto.
 *
 * E RIDUCE LE RIPETIZIONI. La stessa probabilita' compariva tre volte nella
 * stessa schermata con parole diverse: la cifra, la riga di definizione, e poi
 * di nuovo dentro «Perche'». La banda compariva due volte, in parentesi
 * grafica e in lettere. Qui sotto restano SOLO i numeri che sopra non ci sono:
 *  ① i gol attesi, che sono l'ingresso del modello;
 *  ② il record della fascia, che e' la prova esterna;
 *  ③ quanti mercati abbiamo esaminato, che e' il lavoro fatto.
 * Le voci di `reasons` che ripetono ① o la banda vengono filtrate: il
 * contenuto resta, in forma piu' densa, e non torna una seconda volta in prosa.
 *
 * Le celle parlano la lingua dei tre riquadri «come si legge»: icona, occhiello,
 * una cifra, un grafico piccolo, una riga di qualificazione. La fonte sta
 * SEMPRE dentro la frase, mai in un asterisco.
 */

/* La scala fissa dei gol attesi. Non e' normalizzata sul massimo della partita:
   con una scala relativa 1.0 contro 1.2 sembrerebbe uno squilibrio, e due
   partite diverse non si potrebbero confrontare. 4 gol e' l'estremo pratico. */
const SCALA_GOL = 4;

/** Le ragioni gia' rappresentate qui sopra, o gia' dette sopra la piega. */
const RAGIONI_GIA_DETTE = ['Gol attesi', 'Banda di incertezza'];

/**
 * Cosa resta da dire, una volta tolto cio' che la pagina dice gia'.
 *
 * DUE PASSAGGI, entrambi di sola presentazione — il contenuto informativo non
 * si perde, cambia solo dove viene detto:
 *
 *  1. spariscono le voci che il quadro mostra come dato («Gol attesi: …») o
 *     che la riga di definizione dice gia' sopra la piega («Banda di
 *     incertezza: …»);
 *  2. alla voce del mercato si toglie la testa. Il backend la scrive per
 *     esteso — «Handicap -2 ospite: 90 su 100, 15 punti sopra la media di
 *     riferimento (75 su 100)» — ma su questa pagina il nome del mercato e' un
 *     titolo e il 90 e' alto ottanta pixel, a due dita di distanza. Della
 *     frase resta la sola cosa che non e' gia' scritta: lo scarto dal
 *     riferimento.
 *
 * Se il testo non ha la forma attesa resta intero: un filtro che non riconosce
 * una frase deve lasciarla passare, mai troncarla a caso.
 */
export function ragioniResidue(reasons: string[], pronostico: Pronostico | null): string[] {
  const testa = pronostico ? `${pronostico.label}: ${suCento(pronostico.p)} su 100, ` : null;

  return reasons
    .filter((r) => !RAGIONI_GIA_DETTE.some((prefisso) => r.startsWith(prefisso)))
    .map((r) => (testa && r.startsWith(testa) ? maiuscola(r.slice(testa.length)) : r))
    .slice(0, 3);
}

function maiuscola(testo: string): string {
  return testo.charAt(0).toUpperCase() + testo.slice(1);
}

export function QuadroNumeri({
  fixture,
  record,
  ragioni,
}: {
  fixture: FixtureConPronostico;
  record: RecordFascia | null;
  ragioni: string[];
}) {
  const gol = fixture.expected_goals;
  const totale = gol.home + gol.away;
  const esaminati = fixture.diagnostics.n_candidates;

  return (
    <section className="quadro" aria-labelledby="titolo-quadro">
      <h2 id="titolo-quadro" className="label quadro__titolo">
        Come ci siamo arrivati
      </h2>

      <div className="quadro__celle">
        {/* ① I GOL ATTESI — l'ingresso del modello, non un suo risultato. */}
        <div className="cella">
          <IconaGol />
          <h3 className="cella__occhiello">Gol attesi</h3>

          <div className="cella__corpo">
            <BarraGol nome={fixture.home.name} valore={gol.home} lato="casa" />
            <BarraGol nome={fixture.away.name} valore={gol.away} lato="ospite" />
          </div>

          <p className="cella__nota">
            {decimale(totale, 2)} in tutto, su una scala che arriva a {SCALA_GOL}.
          </p>
        </div>

        {/* ② IL RECORD DELLA FASCIA — la prova esterna. La fascia sta dentro
            la frase: un tasso senza la sua fascia e' una media che mente. */}
        <div className="cella">
          <IconaRecord />
          <h3 className="cella__occhiello">Quanto spesso si avverano</h3>

          {record ? (
            <>
              <p className="cella__cifra">
                <span className="cifra-media">{record.suCento}</span>
                <span className="cella__unita">su 100</span>
              </p>

              <div className="cella__corpo">
                <ScalaVenti suCento={record.suCento} />
              </div>

              <p className="cella__nota">
                Su {intero(record.n)} pronostici della fascia {record.etichetta} su 100,{' '}
                {record.fonte === 'storico'
                  ? 'nel nostro test storico'
                  : 'fra quelli che abbiamo pubblicato'}{' '}
                {record.periodo}.
              </p>
            </>
          ) : (
            /* Non sapere ancora e' un'informazione: la cella non sparisce. */
            <p className="cella__nota cella__nota--sola">
              Non abbiamo ancora abbastanza pronostici in questa fascia per dire quanto spesso
              si avverano. Lo diremo quando ne avremo 50.
            </p>
          )}
        </div>

        {/* ③ IL LAVORO FATTO. Dice con un numero cio' che prima era una riga
            di prosa sopra i mercati alternativi («le calcoliamo tutte, ma ne
            consigliamo una sola»), che infatti da li' e' stata tolta. */}
        <div className="cella">
          <IconaMercati />
          <h3 className="cella__occhiello">Mercati esaminati</h3>

          <p className="cella__cifra">
            <span className="cifra-media">{intero(esaminati)}</span>
            <span className="cella__unita">su questa partita</span>
          </p>

          <p className="cella__nota">
            Li calcoliamo tutti a ogni giro. Ne consigliamo uno solo, e solo se supera il
            criterio scritto prima di guardare le partite.
          </p>
        </div>
      </div>

      {ragioni.length > 0 ? (
        <div className="quadro__perche">
          <h3 className="label">Perché questo mercato</h3>
          <ul className="ragioni">
            {ragioni.map((ragione) => (
              <li key={ragione}>
                <span>{testoPulito(ragione)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

/**
 * Una squadra e i suoi gol attesi. La barra e' il LINGUAGGIO A (il pieno), la
 * stessa marca della probabilita': qui e' legittima, perche' e' una quantita'
 * misurata e non una scelta da imitare.
 */
function BarraGol({ nome, valore, lato }: { nome: string; valore: number; lato: string }) {
  const quota = Math.min(valore / SCALA_GOL, 1) * 100;

  return (
    <p className="gol">
      <span className="gol__nome">
        {nome} <span className="gol__lato">{lato}</span>
      </span>
      <span className="gol__valore">{decimale(valore, 2)}</span>
      <span className="gol__barra" aria-hidden="true">
        <span className="gol__riempimento" style={{ width: `${quota}%` }} />
      </span>
    </p>
  );
}

/**
 * La proporzione a venti tacche — la riga di taratura applicata a un tasso.
 * Cento tacche non si contano, venti si: una tacca ogni cinque pronostici.
 */
function ScalaVenti({ suCento }: { suCento: number }) {
  const TACCHE = 20;
  const piene = Math.round((suCento / 100) * TACCHE);

  return (
    <div className="scala20" role="img" aria-label={`${suCento} su 100 avverati.`}>
      {Array.from({ length: TACCHE }, (_, i) => (
        <span key={i} className={`scala20__tacca${i < piene ? '' : ' scala20__tacca--vuota'}`} />
      ))}
    </div>
  );
}

/* Le icone: stessa lingua dei tre riquadri della giornata — tratto a
   --icon-stroke, terminazioni squadrate, geometria ortogonale, decorative. */

function IconaGol() {
  return (
    <svg
      className="cella__icona"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="var(--icon-stroke)"
      strokeLinecap="square"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M4 4v16" />
      <path d="M4 9h13" />
      <path d="M4 16h8" />
    </svg>
  );
}

function IconaRecord() {
  return (
    <svg
      className="cella__icona"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="var(--icon-stroke)"
      strokeLinecap="square"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M3 15h18" />
      <path d="M7 15v-4" />
      <path d="M12 15V7" />
      <path d="M17 15v-6" />
      <path d="M3 19h18" />
    </svg>
  );
}

function IconaMercati() {
  return (
    <svg
      className="cella__icona"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="var(--icon-stroke)"
      strokeLinecap="square"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M4 4h7v7H4z" fill="currentColor" stroke="none" />
      <path d="M13 4h7v7h-7z" />
      <path d="M4 13h7v7H4z" />
      <path d="M13 13h7v7h-7z" />
    </svg>
  );
}
