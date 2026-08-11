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

  return (
    <section className="sezione" aria-labelledby="titolo-tutti">
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
              <th scope="col">Pronostico</th>
              <th scope="col">Probabilità</th>
              <th scope="col">Quota equa</th>
              <th scope="col">Quota di mercato</th>
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
                const q = quoteDi(mercato, fixture.odds);
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
                    <td className="num" data-etichetta="Quota equa">
                      {formattaQuota(q.equa)}
                    </td>
                    <td className="num" data-etichetta="Mercato">
                      {q.mercato !== null ? (
                        formattaQuota(q.mercato)
                      ) : (
                        <span aria-hidden="true">—</span>
                      )}
                      {q.mercato === null ? (
                        <span className="solo-lettori">non quotato</span>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          ))}
      </table>

      <p className="sezione__nota">
        Su questa partita abbiamo calcolato {fixture.diagnostics.n_candidates} mercati e li
        abbiamo raggruppati in {fixture.diagnostics.n_clusters} famiglie di esiti che si
        muovono insieme. Qui c’è il migliore di ogni famiglia: mostrarli tutti e{' '}
        {fixture.diagnostics.n_candidates} sarebbe lo stesso mercato scritto in venti modi.
        La colonna «mercato» è vuota dove la nostra fonte gratuita di quote non copre quel
        tipo di scommessa, che è la maggior parte dei casi.
      </p>
    </section>
  );
}
