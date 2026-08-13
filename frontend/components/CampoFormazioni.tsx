import type { Formazioni, GiocatoreInCampo, LatoFormazione } from '@/lib/tipi';

/**
 * IL CAMPO CON LE FORMAZIONI PROBABILI.
 *
 * Impaginazione verticale — casa in basso, ospiti in alto ribaltati — perche'
 * in verticale il campo entra nella larghezza di un telefono senza rimpicciolire
 * i nomi, ed e' sul telefono che una formazione si guarda davvero.
 *
 * NIENTE JAVASCRIPT. Le posizioni sono percentuali dentro una scatola con
 * proporzione fissa: il campo si ridimensiona da solo e non serve misurare
 * niente a runtime.
 *
 * ACCESSIBILITA'. Il campo e' una LISTA, non un disegno. Chi usa uno screen
 * reader sente i giocatori nell'ordine dal portiere all'attacco, con il ruolo;
 * la posizione sul terreno e' presentazione e non porta informazione che non
 * sia gia' nel testo. Il modulo e' scritto a parole accanto al titolo, non
 * lasciato dedurre dal disegno.
 *
 * QUANDO IL MODULO NON TORNA. `4-3-3` deve descrivere dieci giocatori di
 * movimento piu' il portiere. Se i conti non tornano — la fonte sbaglia, o
 * manda una formazione incompleta — non si indovina: si distribuiscono i
 * giocatori in righe uguali e il modulo dichiarato NON viene mostrato, perche'
 * mostrarlo accanto a una disposizione che non gli corrisponde sarebbe peggio
 * che non mostrarlo.
 */

/**
 * Il nome della squadra abbreviato quanto basta a non coprire il portiere.
 *
 * L'etichetta sta in un angolo del campo e il portiere al centro della linea
 * di porta: «Paris Saint-Germain FC» arrivava a sovrapporsi al suo nome.
 *
 * Prima si tolgono i suffissi societari, che non aggiungono niente su un
 * campo — nessuno guarda undici maglie e si chiede se sia una FC o una AFC.
 * Se non basta si usa la sigla, che le partite gia' portano con se': meglio
 * `PSG`, che chiunque legge, di un nome tagliato a meta' con i puntini.
 */
const SUFFISSI = /\s+(FC|AFC|CF|SC|AC|FK|BK|SK|CD|UD|SS|US|AS|IF|BV|SV)$/i;

function abbreviaSquadra(nome: string, tla?: string): string {
  const senzaSuffisso = nome.trim().replace(SUFFISSI, '').trim();
  if (senzaSuffisso.length <= 18) return senzaSuffisso;
  if (tla && tla.trim()) return tla.trim();
  return senzaSuffisso;
}

/** Il cognome, che e' quello che si legge su una maglia. */
function cognome(nome: string): string {
  const intero = nome.trim();
  const parti = intero.split(/\s+/);
  const ultima = parti.at(-1);
  if (!ultima || parti.length === 1) return intero;
  // "Nuno Mendes", "Joao Neves": due parole corte sono spesso entrambe il nome
  // d'arte. Sopra i 3 caratteri la seconda basta.
  return ultima.length >= 3 ? ultima : intero;
}

/**
 * Le righe del modulo, o `null` se non descrive questi giocatori.
 *
 * `null` non e' un errore da nascondere: e' il segnale che fa cadere il campo
 * sulla disposizione di ripiego e toglie il modulo dall'intestazione.
 */
function righeDelModulo(modulo: string | null | undefined, diMovimento: number): number[] | null {
  if (!modulo) return null;
  const numeri = modulo
    .split(/[-–]/)
    .map((p) => Number.parseInt(p.trim(), 10))
    .filter((n) => Number.isFinite(n) && n > 0);
  if (numeri.length === 0) return null;
  const somma = numeri.reduce((a, b) => a + b, 0);
  return somma === diMovimento ? numeri : null;
}

/** Ripiego: righe il piu' uguali possibile. */
function righeDiRipiego(diMovimento: number): number[] {
  if (diMovimento <= 0) return [];
  const perRiga = 4;
  const righe: number[] = [];
  let restanti = diMovimento;
  while (restanti > 0) {
    const n = Math.min(perRiga, restanti);
    righe.push(n);
    restanti -= n;
  }
  return righe;
}

type Posizionato = { g: GiocatoreInCampo; x: number; y: number };

/**
 * Colloca gli undici. `dallAlto` ribalta il lato ospite.
 *
 * Il portiere sta sulla linea di porta, il resto si distribuisce fra il 18% e
 * il 46% dell'altezza totale: mezzo campo per squadra, con il centrocampo che
 * si ferma prima della meta' per non accavallarsi con gli avversari.
 */
function collocare(lato: LatoFormazione, dallAlto: boolean): { posti: Posizionato[]; moduloOk: boolean } {
  const titolari = lato.titolari ?? [];
  if (titolari.length === 0) return { posti: [], moduloOk: false };

  const portiere = titolari[0];
  if (!portiere) return { posti: [], moduloOk: false };
  const movimento = titolari.slice(1);
  const righe = righeDelModulo(lato.modulo, movimento.length);
  const moduloOk = righe !== null;
  const disposizione = righe ?? righeDiRipiego(movimento.length);

  const posti: Posizionato[] = [];
  const yPortiere = dallAlto ? 4 : 96;
  posti.push({ g: portiere, x: 50, y: yPortiere });

  const yPrima = 17;
  const yUltima = 45;
  const passo = disposizione.length > 1 ? (yUltima - yPrima) / (disposizione.length - 1) : 0;

  let indice = 0;
  disposizione.forEach((quanti, r) => {
    const yMeta = yPrima + passo * r;
    const y = dallAlto ? yMeta : 100 - yMeta;
    for (let i = 0; i < quanti; i += 1) {
      const g = movimento[indice];
      indice += 1;
      if (!g) break;
      // Distribuzione orizzontale con margine ai lati, cosi' i nomi delle ali
      // non escono dal campo.
      const x = 12 + ((i + 0.5) / quanti) * 76;
      posti.push({ g, x, y });
    }
  });

  return { posti, moduloOk };
}

function Lato({
  lato,
  squadra,
  sigla,
  dallAlto,
}: {
  lato: LatoFormazione;
  squadra: string;
  sigla?: string;
  dallAlto: boolean;
}) {
  const { posti, moduloOk } = collocare(lato, dallAlto);
  if (posti.length === 0) return null;

  return (
    <>
      <p className={`campo__squadra ${dallAlto ? 'campo__squadra--alto' : 'campo__squadra--basso'}`}>
        <span className="campo__nome-squadra" title={squadra}>
          {abbreviaSquadra(squadra, sigla)}
        </span>
        {moduloOk && lato.modulo ? <span className="campo__modulo">{lato.modulo}</span> : null}
      </p>
      <ul className={`campo__lato ${dallAlto ? 'campo__lato--ospiti' : 'campo__lato--casa'}`}>
        {posti.map(({ g, x, y }) => (
          <li
            key={`${g.id ?? g.nome}`}
            className="campo__posto"
            style={{ left: `${x}%`, top: `${y}%` }}
          >
            <span className="campo__maglia" aria-hidden="true">
              {g.maglia ?? ''}
            </span>
            <span className="campo__giocatore">
              <span className="campo__cognome">{cognome(g.nome)}</span>
              <span className="solo-lettori">
                {' '}
                — {g.nome}
                {g.ruolo ? `, ${g.ruolo}` : ''}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

/** «probabili, lette 5 ore prima» — la fiducia sta nel quando, non nel se. */
function quandoLette(ore: number | null | undefined): string | null {
  if (typeof ore !== 'number' || ore <= 0) return null;
  if (ore < 1.5) return 'lette meno di un’ora e mezza prima';
  if (ore < 24) return `lette circa ${Math.round(ore)} ore prima`;
  const giorni = Math.round(ore / 24);
  return `lette circa ${giorni} ${giorni === 1 ? 'giorno' : 'giorni'} prima`;
}

export function CampoFormazioni({
  formazioni,
  casa,
  ospiti,
  siglaCasa,
  siglaOspiti,
}: {
  formazioni: Formazioni;
  casa: string;
  ospiti: string;
  siglaCasa?: string;
  siglaOspiti?: string;
}) {
  const hoCasa = (formazioni.casa?.titolari?.length ?? 0) > 0;
  const hoOspiti = (formazioni.ospiti?.titolari?.length ?? 0) > 0;
  if (!hoCasa && !hoOspiti) return null;

  const quando = quandoLette(formazioni.ore_prima);

  return (
    <section className="sezione formazioni" id="formazioni" aria-labelledby="titolo-formazioni">
      <h2 id="titolo-formazioni" className="label sezione__titolo">
        <span className="bersaglio" aria-hidden="true" /> Le formazioni
      </h2>

      <p className={`formazioni__stato ${formazioni.confermate ? 'is-ufficiali' : 'is-probabili'}`}>
        <strong>{formazioni.confermate ? 'Ufficiali' : 'Probabili'}</strong>
        {formazioni.confermate ? (
          <> — annunciate dalle squadre.</>
        ) : (
          <>
            {' '}
            — non ancora annunciate{quando ? `, ${quando}` : ''}. Possono cambiare fino al calcio
            d’inizio.
          </>
        )}
      </p>

      <div className="campo" role="group" aria-label="Disposizione in campo">
        <div className="campo__erba" aria-hidden="true">
          <span className="campo__meta" />
          <span className="campo__cerchio" />
          <span className="campo__area campo__area--alto" />
          <span className="campo__area campo__area--basso" />
        </div>
        {hoOspiti ? (
          <Lato lato={formazioni.ospiti} squadra={ospiti} sigla={siglaOspiti} dallAlto />
        ) : null}
        {hoCasa ? (
          <Lato lato={formazioni.casa} squadra={casa} sigla={siglaCasa} dallAlto={false} />
        ) : null}
      </div>
    </section>
  );
}
