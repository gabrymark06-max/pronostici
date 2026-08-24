/**
 * DA DOVE SI LEGGE IL CONTORNO DI UNA PARTITA.
 *
 * Ci sono due campi, e non e' un pasticcio da sistemare: e' la storia del
 * progetto scritta nei dati. Fino al 24 agosto 2026 arbitro, formazioni e
 * quote estese arrivavano tutti da Sofascore e stavano in `sofascore`. Da quel
 * giorno Sofascore emette il token che autorizza la sua API solo dentro un
 * browser e solo per IP residenziali, e il job e' passato a due fonti nuove
 * che scrivono in `contorno`.
 *
 * I file vecchi non si riscrivono. Contengono cose che le fonti nuove non
 * hanno — le medie cartellini dell'arbitro, i mercati estesi — e sono state
 * lette davvero da Sofascore: ricopiarle sotto un'altra insegna le perderebbe
 * invece di salvarle.
 *
 * Quindi nessun componente legge i due campi da solo. Si passa da qui, e da
 * qui esce un blocco solo.
 */
import type { Contorno, Fixture } from './tipi';

/**
 * Il contorno di una partita, da qualunque delle due epoche venga.
 *
 * `contorno` vince su `sofascore` quando ci sono entrambi: e' quello che il
 * job piu' recente ha scritto, quindi e' quello aggiornato.
 */
export function contornoDi(fixture: Fixture): Contorno | null {
  return fixture.contorno ?? fixture.sofascore ?? null;
}

/**
 * Come chiamare la fonte di una sezione, in italiano leggibile.
 *
 * I dati di prima non hanno nessun campo `fonte` — quando sono stati scritti
 * c'era una fonte sola e nominarla sarebbe stato ridondante. L'assenza quindi
 * non e' ignoranza: e' Sofascore, ed e' giusto poterlo dire.
 */
export function nomeFonte(fonte: string | undefined): string {
  switch (fonte) {
    case 'sportsgambler':
      return 'Sportsgambler';
    case 'football-data':
      return 'football-data.org';
    default:
      return 'Sofascore';
  }
}
