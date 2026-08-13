'use client';

import { useEffect, useRef, useSyncExternalStore } from 'react';

import type { RiepilogoGiorno } from '@/lib/dati';
import { dataLunga, pezziGiorno } from '@/lib/formato';

/**
 * IL CALENDARIO — la sola superficie di controllo del prodotto.
 *
 * Appiccicato subito sotto la barra di navigazione: barra e calendario insieme
 * sono il cromo, e restano visibili mentre la lista scorre. È la meccanica dei
 * tabelloni di risultati, dove il primo gesto è sempre «che giorno guardo».
 *
 * Ogni casella porta tre cose: la sigla del giorno, il numero, e QUANTE
 * PARTITE ci sono. La terza è ciò che trasforma il calendario da elenco di
 * destinazioni in informazione — dice anche dove vale la pena andare.
 *
 * IERI / OGGI / DOMANI. Sono le tre parole che chi apre un tabellone cerca per
 * prime, e la sigla del giorno della settimana non le sostituisce. Non si
 * possono però calcolare a build time: il sito è statico, il calcolo gira una
 * volta la notte, e una pagina servita il giorno dopo direbbe «OGGI» sul
 * giorno sbagliato — un errore silenzioso e credibile, il tipo peggiore. Si
 * calcolano quindi DOPO l'idratazione, sull'orologio di chi guarda: prima di
 * allora la casella mostra la sigla, che è vera sempre.
 *
 * Restano `<a>` reali verso `/giorno/{data}`: funzionano senza JavaScript,
 * sono condivisibili, e il tasto indietro fa la cosa giusta senza codice.
 * L'altro JavaScript porta in vista il giorno corrente scrivendo `scrollLeft`
 * invece di `scrollIntoView`: così scorre il binario, mai la pagina.
 */
export function Calendario({
  giorni,
  corrente,
  precedente,
  successivo,
  /**
   * La rotta su cui si muove il calendario, senza data e senza barre.
   *
   * La striscia dei giorni serve identica in due posti — la lista delle
   * partite e il pronostico del giorno — e in ognuno deve restare DENTRO la
   * propria sezione. Un calendario che dal pronostico del giorno ti sposta
   * nella lista non e' un calendario: e' un'uscita mascherata da controllo.
   */
  base = '/giorno',
}: {
  giorni: RiepilogoGiorno[];
  corrente: string;
  precedente: string | null;
  successivo: string | null;
  base?: string;
}) {
  const binario = useRef<HTMLUListElement>(null);
  const attivo = useRef<HTMLAnchorElement>(null);

  /* L'orologio è uno stato ESTERNO a React, e si legge come tale invece di
     copiarlo in uno stato con un effetto: `useSyncExternalStore` dà `null` sul
     server e la data locale sul client, senza il render a cascata che un
     `setState` dentro un effetto produrrebbe. Il valore è una stringa, quindi
     `getSnapshot` resta stabile fra due chiamate nello stesso giorno. */
  const oggi = useSyncExternalStore(niente, dataLocale, () => null);

  useEffect(() => {
    const contenitore = binario.current;
    const voce = attivo.current;
    if (!contenitore || !voce) return;
    const centro = voce.offsetLeft - (contenitore.clientWidth - voce.offsetWidth) / 2;
    contenitore.scrollLeft = Math.max(0, centro);
  }, [corrente]);

  return (
    <nav className="rail" aria-label="Calendario">
      <div className="rail__interno colonna colonna--lista">
        <Freccia data={precedente} verso="precedente" base={base} />

        <ul className="rail__binario" ref={binario}>
          {giorni.map((giorno) => {
            const { sigla, numero } = pezziGiorno(giorno.data);
            const attuale = giorno.data === corrente;
            const parola = parolaRelativa(giorno.data, oggi);
            return (
              <li key={giorno.data}>
                <a
                  ref={attuale ? attivo : undefined}
                  className={`rail__giorno${parola ? ' rail__giorno--vicino' : ''}`}
                  href={`${base}/${giorno.data}/`}
                  aria-current={attuale ? 'date' : undefined}
                  /* WCAG 2.5.3 «Label in Name»: il nome accessibile deve
                     COMINCIARE con il testo che si vede. Chi usa il comando
                     vocale dice quello che legge — «clicca OGGI 11». */
                  aria-label={`${parola ?? sigla} ${numero} — ${dataLunga(giorno.data)}, ${etichettaConteggio(giorno.total)}`}
                >
                  <span className="rail__sigla" aria-hidden="true">
                    {parola ?? sigla}
                  </span>
                  <span className="rail__numero" aria-hidden="true">
                    {numero}
                  </span>
                  <span className="rail__conteggio" aria-hidden="true">
                    {giorno.total === 0 ? '—' : giorno.total}
                  </span>
                </a>
              </li>
            );
          })}
        </ul>

        <Freccia data={successivo} verso="successivo" base={base} />
      </div>
    </nav>
  );
}

/* L'orologio non emette eventi a cui iscriversi: la sottoscrizione è vuota per
   contratto, e la data si rilegge a ogni render come qualunque altro valore
   esterno. Chi tiene la scheda aperta oltre la mezzanotte vede la parola
   aggiornarsi al primo render successivo — non è uno stato da mantenere. */
function niente(): () => void {
  return () => {};
}

/** La data LOCALE di chi guarda, non quella UTC: alle 01:00 in Italia
    `toISOString()` direbbe ancora ieri. */
function dataLocale(): string {
  const adesso = new Date();
  const y = adesso.getFullYear();
  const m = String(adesso.getMonth() + 1).padStart(2, '0');
  const d = String(adesso.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/** `IERI` / `OGGI` / `DOMANI`, o `null` per ogni altro giorno. */
function parolaRelativa(data: string, oggi: string | null): string | null {
  if (!oggi) return null;
  if (data === oggi) return 'OGGI';
  const base = new Date(`${oggi}T12:00:00Z`).getTime();
  const giorno = new Date(`${data}T12:00:00Z`).getTime();
  const differenza = Math.round((giorno - base) / 86_400_000);
  if (differenza === -1) return 'IERI';
  if (differenza === 1) return 'DOMANI';
  return null;
}

function etichettaConteggio(total: number): string {
  if (total === 0) return 'nessuna partita';
  return total === 1 ? '1 partita' : `${total} partite`;
}

/**
 * L'estremo senza giorno non è un link morto: è un segno spento, fuori
 * dall'ordine di tabulazione e dichiarato come tale.
 */
function Freccia({
  data,
  verso,
  base,
}: {
  data: string | null;
  verso: 'precedente' | 'successivo';
  base: string;
}) {
  const glifo = verso === 'precedente' ? '‹' : '›';

  if (!data) {
    return (
      <span className="rail__freccia rail__freccia--spenta" aria-hidden="true">
        {glifo}
      </span>
    );
  }

  return (
    <a
      className="rail__freccia"
      href={`${base}/${data}/`}
      aria-label={`Giorno ${verso}, ${dataLunga(data)}`}
    >
      <span aria-hidden="true">{glifo}</span>
    </a>
  );
}
