'use client';

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

import { chiSono, CONTI_ACCESI, conto, type Utente } from '@/lib/conto';

/**
 * CHI SEI, per tutta l'applicazione.
 *
 * TRE STATI, NON DUE. `caricamento` esiste perche' il sito e' statico: l'HTML
 * arriva prima che si sappia chi sei, e per un istante ogni pagina e' la pagina
 * di un anonimo. Senza il terzo stato la barra mostrerebbe «Accedi» per mezzo
 * secondo a chi e' gia' collegato — uno sfarfallio che sembra un difetto e che
 * su una connessione lenta dura abbastanza da far cliccare.
 *
 * NON C'E' NESSUN DATO DELL'UTENTE IN `localStorage`. Sarebbe l'unico modo di
 * togliere quell'istante, e il prezzo sarebbe una copia dell'identita' che
 * resta li' dopo l'uscita, dopo la chiusura del conto, e su un computer
 * condiviso. L'unica fonte di verita' e' il server.
 */

interface Contesto {
  utente: Utente | null;
  caricamento: boolean;
  /** Da chiamare dopo accesso, registrazione o cambio password. */
  aggiorna: (u: Utente | null) => void;
  esci: () => Promise<void>;
}

const Ctx = createContext<Contesto>({
  utente: null,
  caricamento: false,
  aggiorna: () => {},
  esci: async () => {},
});

export function ProvinciaSessione({ children }: { children: ReactNode }) {
  const [utente, setUtente] = useState<Utente | null>(null);
  // Se i conti sono spenti non si carica niente e non si aspetta niente.
  const [caricamento, setCaricamento] = useState(CONTI_ACCESI);

  useEffect(() => {
    if (!CONTI_ACCESI) return;
    let vivo = true;
    chiSono()
      .then((u) => {
        if (vivo) setUtente(u);
      })
      .finally(() => {
        if (vivo) setCaricamento(false);
      });
    // La pulizia serve davvero: in sviluppo React monta due volte, e senza
    // questa la seconda risposta sovrascriverebbe uno stato gia' cambiato.
    return () => {
      vivo = false;
    };
  }, []);

  const esci = useCallback(async () => {
    try {
      await conto.uscita();
    } finally {
      // Si esce dalla pagina ANCHE se la chiamata fallisce. Il caso in cui
      // fallisce e' quello in cui la sessione era gia' morta, e lasciare lo
      // schermo con il nome dell'utente sarebbe il messaggio sbagliato.
      setUtente(null);
    }
  }, []);

  return (
    <Ctx.Provider value={{ utente, caricamento, aggiorna: setUtente, esci }}>
      {children}
    </Ctx.Provider>
  );
}

export function useSessione(): Contesto {
  return useContext(Ctx);
}
