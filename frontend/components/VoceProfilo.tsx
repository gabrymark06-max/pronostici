'use client';

import { PROFILI_ACCESI } from '@/lib/profilo';

import { useSessione } from './Sessione';

/**
 * L'ULTIMA VOCE DELLA BARRA: «Accedi», oppure il tuo nome.
 *
 * NON C'E' QUANDO I PROFILI SONO SPENTI. Se `NEXT_PUBLIC_API_PROFILI` non e'
 * configurata il servizio non esiste, e un bottone «Accedi» che porta a un
 * modulo che non puo' funzionare e' peggio di nessun bottone.
 *
 * MENTRE SI CARICA NON MOSTRA NIENTE, e lo spazio resta occupato.
 * Le alternative erano due e sono entrambe peggiori: mostrare «Accedi» e poi
 * cambiarlo nel nome fa cliccare chi e' gia' dentro; non occupare lo spazio fa
 * saltare tutta la barra quando la risposta arriva, che e' uno spostamento di
 * layout su ogni pagina del sito.
 */
export function VoceProfilo() {
  const { utente, caricamento } = useSessione();

  if (!PROFILI_ACCESI) return null;

  if (caricamento) {
    return <span className="profilo-voce profilo-voce--attesa" aria-hidden="true" />;
  }

  if (!utente) {
    return (
      <a className="profilo-voce profilo-voce--entra" href="/accedi/">
        Accedi
      </a>
    );
  }

  return (
    <a className="profilo-voce" href="/profilo/">
      <span className="profilo-voce__iniziale" aria-hidden="true">
        {utente.nome.slice(0, 1).toUpperCase()}
      </span>
      <span className="profilo-voce__nome">{utente.nome}</span>
    </a>
  );
}
