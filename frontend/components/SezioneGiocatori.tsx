import type { GiocatoreStimato, StimeGiocatori } from '@/lib/tipi';

/**
 * LE STIME SUI SINGOLI GIOCATORI — E LA DICHIARAZIONE CHE NON SONO MISURATE.
 *
 * Tutto il resto del sito pubblica numeri che sono passati da un backtest su
 * 5.018 partite e che finiscono in un registro pubblico. Questi no, per due
 * ragioni che non dipendono da quanto e' buono il modello:
 *
 *   1. non esiste una quota di mercato su questi esiti, quindi il criterio con
 *      cui scegliamo un pronostico — lo scarto dal mercato — qui non e'
 *      nemmeno calcolabile;
 *   2. non esiste uno storico partita-per-partita con cui verificarli.
 *
 * Il rischio non e' che i numeri siano sbagliati: e' che il lettore li tratti
 * come gli altri. Per questo la dichiarazione non e' una nota in fondo ne' un
 * asterisco — e' un blocco che si legge PRIMA della tabella, e la sezione ha
 * un trattamento visivo diverso dai pronostici misurati.
 *
 * Se un giorno queste stime entrassero nel registro, `misurato` diventerebbe
 * `true` nei dati e questo blocco sparirebbe da solo. Finche' e' `false`, resta.
 */

/** I mercati mostrati, nell'ordine in cui hanno senso leggerli. */
const COLONNE: { chiave: string; testa: string; titolo: string }[] = [
  { chiave: 'gol', testa: 'Gol', titolo: 'Segna almeno un gol' },
  { chiave: 'assist', testa: 'Assist', titolo: 'Serve almeno un assist' },
  { chiave: 'gol_o_assist', testa: 'Gol o assist', titolo: 'Segna oppure serve un assist' },
  { chiave: 'cartellino', testa: 'Cartellino', titolo: 'Prende un cartellino' },
  { chiave: 'fallo', testa: 'Fallo', titolo: 'Commette almeno un fallo' },
  { chiave: 'tiro_in_porta', testa: 'Tiro in porta', titolo: 'Almeno un tiro nello specchio' },
];

function Tabella({ titolo, giocatori }: { titolo: string; giocatori: GiocatoreStimato[] }) {
  if (giocatori.length === 0) return null;

  return (
    <div className="giocatori__squadra">
      <h3 className="label giocatori__titolo">{titolo}</h3>
      {/* NIENTE `scorrevole`: la tavola ci sta.
          Ci stava anche prima, se non fosse che «su 100» era ripetuto in ogni
          cella — sei volte per riga, quarantadue per squadra. L'unita' e' la
          stessa per tutte le colonne dei mercati, quindi si dice UNA volta
          nell'intestazione e le celle tengono il solo numero. La larghezza
          crolla e la barra di scorrimento sparisce. */}
      <table className="tabella tabella--giocatori">
        <thead>
          <tr>
            <th scope="col">Giocatore</th>
            {COLONNE.map((c) => (
              <th scope="col" className="num" key={c.chiave} title={c.titolo}>
                {c.testa}
                <span className="giocatori__unita">su 100</span>
              </th>
            ))}
            <th scope="col" className="num">
              Campione
            </th>
          </tr>
        </thead>
        <tbody>
          {giocatori.map((g) => {
            const per = new Map(g.stime.map((s) => [s.mercato, s.p]));
            return (
              <tr key={g.id}>
                <th scope="row">
                  {g.nome}
                  {g.ruolo ? <span className="giocatori__ruolo"> {g.ruolo}</span> : null}
                </th>
                {COLONNE.map((c) => {
                  const p = per.get(c.chiave);
                  return (
                    <td className="num" key={c.chiave} data-etichetta={c.testa}>
                      {typeof p === 'number' ? (
                        <>
                          {Math.round(p * 100)}
                          <span className="solo-lettori"> su 100</span>
                        </>
                      ) : (
                        '—'
                      )}
                    </td>
                  );
                })}
                <td className="num giocatori__campione" data-etichetta="Campione">
                  {g.presenze != null ? `${g.presenze} partite` : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function SezioneGiocatori({
  stime,
  casa,
  ospiti,
}: {
  stime: StimeGiocatori;
  casa: string;
  ospiti: string;
}) {
  if (stime.casa.length === 0 && stime.ospiti.length === 0) return null;

  return (
    <section className="sezione giocatori" id="giocatori" aria-labelledby="titolo-giocatori">
      <h2 id="titolo-giocatori" className="label sezione__titolo">
        <span className="bersaglio" aria-hidden="true" /> I singoli giocatori
      </h2>

      {/* LA DICHIARAZIONE, PRIMA DEI NUMERI. Chi scorre e si ferma alla tabella
          deve aver gia' incontrato questa riga. */}
      {!stime.misurato ? (
        <p className="giocatori__dichiarazione">
          <span className="giocatori__marca" aria-hidden="true">
            !
          </span>
          <span>
            <strong>Questi numeri non sono misurati.</strong> Tutto il resto del sito passa da un
            test storico e finisce nel registro pubblico; questa sezione no. Su questi esiti non
            esiste una quota di mercato con cui confrontarci, e non abbiamo uno storico per
            verificarli. Sono stime dichiarate, non pronostici: <strong>non entrano nel
            registro</strong> e non contano nella percentuale di quelli presi.
          </span>
        </p>
      ) : null}

      <p className="sezione__lettura">
        Calcolate solo per i titolari della formazione probabile, dai loro dati di stagione riportati
        a 76 minuti — quanto gioca in media chi parte titolare. L’ultima colonna dice su quante
        partite poggia la stima: più è alta, più il numero è solido.
        {typeof stime.moltiplicatore_arbitro === 'number' &&
        stime.moltiplicatore_arbitro !== 1 ? (
          <>
            {' '}
            I cartellini tengono conto dell’arbitro designato, con un peso ridotto in proporzione a
            quante partite ha diretto.
          </>
        ) : null}
      </p>

      <Tabella titolo={casa} giocatori={stime.casa} />
      <Tabella titolo={ospiti} giocatori={stime.ospiti} />
    </section>
  );
}
