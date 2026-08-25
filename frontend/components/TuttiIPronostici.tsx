import { suCento } from '@/lib/formato';
import { famiglieAlternative, nomeFamiglia } from '@/lib/mercati';
import { formattaQuota, quoteDi } from '@/lib/quote';
import { tace, type Fixture } from '@/lib/tipi';
import { contornoDi } from '@/lib/contorno';

/**
 * TUTTI I PRONOSTICI DELLA PARTITA — il nostro e gli altri, sulla stessa
 * tavola e con le stesse colonne.
 *
 * Nelle versioni precedenti gli altri mercati stavano chiusi dentro dei
 * `<details>`, per una ragione seria: mostrarli aperti riconsegna al lettore
 * l'argmax che il prodotto toglie di mezzo apposta, cioè l'impulso a
 * scegliersi il numero più alto. Ma tenerli chiusi ha un costo che si è
 * rivelato più alto: chi apre una partita vuole vedere il quadro, e un
 * prodotto che nasconde i propri calcoli sembra averne paura.
 *
 * La soluzione non è nascondere: è ORDINARE E SPIEGARE. La tavola è ordinata
 * per famiglia, il nostro pronostico porta il bersaglio ed è in evidenza, e la
 * riga di lettura sotto dice perché il più probabile non è il migliore — che è
 * l'unica cosa che davvero serve capire per non usare male questa tavola.
 *
 * LE COLONNE SONO LE STESSE DELLA LISTA: mercato, probabilità, quanto la dà
 * il mercato, prezzo trovato,
 * quota di mercato. Un lettore che ha imparato a leggere la lista non deve
 * imparare niente di nuovo qui.
 */
export function TuttiIPronostici({ fixture }: { fixture: Fixture }) {
  const famiglie = famiglieAlternative(fixture);
  const pick = tace(fixture) ? null : fixture.prediction;
  if (!pick && famiglie.length === 0) return null;

  /* Il pronostico scelto entra nella tavola della PROPRIA famiglia, in testa:
     è lo stesso oggetto delle altre righe, e separarlo in un blocco a parte lo
     renderebbe incomparabile proprio dove il confronto è il punto. */
  const gruppi = famiglie.map((g) => ({
    famiglia: g.famiglia,
    mercati:
      pick && pick.family === g.famiglia ? [pick, ...g.mercati] : g.mercati,
  }));
  if (pick && !gruppi.some((g) => g.famiglia === pick.family)) {
    gruppi.unshift({ famiglia: pick.family, mercati: [pick] });
  }

  /* Due assenze diverse che si scrivevano allo stesso modo.
     Un trattino in colonna «il mercato» puo' voler dire due cose opposte: che
     le quote ci sono ma non determinano QUELLA scommessa, oppure che per
     questa partita non ne abbiamo affatto. La seconda riguarda l'intera
     colonna e va detta una volta sotto la tavola, non ripetuta riga per riga
     con la motivazione sbagliata. */
  /* IL CONTORNO INTERO, non una sua mappa.
     Qui passava `contorno.market_p` — le sole probabilita' — a una funzione
     che dal 25 agosto 2026 vuole il blocco completo, perche' i PREZZI stanno
     in un altro campo. Il typecheck non se n'e' accorto: un `Record<string,
     number>` e' assegnabile a un tipo fatto di sole proprieta' opzionali,
     perche' l'index signature non ne dichiara nessuna e il controllo passa a
     vuoto. Risultato: ne' i prezzi ne' le probabilita' della fonte secondaria
     arrivavano mai in questa tavola, e le due colonne restavano vuote su ogni
     partita. */
  const contorno = contornoDi(fixture);
  const nessunaQuota = !fixture.odds?.market_p && !contorno?.market_p;

  /* Se anche una sola riga viene dalla fonte secondaria la tavola lo dichiara
     sotto, una volta: la provenienza di un numero non e' un dettaglio da
     nascondere nel titolo di una cella.
     Si calcola PRIMA di disegnare, non accumulando dentro il ciclo: React non
     garantisce quando e quante volte il corpo di un render venga eseguito, e
     una variabile che cresce durante il disegno e' un valore che dipende
     dall'ordine. Qui la domanda e' semplice e la risposta si ottiene in una
     riga. */
  const usaSecondaria = gruppi.some((g) =>
    g.mercati.some((m) => quoteDi(m, fixture).fonte === 'secondaria'),
  );

  /* UN PREZZO DI UN OPERATORE SOLO NON E' UN CONSENSO, e la tavola lo dice.
     Dal 25 agosto 2026 gol di squadra e handicap europeo hanno un prezzo, e
     viene da un bookmaker solo: nessun comparatore gratuito li pubblica. E'
     un numero vero e piu' debole di una mediana, e chi lo legge deve saperlo
     senza doverlo dedurre. */
  const conUnSoloOperatore = gruppi.some((g) =>
    g.mercati.some((m) => {
      const q = quoteDi(m, fixture);
      return q.prezzo !== null && q.operatori === 1;
    }),
  );

  /* QUALI FAMIGLIE RESTANO SENZA PREZZO, LETTE DALLA TAVOLA E NON DA UN ELENCO.
     Qui sotto c'era una frase che diceva «tre famiglie: gol di squadra,
     handicap e le combo». Era vera il giorno in cui e' stata scritta — e prima
     ancora ne diceva altre due, corrette per lo stesso motivo. Poi e' arrivata
     una fonte che quota le prime due, e la frase e' rimasta a dichiarare
     un'assenza che non c'era piu', su ogni partita del sito.
     Un elenco scritto a mano dentro una frase invecchia in silenzio. Questo si
     ricava dalle righe che il lettore ha davanti, quindi non puo'. */
  const senzaPrezzo = [
    ...new Set(
      gruppi
        .filter((g) => g.mercati.every((m) => quoteDi(m, fixture).prezzo === null))
        .map((g) => nomeFamiglia(g.famiglia).toLowerCase()),
    ),
  ];

  return (
    <section className="sezione" id="pronostici" aria-labelledby="titolo-tutti">
      <h2 id="titolo-tutti" className="label sezione__titolo">
        <span className="bersaglio" aria-hidden="true" /> Tutti i pronostici di questa partita
      </h2>

      <p className="sezione__lettura">
        Il più probabile non è il migliore. Su una partita sbilanciata «doppia chance sul
        favorito» sfiora sempre il massimo, ma è anche quello che il mercato prezza già
        meglio di noi: non ci guadagni niente a giocarlo. Noi scegliamo il mercato in cui il
        nostro modello si discosta di più da quello che il mercato dà per scontato, a patto
        che resti probabile e che la stima sia stabile. Ecco perché il bersaglio non è quasi
        mai sulla riga più alta.
      </p>

      <table className="tabella tabella--mercati">
          <caption className="solo-lettori">
            Tutti i mercati calcolati per questa partita, per famiglia
          </caption>
          <thead>
            <tr>
              {/* `num` non e' solo il carattere monospaziato: porta anche
                  l'allineamento a destra. Senza, l'intestazione resta a
                  sinistra mentre i suoi numeri stanno a destra, e a quel punto
                  la colonna smette di leggersi come colonna. */}
              <th scope="col">Pronostico</th>
              <th scope="col" className="num">
                Probabilità
              </th>
              {/* UNA COLONNA SOLA DI QUOTE, e sono prezzi veri.
                  «La nostra» era `1/probabilita' nostra` e «Il mercato»
                  `1/probabilita' di mercato`: due numeri esatti, nessuno dei
                  due un prezzo. La probabilita' del mercato resta, ma nella
                  sua unita' — su 100 — accanto alla nostra. */}
              <th scope="col" className="num">
                Il mercato dice
              </th>
              <th scope="col" className="num">
                Prezzo trovato
              </th>
            </tr>
          </thead>
          {gruppi.map((gruppo) => (
            <tbody key={gruppo.famiglia}>
              <tr className="tabella__famiglia">
                <th colSpan={5} scope="colgroup">
                  {nomeFamiglia(gruppo.famiglia)}
                </th>
              </tr>
              {gruppo.mercati.map((mercato) => {
                const q = quoteDi(mercato, fixture);
                const nostro = pick != null && mercato.key === pick.key;
                return (
                  <tr key={mercato.key} className={nostro ? 'tabella__nostro' : undefined}>
                    <th scope="row">
                      {nostro ? (
                        <span className="bersaglio" aria-hidden="true" />
                      ) : (
                        <span className="tabella__vuoto" aria-hidden="true" />
                      )}
                      {mercato.label}
                      {nostro ? (
                        <span className="tabella__marca">il nostro</span>
                      ) : null}
                    </th>
                    <td className="num" data-etichetta="Probabilità">
                      {suCento(mercato.p)}
                      <span className="tabella__unita"> su 100</span>
                    </td>
                    <td className="num" data-etichetta="Il mercato dice">
                      {q.pMercato !== null ? (
                        <>
                          {suCento(q.pMercato)}
                          <span className="tabella__unita"> su 100</span>
                        </>
                      ) : (
                        <span aria-hidden="true">—</span>
                      )}
                      {q.pMercato === null ? (
                        <span className="solo-lettori">
                          {nessunaQuota
                            ? 'per questa partita non abbiamo quote'
                            : 'il mercato non determina questa scommessa'}
                        </span>
                      ) : null}
                    </td>
                    <td className="num" data-etichetta="Prezzo trovato">
                      {q.prezzo !== null ? (
                        formattaQuota(q.prezzo)
                      ) : (
                        <span aria-hidden="true">—</span>
                      )}
                      {q.prezzo === null ? (
                        <span className="solo-lettori">
                          nessuna fonte quota questa scommessa
                        </span>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          ))}
      </table>

      {nessunaQuota ? (
        <p className="sezione__nota sezione__nota--assenza">
          <strong>La colonna «il mercato» è vuota su tutte le righe</strong> perché per questa
          partita non abbiamo quote. La fonte principale copre una finestra di quattordici
          giorni con un tetto di chiamate mensili, e nessuna delle altre due ha agganciato
          questa partita. Non è un errore del calcolo, è una fonte che non arriva fin qui.
        </p>
      ) : null}

      {usaSecondaria ? (
        <p className="sezione__nota sezione__nota--fonte">
          Dove la fonte principale non arriva ne usiamo <strong>altre due</strong>. La prima
          è un comparatore e dà la mediana di una ventina di operatori su esito finale,
          doppia chance, entrambe segnano e gol totali. La seconda è un bookmaker europeo, e
          quota le due famiglie che nessun comparatore gratuito pubblica: i gol di una
          singola squadra e l’handicap a tre esiti.
          {conUnSoloOperatore ? (
            <>
              {' '}
              Su questa partita almeno un prezzo qui sopra viene da lui e{' '}
              <strong>da lui soltanto</strong>: è il suo prezzo, non il consenso del mercato,
              e vale meno di una mediana anche quando è giusto.
            </>
          ) : null}{' '}
          Il margine è tolto allo stesso modo su tutte e tre.
        </p>
      ) : null}

      <p className="sezione__nota">
        Su questa partita abbiamo calcolato {fixture.diagnostics.n_candidates} mercati e li
        abbiamo raggruppati in {fixture.diagnostics.n_clusters} famiglie di esiti che si
        muovono insieme. Qui c’è il migliore di ogni famiglia: mostrarli tutti e{' '}
        {fixture.diagnostics.n_candidates} sarebbe lo stesso mercato scritto in venti modi.
        {nessunaQuota ? null : (
          <>
            {' '}
            La colonna «il mercato dice» è la probabilità ricavata dalle quote degli
            operatori, col margine tolto.
          </>
        )}
      </p>

      {nessunaQuota || senzaPrezzo.length === 0 ? null : (
        /* PERCHE' QUELLE RIGHE SONO VUOTE. Un trattino con accanto il motivo e'
           un dato; un trattino da solo e' un buco. */
        <p className="sezione__nota">
          <strong>
            {senzaPrezzo.length === 1
              ? 'Una famiglia resta senza prezzo'
              : `${senzaPrezzo.length} famiglie restano senza prezzo`}
          </strong>
          , e non per una nostra scelta:{' '}
          {senzaPrezzo.map((nome, i) => (
            <span key={nome}>
              {i > 0 ? (i === senzaPrezzo.length - 1 ? ' e ' : ', ') : ''}
              <em>{nome}</em>
            </span>
          ))}
          . Le <em>combo</em> non le espone nessuna fonte gratuita; per le altre è
          l’operatore che non ha aperto quella linea su questa partita. Ricavare il numero
          dal nostro stesso modello riempirebbe la colonna con la nostra stima travestita da
          mercato, e il confronto diventerebbe noi contro noi stessi.
        </p>
      )}
    </section>
  );
}
