'use client';

import { useEffect, useState } from 'react';

import { ErroreProfilo, profilo } from '@/lib/profilo';

import { useSessione } from './Sessione';

/**
 * LA PAGINA CHE SI APRE DAL COLLEGAMENTO NELL'EMAIL.
 *
 * IL GETTONE ARRIVA NELL'INDIRIZZO E SI LEGGE QUI, non in un componente di
 * pagina: su un export statico non esiste un server che veda la stringa di
 * ricerca — l'HTML e' lo stesso per tutti. `useSearchParams` di Next non si
 * puo' usare senza `<Suspense>` e senza rendere la rotta dinamica, quindi si
 * legge `location.search` dopo il montaggio, che e' la cosa piu' semplice e
 * l'unica che funziona davvero qui.
 *
 * SI CONFERMA DA SOLA, senza un bottone «conferma» da premere. Chi ha aperto
 * il collegamento ha gia' espresso l'intenzione: chiedergli un secondo clic
 * per fare la stessa cosa e' un passaggio che non decide niente.
 *
 * QUATTRO ESITI, e sono davvero quattro cose diverse: sto controllando, fatto,
 * il collegamento non vale piu', il servizio non risponde. L'ultimo non e'
 * colpa di chi legge e va detto in modo diverso dal terzo.
 */
type Stato =
  | { fase: 'attesa' }
  | { fase: 'senza-gettone' }
  | { fase: 'fatto'; nome: string }
  | { fase: 'guasto'; messaggio: string; nostro: boolean };

export function Verifica() {
  const { aggiorna } = useSessione();
  const [stato, setStato] = useState<Stato>({ fase: 'attesa' });

  useEffect(() => {
    const gettone = new URLSearchParams(window.location.search).get('g');
    if (!gettone) {
      setStato({ fase: 'senza-gettone' });
      return;
    }
    let vivo = true;
    profilo
      .verifica(gettone)
      .then((u) => {
        if (!vivo) return;
        setStato({ fase: 'fatto', nome: u.nome });
        // Se chi conferma e' anche collegato, la barra e la pagina del profilo
        // devono smettere subito di dire che l'indirizzo non e' confermato.
        aggiorna(u);
      })
      .catch((e) => {
        if (!vivo) return;
        const err = e instanceof ErroreProfilo ? e : null;
        setStato({
          fase: 'guasto',
          messaggio: err?.message ?? 'Non ha funzionato.',
          nostro: err?.codice === 'rete_non_raggiungibile',
        });
      });
    return () => {
      vivo = false;
    };
    // Si esegue una volta sola: il gettone vale un colpo, e un secondo giro
    // troverebbe comunque un collegamento gia' consumato.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (stato.fase === 'attesa') {
    return <p className="pagina-profilo__attesa">Sto confermando…</p>;
  }

  if (stato.fase === 'fatto') {
    return (
      <div className="pagina-profilo__fuori">
        <h1 className="titolo-sezione">Indirizzo confermato</h1>
        <p>Fatto, {stato.nome}. Da adesso questo indirizzo risulta tuo.</p>
        <p className="pagina-profilo__nota">
          <a href="/profilo/">Vai al tuo profilo</a> oppure{' '}
          <a href="/">torna alle partite</a>.
        </p>
      </div>
    );
  }

  if (stato.fase === 'senza-gettone') {
    return (
      <div className="pagina-profilo__fuori">
        <h1 className="titolo-sezione">Manca il codice</h1>
        <p>
          Questo indirizzo si apre dal collegamento che ti abbiamo mandato per email. Se ci
          sei arrivato scrivendolo a mano, manca il pezzo finale.
        </p>
        <p className="pagina-profilo__nota">
          Dalla <a href="/profilo/">pagina del tuo profilo</a> puoi farti rimandare il
          messaggio.
        </p>
      </div>
    );
  }

  return (
    <div className="pagina-profilo__fuori">
      <h1 className="titolo-sezione">Non ha funzionato</h1>
      <p className={`modulo__errore${stato.nostro ? ' modulo__errore--nostro' : ''}`}>
        {stato.messaggio}
      </p>
      <p className="pagina-profilo__nota">
        I collegamenti valgono 24 ore e si usano una volta sola. Dalla{' '}
        <a href="/profilo/">pagina del tuo profilo</a> puoi chiederne un altro.
      </p>
    </div>
  );
}
