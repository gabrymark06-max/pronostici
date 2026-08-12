"""Scelta del pronostico consigliato: passi 4-8 della pipeline (ricerca 8.1).

Il vincolo di prodotto dell'utente - *"se e' presente una value bet alta ma e'
veramente difficile che esca, non gliela consigliamo"* - **non e' imposto con
una soglia**: e' gia' dentro la matematica. Il punteggio e' la divergenza KL
fra la nostra probabilita' e il riferimento, che coincide esattamente con il
tasso di crescita log-ottimale di Kelly. A parita' di vantaggio del 10%, il
punteggio cade di 124 volte passando da p=0,75 a p=0,02.

Quando si tace, si persiste **quale filtro ha morso**: il frontend ne ha
bisogno per scrivere tre messaggi diversi (brief 8.4), e un booleano non
basterebbe.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .markets import catalog

# Tabella dei parametri, ricerca 8.3. Valori iniziali motivati, non frutto di
# grid search: con due stagioni il budget statistico non la permette (7.2).
P_MIN = 0.50  # sicurezza: non consigliamo esiti meno probabili che no
SIGMA_MAX = 0.12  # sicurezza: stima troppo instabile per dire qualcosa
# Editoriale: sotto questa soglia il pronostico non dice niente piu' della
# media. E' l'unica manopola, e non e' stata scelta a mano: il backtest del
# 2026-08-08 (521 rifit, 4.995 partite) ha misurato la curva soglia -> tasso di
# silenzio, e 0,008 e' il punto che porta il silenzio al 26,0%, il piu' vicino
# al 25% dichiarato nel protocollo *prima* della corsa. Il valore precedente
# (0,005) taceva sul 17,4%. Si sceglie il tasso, si legge la soglia.
S_MIN = 0.008
RHO_MAX = 0.80  # soglia di clustering per correlazione
# Ricaduta quando il backtest non ha ancora misurato una famiglia (ricerca 8.3).
# I valori veri arrivano da `model.tau.load_tau_by_family`.
TAU_DEFAULT = 0.08

# Famiglie che si **calcolano e si mostrano** ma non concorrono al consigliato.
#
# 2026-08-11, over/under. Il backtest del 2026-08-08 aveva gia' pubblicato il
# risultato negativo (log loss 0,69922 contro 0,68855 del base rate su Over
# 2.5). L'indagine di `jobs/halflife.py` su 5.018 partite ha escluso le tre
# cause sospette:
#
# * l'emivita: su tutta la griglia 120-540 giorni il modello resta sotto il base
#   rate, con uno scarto fra 0,0134 e 0,0182 nats e un errore standard di 0,004;
# * la correzione Dixon-Coles: le sue quattro celle stanno **tutte** sotto la
#   linea 2.5 e le loro correzioni si annullano, quindi su Over 2.5 il suo
#   effetto e' esattamente zero (verificato in `tests/test_matrix_totals.py`);
# * il troncamento: massa persa 3,1e-05, e con `max_goals = 18` il log loss
#   cambia di 2e-05.
#
# Resta la spiegazione semplice: la nostra stima per-partita dei **gol totali**
# non porta informazione. La ricalibrazione logistica in-sample - un limite
# superiore, quindi ottimistico - guadagna 0,0024 nats sul base rate.
#
# --- RIAMMESSA IL 12 AGOSTO 2026, SU RICHIESTA ESPLICITA ---------------------
#
# Il proprietario ha chiesto che over/under torni consigliabile, conoscendo
# questo risultato. E' una sua decisione e va rispettata; ma la misura resta
# quella, e allora il prodotto deve dirlo dove il pronostico compare. Il
# frontend mostra un avviso dedicato su ogni pronostico di questa famiglia
# (`components/AvvisoOverUnder.tsx`): senza quell'avviso il sito prometterebbe
# una cosa che i suoi stessi numeri smentiscono, e la promessa del prodotto -
# «ci facciamo misurare in pubblico» - varrebbe zero.
#
# L'insieme resta e resta usato: e' il parametro con cui il backtest riproduce
# il braccio di confronto, e sara' il posto dove rimettere over/under se il
# prossimo test storico confermasse il risultato negativo su piu' dati.
NON_SELECTABLE_FAMILIES: frozenset[str] = frozenset()

EPS = 1e-9


def kl_binary(p: np.ndarray | float, q: np.ndarray | float) -> np.ndarray | float:
    """Divergenza KL binaria D(p||q), in nats.

    `q` e' la quota sgonfiata dove esiste, il base rate dove non esiste: lo
    stesso identico codice serve i due casi (ricerca 3.3).

    Attenzione: e' positiva **in entrambe le direzioni**. Misura quanta
    informazione abbiamo rispetto al riferimento, non da che parte stare. Per
    ordinare i pronostici serve `directional_score`.
    """
    p = np.clip(p, EPS, 1 - EPS)
    q = np.clip(q, EPS, 1 - EPS)
    return p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))


def directional_score(p: np.ndarray | float, q: np.ndarray | float) -> np.ndarray:
    """Tasso di crescita log-ottimale di Kelly per **scommettere sull'evento**.

    Kelly (ricerca 2.1, eq. 3) e' esplicito: `k(p) = 0` quando `p <= 1/theta`,
    cioe' quando la nostra probabilita' non supera quella di riferimento. In
    quel caso l'informazione c'e' ma punta dalla parte opposta: la mossa
    ottimale e' l'evento complementare, non questo.

    Usare la KL nuda come punteggio consiglierebbe eventi che riteniamo
    **meno** probabili del riferimento - vantaggio atteso negativo, con un
    punteggio alto. Qui il punteggio e' zero e il filtro `S_min` li elimina.
    """
    p_arr = np.asarray(p, dtype=float)
    q_arr = np.asarray(q, dtype=float)
    return np.where(p_arr > q_arr, kl_binary(p_arr, q_arr), 0.0)


def shrink(
    p_hat: np.ndarray | float, sigma: np.ndarray | float, q_ref: np.ndarray | float,
    tau: np.ndarray | float,
) -> tuple[np.ndarray, np.ndarray]:
    """Media a posteriori, Smith & Winkler (2006) eq. 6a-6b.

    Senza questo passo l'argmax su 11 mercati sovrastima di ~1,5 sigma
    (maledizione dell'ottimizzatore). Con sigma realistica (~0,10) il
    punteggio si riduce di circa 6,5 volte: e' il prezzo onesto di avere due
    stagioni di dati.
    """
    tau2 = np.maximum(np.asarray(tau, dtype=float) ** 2, EPS)
    alpha = 1.0 / (1.0 + np.asarray(sigma, dtype=float) ** 2 / tau2)
    return alpha * np.asarray(p_hat) + (1 - alpha) * np.asarray(q_ref), alpha


def market_correlation(
    matrix: np.ndarray, mask_a: np.ndarray, mask_b: np.ndarray
) -> float:
    """Correlazione **esatta** fra due mercati binari, dalla matrice congiunta.

    Non stimata dallo storico: alcuni mercati sono annidati (Over 2.5 dentro
    Over 1.5) e una correlazione empirica li tratterebbe male.
    """
    pa = float(matrix[mask_a].sum())
    pb = float(matrix[mask_b].sum())
    pab = float(matrix[mask_a & mask_b].sum())
    den = np.sqrt(pa * (1 - pa) * pb * (1 - pb))
    return 0.0 if den <= EPS else float((pab - pa * pb) / den)


def correlation_matrix(matrix: np.ndarray, keys: list[str], max_goals: int) -> np.ndarray:
    """Matrice di correlazione fra i mercati candidati, tutta dalla matrice."""
    masks = {d.key: d.mask for d in catalog(max_goals)}
    flat = matrix.ravel()
    sel = [masks[k].ravel() for k in keys]
    probs = np.array([flat[m].sum() for m in sel])
    n = len(keys)
    corr = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            pab = float(flat[sel[i] & sel[j]].sum())
            den = np.sqrt(probs[i] * (1 - probs[i]) * probs[j] * (1 - probs[j]))
            value = 0.0 if den <= EPS else (pab - probs[i] * probs[j]) / den
            corr[i, j] = corr[j, i] = value
    return corr


def single_linkage_clusters(
    corr: np.ndarray, threshold: float = RHO_MAX
) -> list[list[int]]:
    """Cluster a legame singolo su |correlazione| >= soglia.

    Riduce tipicamente ~90 mercati a pochi cluster: e' quello il **numero
    effettivo di prove** su cui si fa argmax, e da cui dipende quanto morde la
    maledizione dell'ottimizzatore.
    """
    n = corr.shape[0]
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if abs(corr[i, j]) >= threshold:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [sorted(v) for v in groups.values()]


@dataclass
class Candidate:
    key: str
    family: str
    label: str
    p_hat: float  # media bootstrap, non shrinkata
    sigma: float  # sd bootstrap
    p5: float
    p95: float
    p_tilde: float  # dopo shrinkage: l'unica mostrabile all'utente
    alpha: float
    reference: float
    score: float
    passes_p_min: bool
    passes_sigma_max: bool
    passes_s_min: bool
    # Una famiglia esclusa dalla selezione produce comunque il suo candidato:
    # serve a misurarla (tau^2 per famiglia, log loss contro il base rate) anche
    # quando non puo' piu' vincere. Toglierla dal calcolo renderebbe cieco
    # proprio il numero che ha motivato l'esclusione.
    selectable: bool = True

    @property
    def survives(self) -> bool:
        return (
            self.selectable
            and self.passes_p_min
            and self.passes_sigma_max
            and self.passes_s_min
        )

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "family": self.family,
            "label": self.label,
            "p": round(self.p_tilde, 4),
            "p_raw": round(self.p_hat, 4),
            "sigma": round(self.sigma, 4),
            "band_p5": round(self.p5, 4),
            "band_p95": round(self.p95, 4),
            "shrink_alpha": round(self.alpha, 4),
            "reference": round(self.reference, 4),
            "score": round(self.score, 6),
        }


@dataclass
class Selection:
    """Il risultato: un pronostico, oppure il silenzio con la sua ragione."""

    pick: Candidate | None
    silence_reason: str | None  # "S_min" | "sigma_max" | "p_min" | "no_candidates"
    n_candidates: int
    n_clusters: int
    cluster_members: list[str] = field(default_factory=list)
    filter_bites: dict[str, int] = field(default_factory=dict)
    runners_up: list[Candidate] = field(default_factory=list)

    @property
    def is_silent(self) -> bool:
        return self.pick is None


def build_candidates(
    probs_by_draw: dict[str, np.ndarray],
    references: dict[str, float],
    *,
    tau: float | dict[str, float] = TAU_DEFAULT,
    selectable_keys: set[str] | None = None,
    excluded_families: frozenset[str] | None = None,
    include_unselectable: bool = False,
    max_goals: int = 12,
) -> list[Candidate]:
    """Passi 2-5: incertezza, riferimento, shrinkage, punteggio.

    `include_unselectable=True` restituisce **anche** i mercati che non possono
    vincere, marcati `selectable=False`. Non li rende eleggibili — `select` li
    scarta comunque — ma permette al backtest di continuare a misurare le
    famiglie escluse. E' l'unico modo di sapere se un giorno tornassero a
    portare informazione.

    `excluded_families=None` significa "quelle di produzione". Passare un
    insieme vuoto le riammette tutte: serve ai bracci di confronto del backtest,
    che devono poter riprodurre la configurazione **precedente** all'esclusione.
    Un parametro che sapesse solo restringere renderebbe impossibile misurare
    cosa si e' guadagnato togliendo una famiglia.
    """
    excluded = (
        NON_SELECTABLE_FAMILIES if excluded_families is None else excluded_families
    )
    defs = {d.key: d for d in catalog(max_goals)}
    out: list[Candidate] = []
    for key, draws in probs_by_draw.items():
        definition = defs.get(key)
        if definition is None:
            continue
        selectable = (
            definition.selectable
            and definition.family not in excluded
            and (selectable_keys is None or key in selectable_keys)
        )
        if not selectable and not include_unselectable:
            continue
        reference = references.get(key)
        if reference is None:
            continue

        p_hat = float(draws.mean())
        sigma = float(draws.std(ddof=1))
        p5, p95 = (float(v) for v in np.percentile(draws, [5, 95]))
        tau_value = tau[definition.family] if isinstance(tau, dict) else tau
        p_tilde, alpha = shrink(p_hat, sigma, reference, tau_value)
        p_tilde = float(p_tilde)
        score = float(directional_score(p_tilde, reference))

        out.append(
            Candidate(
                key=key,
                family=definition.family,
                label=definition.label,
                p_hat=p_hat,
                sigma=sigma,
                p5=p5,
                p95=p95,
                p_tilde=p_tilde,
                alpha=float(alpha),
                reference=reference,
                score=score,
                passes_p_min=p_tilde >= P_MIN,
                passes_sigma_max=sigma <= SIGMA_MAX,
                passes_s_min=score >= S_MIN,
                selectable=selectable,
            )
        )
    return out


def _silence_reason(candidates: list[Candidate]) -> str:
    """Quale filtro ha morso, in ordine di priorita'.

    L'ordine non e' arbitrario: si riporta `S_min` solo se qualcosa aveva gia'
    superato i due filtri di sicurezza, cioe' solo quando il messaggio "non
    abbiamo niente da aggiungere" e' quello vero. Mappa 1:1 sui tre testi
    dell'interfaccia (brief 8.4).
    """
    if not candidates:
        return "no_candidates"
    safe = [c for c in candidates if c.passes_p_min and c.passes_sigma_max]
    if safe:
        return "S_min"
    probable = [c for c in candidates if c.passes_p_min]
    if probable:
        return "sigma_max"
    return "p_min"


def select(
    candidates: list[Candidate],
    matrix: np.ndarray,
    *,
    rho_max: float = RHO_MAX,
    max_goals: int = 12,
) -> Selection:
    """Passi 6-8: filtri duri, clustering, scelta, oppure silenzio.

    I candidati non eleggibili escono **prima** di ogni conteggio: `n_candidates`
    e `filter_bites` sono quello che l'utente vede scritto sulla scheda del
    silenzio ("abbiamo esaminato N mercati"), e devono contare i mercati che
    potevano davvero essere consigliati.
    """
    candidates = [c for c in candidates if c.selectable]
    bites = {
        "p_min": sum(1 for c in candidates if not c.passes_p_min),
        "sigma_max": sum(1 for c in candidates if not c.passes_sigma_max),
        "S_min": sum(1 for c in candidates if not c.passes_s_min),
    }
    survivors = [c for c in candidates if c.survives]
    if not survivors:
        return Selection(
            pick=None,
            silence_reason=_silence_reason(candidates),
            n_candidates=len(candidates),
            n_clusters=0,
            filter_bites=bites,
        )

    keys = [c.key for c in survivors]
    corr = correlation_matrix(matrix, keys, max_goals)
    clusters = single_linkage_clusters(corr, rho_max)

    # Si sceglie il CLUSTER con punteggio massimo...
    best_cluster = max(clusters, key=lambda idx: max(survivors[i].score for i in idx))
    # ...e dentro il cluster il membro con probabilita' piu' alta.
    # E' qui che il vincolo di prodotto morde di piu': a punteggi
    # confrontabili preferisce Over 1.5 a Over 2.5, doppia chance a 1X2.
    winner = max(best_cluster, key=lambda i: survivors[i].p_tilde)
    pick = survivors[winner]

    others = sorted(
        (survivors[i] for i in best_cluster if i != winner),
        key=lambda c: -c.p_tilde,
    )
    runners = sorted(
        (c for j, c in enumerate(survivors) if j not in best_cluster),
        key=lambda c: -c.score,
    )[:5]

    return Selection(
        pick=pick,
        silence_reason=None,
        n_candidates=len(candidates),
        n_clusters=len(clusters),
        cluster_members=[c.key for c in others],
        filter_bites=bites,
        runners_up=runners,
    )
