import type { Arbitro } from '@/lib/tipi';

/**
 * L'ARBITRO DESIGNATO, CON IL SUO CAMPIONE ACCANTO.
 *
 * Un arbitro a 2,7 gialli a partita sembra severo. Su dieci partite non lo si
 * puo' dire: dieci partite non distinguono un arbitro severo da uno normale
 * che ha preso tre serate movimentate. Il numero da solo inganna, e il modo
 * per non ingannare non e' nasconderlo — e' scriverlo accanto a quante partite
 * lo sostengono, con la stessa dimensione.
 *
 * Per questo il conteggio non e' una nota in fondo ne' un asterisco: e' la
 * seconda meta' della stessa frase.
 *
 * Sotto le venti partite compare anche la riga che lo dice a parole, perche'
 * «10 partite» e' un dato che si legge senza capirlo se non si sa quanto ne
 * servirebbero.
 */

/** Sotto questa soglia il tasso e' troppo mosso per farci conto. */
const PARTITE_SUFFICIENTI = 20;

export function BloccoArbitro({ arbitro, stadio }: { arbitro: Arbitro; stadio?: string }) {
  const partite = arbitro.partite ?? 0;
  const gialliMedia = arbitro.gialli_per_partita ?? null;
  const campioneSottile = partite > 0 && partite < PARTITE_SUFFICIENTI;

  return (
    <section className="sezione arbitro" id="arbitro" aria-labelledby="titolo-arbitro">
      <h2 id="titolo-arbitro" className="label sezione__titolo">
        <span className="bersaglio" aria-hidden="true" /> L’arbitro
      </h2>

      <p className="arbitro__nome">
        {arbitro.nome}
        {arbitro.paese ? <span className="arbitro__paese"> · {arbitro.paese}</span> : null}
      </p>

      {gialliMedia !== null && partite > 0 ? (
        <p className="arbitro__cifra">
          <span className="arbitro__valore">{gialliMedia.toFixed(2)}</span>
          <span className="arbitro__unita">
            cartellini gialli a partita, su {partite} {partite === 1 ? 'partita' : 'partite'}
          </span>
        </p>
      ) : (
        <p className="arbitro__assente">
          Non abbiamo il suo storico disciplinare: la fonte non lo espone per questo arbitro.
        </p>
      )}

      {campioneSottile ? (
        <p className="arbitro__avviso">
          <span className="arbitro__marca" aria-hidden="true">
            !
          </span>{' '}
          <span>
            <strong>{partite} partite sono poche</strong> per dire che tipo di arbitro è. A questo
            numero un arbitro normale con tre serate movimentate è indistinguibile da uno severo.
            Dove usiamo questo dato lo pesiamo di conseguenza, invece di prenderlo per buono.
          </span>
        </p>
      ) : null}

      <dl className="arbitro__dettagli">
        {arbitro.gialli != null ? (
          <div>
            <dt>Gialli</dt>
            <dd>{arbitro.gialli}</dd>
          </div>
        ) : null}
        {arbitro.rossi != null ? (
          <div>
            <dt>Rossi</dt>
            <dd>{arbitro.rossi}</dd>
          </div>
        ) : null}
        {stadio ? (
          <div>
            <dt>Stadio</dt>
            <dd>{stadio}</dd>
          </div>
        ) : null}
      </dl>
    </section>
  );
}
