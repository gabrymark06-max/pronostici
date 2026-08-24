'use client';

import { useEffect, useRef, useState } from 'react';

import { interno } from '@/lib/sito';
import { useParametro } from '@/lib/indirizzo';
import { ErroreProfilo, profilo } from '@/lib/profilo';

import { useSessione } from './Sessione';

/**
 * DOVE ATTERRA CHI CLICCA IL COLLEGAMENTO NELL'EMAIL DI CONFERMA.
 *
 * IL GETTONE SI LEGGE DA `location`, non da `useSearchParams`: su un export
 * statico i parametri della richiesta non esistono in fase di build, e
 * `useSearchParams` costringerebbe l'intera pagina dentro un `<Suspense>` per
 * un'informazione che qui arriva comunque solo nel browser. Il come sta in
 * `lib/indirizzo`, insieme alla ragione per cui non e' un `useEffect`.
 *
 * L'ASSENZA DEL GETTONE NON E' UNO STATO DA IMPOSTARE, e' quello che si vede
 * quando il gettone non c'e'. Prima era un `setState` dentro l'effetto: un
 * secondo render per dire una cosa che si sapeva gia' al primo.
 *
 * SI CONFERMA DA SOLA, senza un bottone «conferma». Chi ha cliccato il
 * collegamento nell'email ha gia' espresso l'intenzione: chiedergli un secondo
 * clic sarebbe un passaggio che non protegge da niente — il gettone e' gia'
 * stato aperto — e che perde chi si distrae.
 *
 * NON SI RIPETE. Il gettone vale una volta sola: senza la guardia, il doppio
 * montaggio di React in sviluppo consumerebbe il gettone al primo giro e
 * mostrerebbe l'errore del secondo. Sarebbe un guasto che si vede solo in
 * sviluppo, cioe' il tipo che si insegue per ore.
 */
const SENZA_GETTONE =
  'Questo indirizzo non porta nessun codice di conferma. Apri il collegamento ' +
  'direttamente dall’email che ti abbiamo mandato.';

export function PaginaVerifica() {
  const { aggiorna } = useSessione();
  const gettone = useParametro('g');
  const [stato, setStato] = useState<'attesa' | 'fatto' | 'guasto'>('attesa');
  const [messaggio, setMessaggio] = useState('');
  const partito = useRef(false);

  useEffect(() => {
    // `undefined` e' «il browser non ha ancora parlato», `null` e' «non c'e'».
    // Nessuno dei due e' un gettone da spendere.
    if (!gettone) return;
    if (partito.current) return;
    partito.current = true;

    profilo
      .verifica(gettone)
      .then((u) => {
        setStato('fatto');
        // Se sei collegato in questo browser, la barra si aggiorna da sola.
        // Se non lo sei, `aggiorna` mette l'utente e la barra ti riconosce:
        // il gettone e' arrivato nella tua casella, quindi sei tu.
        aggiorna(u);
      })
      .catch((e) => {
        setStato('guasto');
        setMessaggio(
          e instanceof ErroreProfilo
            ? e.message
            : 'Non ha funzionato. Riprova fra poco.',
        );
      });
  }, [aggiorna, gettone]);

  if (gettone === null) {
    return (
      <div className="esito esito--fallito">
        <h1 className="titolo-sezione">Non ha funzionato</h1>
        <p>{SENZA_GETTONE}</p>
        <p className="esito__azioni">
          <a className="azione azione--piena" href={interno('/profilo/')}>
            Vai al tuo profilo
          </a>
        </p>
      </div>
    );
  }

  if (stato === 'attesa') {
    return (
      <div className="esito">
        <h1 className="titolo-sezione">Un momento…</h1>
        <p>Sto confermando il tuo indirizzo.</p>
      </div>
    );
  }

  if (stato === 'fatto') {
    return (
      <div className="esito esito--riuscito">
        <h1 className="titolo-sezione">Indirizzo confermato</h1>
        <p>
          Da adesso sappiamo che questa casella è tua. Serve per una cosa sola: poterti
          rimandare la password se un giorno la dimentichi.
        </p>
        <p className="esito__azioni">
          <a className="azione azione--piena" href={interno('/profilo/')}>
            Vai al tuo profilo
          </a>
          <a className="azione" href={interno('/')}>
            Vedi le partite
          </a>
        </p>
      </div>
    );
  }

  return (
    <div className="esito esito--fallito">
      <h1 className="titolo-sezione">Non ha funzionato</h1>
      <p>{messaggio}</p>
      <p className="esito__nota">
        Il motivo più probabile è che il collegamento fosse vecchio: ne vale uno solo alla
        volta, e chiederne un altro annulla il precedente. Dalla pagina del tuo profilo puoi
        chiederne uno nuovo.
      </p>
      <p className="esito__azioni">
        <a className="azione azione--piena" href={interno('/profilo/')}>
          Vai al tuo profilo
        </a>
      </p>
    </div>
  );
}
