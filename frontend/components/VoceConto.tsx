'use client';

import { CONTI_ACCESI } from '@/lib/conto';

import { useSessione } from './Sessione';

/**
 * L'ULTIMA VOCE DELLA BARRA: «Accedi», oppure il tuo nome.
 *
 * NON C'E' QUANDO I CONTI SONO SPENTI. Se `NEXT_PUBLIC_API_CONTI` non e'
 * configurata il servizio non esiste, e un bottone «Accedi» che porta a un
 * modulo che non puo' funzionare e' peggio di nessun bottone.
 *
 * MENTRE SI CARICA NON MOSTRA NIENTE, e lo spazio resta occupato.
 * Le alternative erano due e sono entrambe peggiori: mostrare «Accedi» e poi
 * cambiarlo nel nome fa cliccare chi e' gia' dentro; non occupare lo spazio fa
 * saltare tutta la barra quando la risposta arriva, che e' uno spostamento di
 * layout su ogni pagina del sito.
 */
export function VoceConto() {
  const { utente, caricamento } = useSessione();

  if (!CONTI_ACCESI) return null;

  if (caricamento) {
    return <span className="conto-voce conto-voce--attesa" aria-hidden="true" />;
  }

  if (!utente) {
    return (
      <a className="conto-voce conto-voce--entra" href="/accedi/">
        Accedi
      </a>
    );
  }

  return (
    <a className="conto-voce" href="/conto/">
      <span className="conto-voce__iniziale" aria-hidden="true">
        {utente.nome.slice(0, 1).toUpperCase()}
      </span>
      <span className="conto-voce__nome">{utente.nome}</span>
    </a>
  );
}
