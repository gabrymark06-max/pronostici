/**
 * LA GIORNATA: calendario, campionati, partite. Una sola volta, due indirizzi.
 *
 * `/giorno/<data>/` e `/` mostrano la stessa cosa, e fino al 25 agosto 2026
 * non era vero: la radice era un `<meta refresh>` verso il giorno di apertura,
 * quindi chi apriva il sito trovava una pagina quasi bianca con un link e
 * aspettava che il browser lo seguisse. Su una connessione lenta quel mezzo
 * secondo e' la prima impressione del prodotto, e diceva «qui non c'e' niente».
 *
 * Adesso la radice RENDE la giornata, e il `refresh` non c'e' piu'. Il
 * canonical continua a puntare a `/giorno/<data>/`: e' lo stesso contenuto a
 * due indirizzi, e i motori devono sapere quale dei due e' l'originale.
 */
import { BloccoCampionato } from '@/components/BloccoCampionato';
import { Calendario } from '@/components/Calendario';
import { rangoCompetizione } from '@/lib/campionati';
import {
  finestraGiorni,
  giorniVicini,
  leggiAccuracy,
  leggiBacktest,
  leggiGiorno,
  manifestoCrest,
  riepilogoGiorni,
} from '@/lib/dati';
import { recordDiFascia } from '@/lib/fascia';
import { dataLunga, dataLungaMaiuscola } from '@/lib/formato';
import { fraseRevisioniDelGiorno } from '@/lib/testi';
import { tace, type Fixture } from '@/lib/tipi';

/**
 * Raggruppa per campionato, nell'ORDINE DICHIARATO in lib/campionati.ts.
 *
 * L'ordine per primo calcio d'inizio cambierebbe ogni giorno, e un lettore non
 * potrebbe imparare dove sta il suo campionato. Un ordine stabile è metà
 * dell'organizzazione per campionati.
 */
function perCampionato(fixtures: Fixture[]): { codice: string; partite: Fixture[] }[] {
  const gruppi = new Map<string, Fixture[]>();
  for (const f of fixtures) {
    const esistente = gruppi.get(f.competition);
    if (esistente) esistente.push(f);
    else gruppi.set(f.competition, [f]);
  }
  return [...gruppi.entries()]
    .map(([codice, partite]) => ({
      codice,
      partite: [...partite].sort((a, b) => a.utc_date.localeCompare(b.utc_date)),
    }))
    .sort(
      (a, b) =>
        rangoCompetizione(a.codice) - rangoCompetizione(b.codice) ||
        a.codice.localeCompare(b.codice),
    );
}

/** "14 partite" / "1 partita" / "nessuna partita" — per il titolo non visibile. */
function etichettaPartite(totale: number): string {
  if (totale === 0) return 'nessuna partita';
  return totale === 1 ? '1 partita' : `${totale} partite`;
}

/** `null` quando quel giorno non ha mai avuto un file: chi chiama decide cosa farne. */
export function VistaGiorno({ data }: { data: string }) {
  const giorno = leggiGiorno(data);
  if (!giorno) return null;

  const { precedente, successivo } = giorniVicini(data);
  const manifesto = manifestoCrest();
  const crest = (url: string | null) => (url ? (manifesto[url] ?? url) : null);

  /* I due file si leggono una volta sola per pagina, e nella riga arriva già
     un solo record etichettato con la propria provenienza. */
  const accuracy = leggiAccuracy();
  const backtest = leggiBacktest();
  const record = (fixture: Fixture) =>
    tace(fixture) ? null : recordDiFascia(fixture.prediction.p, accuracy, backtest);

  const gruppi = perCampionato(giorno.fixtures);
  const revisioni = fraseRevisioniDelGiorno(giorno.fixtures);
  const silenzi = giorno.silence_count;

  return (
    <>
      <Calendario
        giorni={riepilogoGiorni(finestraGiorni(data, 9))}
        corrente={data}
        precedente={precedente}
        successivo={successivo}
      />

      {/* IL TITOLO NON SI VEDE, ma esiste.
          La data e il conteggio sono già nella striscia dei giorni, che porta
          sigla, numero, totale delle partite e segna il giorno corrente:
          ripeterli in prosa era un titolo che spiegava il controllo che gli
          stava sopra. Resta l'<h1> per i motori e per chi ascolta — nascosto
          alla vista, MAI `display:none`, che lo toglierebbe anche a loro. */}
      <h1 className="solo-lettori">
        {dataLungaMaiuscola(data)} — {etichettaPartite(giorno.total)}
        {silenzi > 0 ? `, ${silenzi} in silenzio` : ''}
      </h1>

      {giorno.total === 0 ? (
        /* Un giorno senza partite NON è un silenzio e non deve somigliargli:
           niente lastra, niente glifo. */
        <div className="colonna colonna--lista">
          <div className="giorno-vuoto">
            <p>Il {dataLunga(data)} non si gioca in nessuno dei campionati che seguiamo.</p>
            <p>Il calendario qui sopra porta ai giorni in cui si gioca.</p>
          </div>
        </div>
      ) : (
        <div className="lastra">
          <div className="colonna colonna--lista">
            {/* La riga delle revisioni descrive la LISTA, non la giornata: sta
                in testa a ciò che descrive, e compare solo nei giorni in cui
                qualcosa è davvero cambiato. */}
            {revisioni ? <p className="lista__revisioni">{revisioni}</p> : null}

            {gruppi.map((gruppo) => (
              <BloccoCampionato
                key={gruppo.codice}
                codice={gruppo.codice}
                partite={gruppo.partite}
                crest={crest}
                record={record}
              />
            ))}
          </div>
        </div>
      )}
    </>
  );
}

export { etichettaPartite };
