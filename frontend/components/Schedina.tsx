import { ora, suCento } from '@/lib/formato';
import { formattaQuota } from '@/lib/quote';
import type { Gamba, Schedina as Combinazione } from '@/lib/schedine';

import { Crest } from './Crest';
import { interno } from '@/lib/sito';

/**
 * UNA SCHEDINA — le partite che la compongono, e quanto vale davvero.
 *
 * IL NUMERO GRANDE E' LA PROBABILITA', NON LA QUOTA. Ovunque altrove le
 * schedine si presentano dalla quota — «multipla a 5,20!» — perche' la quota e'
 * l'unico numero che cresce quando la scommessa peggiora. Qui il numero grande
 * e' quello che cala: quante volte su cento esce tutta intera.
 *
 * E' l'informazione che decide, ed e' la stessa cosa della quota scritta al
 * contrario: la nostra quota E' 1 diviso la probabilita', quindi una schedina
 * a 5,00 vale 20 su 100 comunque la si componga. Mettere grande la quota
 * significherebbe mettere grande il numero che non aggiunge niente.
 *
 * OGNI GAMBA PORTA LA SUA PROBABILITA', accanto al suo pronostico. Serve a
 * vedere da dove viene il crollo: cinque gambe da 80 su 100 fanno 33 su 100
 * tutte insieme, e nessuna delle cinque sembrava rischiosa. E' la cosa che una
 * schedina nasconde per costruzione, e qui e' in colonna.
 *
 * A PARTITA CONCLUSA ogni gamba dice com'e' andata e la schedina dice se e'
 * uscita. Una gamba sbagliata basta: si vede subito quale.
 */

const TITOLI: Record<Combinazione['tipo'], { nome: string; occhiello: string }> = {
  raddoppio: { nome: 'Il raddoppio', occhiello: 'Due partite' },
  multipla: { nome: 'La multipla', occhiello: 'Il minor numero di partite per arrivare a 5,00' },
};

function Esito({ uscito }: { uscito: boolean | null }) {
  if (uscito === null) {
    return (
      <span className="gamba__esito gamba__esito--attesa">
        <span className="solo-lettori">Non ancora giocata</span>
        <span aria-hidden="true">·</span>
      </span>
    );
  }
  return (
    <span className={`gamba__esito gamba__esito--${uscito ? 'si' : 'no'}`}>
      {uscito ? 'uscito' : 'non uscito'}
    </span>
  );
}

function Riga({ gamba, crest }: { gamba: Gamba; crest: (url: string | null) => string | null }) {
  const { fixture, pronostico } = gamba;
  return (
    <li className="gamba">
      <a className="gamba__link" href={interno(`/partita/${fixture.match_id}/`)}>
        <span className="gamba__ora">{ora(fixture.utc_date)}</span>

        <span className="gamba__squadre">
          <span className="gamba__squadra">
            <Crest src={crest(fixture.home.crest)} tla={fixture.home.tla} />
            {fixture.home.name}
          </span>
          <span className="gamba__squadra">
            <Crest src={crest(fixture.away.crest)} tla={fixture.away.tla} />
            {fixture.away.name}
          </span>
        </span>

        <span className="gamba__mercato">{pronostico.label}</span>

        <span className="gamba__p num">
          {suCento(pronostico.p)}
          <span className="gamba__unita"> su 100</span>
        </span>

        <span className="gamba__quota num">
          {gamba.prezzo !== null ? (
            formattaQuota(gamba.prezzo)
          ) : (
            <span aria-hidden="true">—</span>
          )}
        </span>

        <Esito uscito={gamba.uscito} />
      </a>
    </li>
  );
}

export function Schedina({
  schedina,
  crest,
}: {
  schedina: Combinazione;
  crest: (url: string | null) => string | null;
}) {
  const titolo = TITOLI[schedina.tipo];
  const conclusa = schedina.esito !== 'in-corso';

  return (
    <section className={`schedina schedina--${schedina.esito}`}>
      <header className="schedina__testa">
        <div>
          <p className="label">
            <span className="bersaglio" aria-hidden="true" /> {titolo.nome}
          </p>
          <p className="schedina__occhiello">{titolo.occhiello}</p>
        </div>

        <div className="schedina__perno">
          <p className="cifra">{suCento(schedina.p)}</p>
          <p className="schedina__unita">su 100 esce tutta intera</p>
        </div>
      </header>

      <ul className="schedina__gambe">
        {schedina.gambe.map((g) => (
          <Riga key={g.fixture.match_id} gamba={g} crest={crest} />
        ))}
      </ul>

      <div className="schedina__piede">
        {/* IL PREZZO O NIENTE. Qui c'era il prodotto delle nostre quote eque
            — `1/probabilita'` moltiplicate fra loro — presentato sotto la
            parola «Quota». Nessuno paga quel numero: la probabilita' che la
            schedina esca tutta intera e' gia' scritta in testa, ed e' la cosa
            che sappiamo. */}
        <p className="schedina__quota">
          <span className="label">Prezzo</span>{' '}
          {schedina.prezzo !== null ? (
            <>
              <strong className="num">{formattaQuota(schedina.prezzo)}</strong>{' '}
              <span className="schedina__mercato">
                moltiplicando i prezzi trovati sulle {schedina.gambe.length} gambe
              </span>
            </>
          ) : (
            <span className="schedina__mercato">
              non calcolabile: almeno una gamba &egrave; su un mercato che nessuna
              fonte quota
            </span>
          )}
        </p>

        {conclusa ? (
          <p className={`schedina__verdetto schedina__verdetto--${schedina.esito}`}>
            {schedina.esito === 'uscita'
              ? 'Uscita tutta intera.'
              : `Non uscita: ${schedina.gambe.filter((g) => g.uscito === false).length} su ${schedina.gambe.length} sbagliate.`}
          </p>
        ) : schedina.concluse > 0 ? (
          <p className="schedina__verdetto">
            {schedina.concluse} su {schedina.gambe.length} già giocate, tutte a posto finora.
          </p>
        ) : null}
      </div>

      {!schedina.bersaglioRaggiunto ? (
        <p className="schedina__nota">
          <strong>
            Questa schedina non scende sotto {suCento(schedina.bersaglioP)} su 100.
          </strong>{' '}
          Le
          partite di oggi su cui ci esponiamo sono poche o tutte molto probabili, e non c’è
          combinazione che ci arrivi. Preferiamo mostrarla più bassa che allungarla con
          pronostici che non faremmo.
        </p>
      ) : null}
    </section>
  );
}
