'use client';

import { useMemo, useState } from 'react';

import { dataConAnno, suCento } from '@/lib/formato';
import { nomeCompetizione, TESTO_PROVENIENZA } from '@/lib/testi';
import type { RigaRegistro } from '@/lib/tipi';

import { ChipProvenienza } from './ChipProvenienza';

type Fase = 'preliminary' | 'definitive';
type Esito = 'uscito' | 'non-uscito' | 'attesa';

const GLIFO_SILENZIO: Record<string, string> = {
  S_min: '≈',
  no_candidates: '≈',
  sigma_max: '±',
  p_min: '<',
};

/**
 * Il registro dal vivo, nudo.
 *
 * I filtri sono <button aria-pressed> e filtrano righe GIÀ PRESENTI NEL DOM:
 * senza JavaScript la tabella resta completa e leggibile, che è il motivo per
 * cui non sono link con query string. Nessun filtro è preselezionato.
 *
 * I silenzi SONO nel registro: un registro che elenca solo i pronostici
 * nasconderebbe metà della propria disciplina.
 */
export function Registro({ righe }: { righe: RigaRegistro[] }) {
  const [fase, setFase] = useState<Fase | null>(null);
  const [esito, setEsito] = useState<Esito | null>(null);
  const [competizione, setCompetizione] = useState<string | null>(null);

  const competizioni = useMemo(
    () => [...new Set(righe.map((r) => r.competition))].sort(),
    [righe],
  );

  const visibili = righe.filter((r) => {
    if (fase && r.phase !== fase) return false;
    if (competizione && r.competition !== competizione) return false;
    if (esito) {
      const suo: Esito = r.outcome === 1 ? 'uscito' : r.outcome === 0 ? 'non-uscito' : 'attesa';
      if (suo !== esito) return false;
    }
    return true;
  });

  function commuta<T>(attuale: T | null, valore: T, imposta: (v: T | null) => void) {
    imposta(attuale === valore ? null : valore);
  }

  return (
    <section className="sezione--pesante" aria-labelledby="titolo-registro">
      <h2 id="titolo-registro" className="titolo-sezione">
        Il registro
      </h2>

      <div className="filtri">
        <div className="filtri__gruppo">
          <span className="label filtri__nome">Fase</span>
          {(['preliminary', 'definitive'] as const).map((v) => (
            <button
              key={v}
              type="button"
              className="filtro"
              aria-pressed={fase === v}
              onClick={() => commuta(fase, v, setFase)}
            >
              {v === 'preliminary' ? 'preliminare' : 'definitivo'}
            </button>
          ))}
        </div>

        <div className="filtri__gruppo">
          <span className="label filtri__nome">Esito</span>
          {(['uscito', 'non-uscito', 'attesa'] as const).map((v) => (
            <button
              key={v}
              type="button"
              className="filtro"
              aria-pressed={esito === v}
              onClick={() => commuta(esito, v, setEsito)}
            >
              {v === 'non-uscito' ? 'non uscito' : v === 'attesa' ? 'in attesa' : 'uscito'}
            </button>
          ))}
        </div>

        <div className="filtri__gruppo">
          <span className="label filtri__nome">Competizione</span>
          {competizioni.map((v) => (
            <button
              key={v}
              type="button"
              className="filtro"
              aria-pressed={competizione === v}
              onClick={() => commuta(competizione, v, setCompetizione)}
            >
              {nomeCompetizione(v)}
            </button>
          ))}
        </div>
      </div>

      <p className="micro registro__conteggio" role="status">
        {visibili.length === righe.length
          ? `${righe.length} righe`
          : `${visibili.length} righe su ${righe.length}`}
      </p>

      <div className="scorrevole">
        <table className="tabella">
          <caption>Ogni pronostico che abbiamo pubblicato prima della partita.</caption>
          <thead>
            <tr>
              <th scope="col">Scritto il</th>
              <th scope="col">Partita</th>
              <th scope="col">Fase</th>
              <th scope="col">Mercato</th>
              <th scope="col">Probabilità</th>
              <th scope="col">Esito</th>
            </tr>
          </thead>
          <tbody>
            {visibili.map((riga) => (
              <tr key={riga.prediction_id}>
                <td className="num">{dataConAnno(riga.written_at.slice(0, 10))}</td>
                <th scope="row">
                  <a className="registro__partita" href={`/partita/${riga.match_id}/`}>
                    {riga.home} — {riga.away}
                  </a>
                </th>
                <td>
                  <ChipProvenienza source={riga.source} compatto />
                </td>
                <td>
                  {riga.market_label ? (
                    riga.market_label
                  ) : (
                    <span className="registro__silenzio">
                      nessun pronostico{' '}
                      <span aria-hidden="true">
                        {riga.silence_reason ? GLIFO_SILENZIO[riga.silence_reason] : ''}
                      </span>
                    </span>
                  )}
                </td>
                <td className="num">{riga.p !== null ? `${suCento(riga.p)} su 100` : '—'}</td>
                <td>
                  <EsitoCella riga={riga} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {visibili.length === 0 ? (
        <p className="corpo" style={{ marginTop: 'var(--s-4)' }}>
          Nessuna riga con questi filtri. Premi di nuovo un filtro per toglierlo.
        </p>
      ) : null}

      <p className="definizione">
        La fase dice con quale informazione avevamo scritto: «{TESTO_PROVENIENZA.model_only}» prima
        che arrivassero le quote, «{TESTO_PROVENIENZA.blended_with_odds}» dopo. Le righe non si
        cancellano e non si riscrivono.
      </p>
    </section>
  );
}

/** Parola + glifo + colore. Mai il colore da solo. */
function EsitoCella({ riga }: { riga: RigaRegistro }) {
  if (riga.outcome === 1) {
    return (
      <span className="registro__esito esito-uscito">
        uscito <span aria-hidden="true">▪</span>
      </span>
    );
  }
  if (riga.outcome === 0) {
    return (
      <span className="registro__esito esito-non-uscito">
        non uscito <span aria-hidden="true">▫</span>
      </span>
    );
  }
  return (
    <span className="registro__esito esito-attesa">
      in attesa <span aria-hidden="true">—</span>
    </span>
  );
}
