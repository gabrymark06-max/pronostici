import { suCento } from '@/lib/formato';
import { famiglieAlternative, nomeFamiglia } from '@/lib/mercati';
import { formattaQuota, quoteDi } from '@/lib/quote';
import { tace, type Fixture } from '@/lib/tipi';

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
 * LE COLONNE SONO LE STESSE DELLA LISTA: mercato, probabilità, quota equa,
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
  const secondarie = fixture.sofascore?.market_p ?? null;
  const nessunaQuota = !fixture.odds?.market_p && !secondarie;

  /* Se anche una sola riga viene dalla fonte secondaria la tavola lo dichiara
     sotto, una volta: la provenienza di un numero non e' un dettaglio da
     nascondere nel titolo di una cella.
     Si calcola PRIMA di disegnare, non accumulando dentro il ciclo: React non
     garantisce quando e quante volte il corpo di un render venga eseguito, e
     una variabile che cresce durante il disegno e' un valore che dipende
     dall'ordine. Qui la domanda e' semplice e la risposta si ottiene in una
     riga. */
  const usaSecondaria = gruppi.some((g) =>
    g.mercati.some((m) => quoteDi(m, fixture.odds, secondarie).fonte === 'secondaria'),
  );

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
              <th scope="col" className="num">
                La nostra
              </th>
              <th scope="col" className="num">
                Il mercato
              </th>
            </tr>
          </thead>
          {gruppi.map((gruppo) => (
            <tbody key={gruppo.famiglia}>
              <tr className="tabella__famiglia">
                <th colSpan={4} scope="colgroup">
                  {nomeFamiglia(gruppo.famiglia)}
                </th>
              </tr>
              {gruppo.mercati.map((mercato) => {
                const q = quoteDi(mercato, fixture.odds, secondarie);
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
                    <td className="num" data-etichetta="La nostra">
                      {formattaQuota(q.nostra)}
                    </td>
                    <td className="num" data-etichetta="Il mercato">
                      {q.mercato !== null ? (
                        formattaQuota(q.mercato)
                      ) : (
                        <span aria-hidden="true">—</span>
                      )}
                      {q.mercato === null ? (
                        <span className="solo-lettori">
                          {nessunaQuota
                            ? 'per questa partita non abbiamo quote'
                            : 'il mercato non determina questa scommessa'}
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
          giorni con un tetto di chiamate mensili, e la seconda non ha agganciato questa
          partita. Non è un errore del calcolo, è una fonte che non arriva fin qui.
        </p>
      ) : null}

      {usaSecondaria ? (
        <p className="sezione__nota sezione__nota--fonte">
          Dove la fonte principale non arriva usiamo una <strong>seconda fonte</strong>, che
          aggrega più operatori. Copre quattro famiglie che si traducono senza interpretare:
          esito finale, doppia chance, entrambe segnano, e i gol totali su tutte le linee da
          0,5 a 4,5. Il margine è tolto allo stesso modo.
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
            La colonna «il mercato» è la stessa quota equa calcolata sulle quote degli
            operatori, col margine tolto.
          </>
        )}
      </p>

      {nessunaQuota ? null : (
        /* PERCHE' QUELLE RIGHE SONO VUOTE, con i nomi veri.
           Prima qui c'era una frase che dava «gol di squadra ed entrambe
           segnano» come esempi di cio' che le fonti non determinano. Entrambe
           segnano ora e' coperto, e la frase era rimasta a dire il falso. Le
           famiglie scoperte sono tre e si chiamano per nome: un trattino con
           accanto il motivo e' un dato, un trattino da solo e' un buco. */
        <p className="sezione__nota">
          <strong>Tre famiglie restano senza quota di mercato</strong>, e non per una nostra
          scelta: <em>gol di squadra</em>, <em>handicap</em> e le <em>combo</em>. Nessuna delle
          fonti gratuite che possiamo leggere quota quanti gol segna una singola squadra;
          l’handicap ci arriva solo in versione asiatica, che è un’altra scommessa e non si
          può scrivere sotto il nome di questa. Ricavarle dal nostro stesso modello
          riempirebbe la colonna con il nostro numero travestito da mercato, e il confronto
          diventerebbe noi contro noi stessi.
        </p>
      )}
    </section>
  );
}
