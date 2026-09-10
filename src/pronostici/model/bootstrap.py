"""Bootstrap parametrico: l'incertezza dei parametri, per campionato.

L'osservazione che dimensiona tutto (brief 5.1): i 300 draw **non si fanno
per partita, si fanno per campionato**. Il costo sta nel rifit, e il rifit
dipende solo dai risultati del campionato. Si persistono i 300 vettori di
parametri; scorare una fixture significa poi costruire 300 matrici, che sono
prodotti esterni di Poisson: millisecondi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .dixon_coles import DCParams, MatchData, fit

DEFAULT_DRAWS = 300

# Quanto della distanza dalla media si porta dietro una squadra presa in
# prestito da un altro campionato (vedi `BootstrapResult.con_prestiti`).
# 0,7: chi domina un campionato non domina la Champions, ma non e' nemmeno
# una squadra qualunque. E' un giudizio, e sta qui per poter diventare una
# misura quando il backtest avra' abbastanza partite di coppa da dirlo.
PRESTITO_SHRINK = 0.7


def _non_zero(sigma: np.ndarray) -> np.ndarray:
    """Una deviazione standard nulla non deve dividere per zero."""
    return np.where(sigma > 1e-9, sigma, 1.0)


@dataclass(frozen=True)
class BootstrapResult:
    point: DCParams
    attack: np.ndarray  # (B, n)
    defence: np.ndarray  # (B, n)
    home_adv: np.ndarray  # (B,)
    rho: np.ndarray  # (B,)
    teams: tuple[str, ...]
    converged: int
    seed: int

    @property
    def draws(self) -> int:
        return len(self.home_adv)

    # Da dove viene la forza di una squadra che questo modello non ha visto:
    # nome -> codice della competizione da cui e' stata presa in prestito.
    # Vuoto per un bootstrap nato dal fit; si riempie con `con_prestiti`.
    prestiti: dict[str, str] = field(default_factory=dict)

    def knows(self, team: str) -> bool:
        return team in self.teams

    def con_prestiti(
        self, altri: dict[str, BootstrapResult], squadre: list[str]
    ) -> BootstrapResult:
        """Lo stesso modello, con in piu' le squadre prese da un altro campionato.

        IL PROBLEMA CHE RISOLVE. La Roma alla prima di Champions non ha storico
        in Champions, ma ne ha tre stagioni in Serie A, e quel modello sa
        benissimo quanto e' forte. Trattarla come «squadra media» (vedi
        `_params`) e' onesto ma butta via informazione che abbiamo.

        COME SI TRAPIANTA. I parametri di Dixon-Coles sono relativi al proprio
        campionato: l'attacco della Roma dice quanto segna rispetto alla media
        della Serie A, non in assoluto. Quindi non si copia il numero, si copia
        LA POSIZIONE: quante deviazioni standard sopra la media del suo
        campionato — draw per draw, cosi' l'incertezza del rifit viaggia con
        lei — e la si riporta sulla media e la dispersione di questo modello.
        Una squadra a una deviazione sopra la media in Serie A e' circa una
        quarta; a una deviazione sopra la media in Champions e' circa un'ottava.
        E' esattamente il ridimensionamento che serve.

        CON UN FRENO. `PRESTITO_SHRINK` accorcia la distanza dalla media: chi
        domina un campionato piccolo non domina la Champions, e il modello di
        Serie A non sa niente di come la Roma gioca contro il Bayern. Il freno
        e' un giudizio, non una misura, e sta in una costante per poterlo
        cambiare quando il backtest avra' abbastanza partite per dire quanto.

        Chi non trova posto in nessun altro modello resta fuori, e per lui vale
        ancora la squadra media col suo silenzio.
        """
        nuovi_att: list[np.ndarray] = []
        nuovi_dif: list[np.ndarray] = []
        nomi: list[str] = []
        origine: dict[str, str] = dict(self.prestiti)
        mia_att_m, mia_att_s = self.attack.mean(axis=1), self.attack.std(axis=1)
        mia_dif_m, mia_dif_s = self.defence.mean(axis=1), self.defence.std(axis=1)

        for team in squadre:
            if team in self.teams or team in nomi:
                continue
            for codice, altro in altri.items():
                if team not in altro.teams or altro.draws != self.draws:
                    continue
                i = altro.teams.index(team)
                z_att = (altro.attack[:, i] - altro.attack.mean(axis=1)) / _non_zero(
                    altro.attack.std(axis=1)
                )
                z_dif = (altro.defence[:, i] - altro.defence.mean(axis=1)) / _non_zero(
                    altro.defence.std(axis=1)
                )
                nuovi_att.append(mia_att_m + PRESTITO_SHRINK * z_att * mia_att_s)
                nuovi_dif.append(mia_dif_m + PRESTITO_SHRINK * z_dif * mia_dif_s)
                nomi.append(team)
                origine[team] = codice
                break

        if not nomi:
            return self
        return BootstrapResult(
            point=self.point,
            attack=np.column_stack([self.attack, *nuovi_att]),
            defence=np.column_stack([self.defence, *nuovi_dif]),
            home_adv=self.home_adv,
            rho=self.rho,
            teams=(*self.teams, *nomi),
            converged=self.converged,
            seed=self.seed,
            prestiti=origine,
        )

    def _params(self, team: str) -> tuple[np.ndarray, np.ndarray]:
        """Attacco e difesa di una squadra per ogni draw — o della squadra media.

        UNA SQUADRA CHE IL MODELLO NON HA MAI VISTO non e' una squadra senza
        forza: e' una squadra di cui non sappiamo la forza. La stima meno
        sbagliata e' «una squadra media di questa competizione», cioe' la media
        delle colonne, draw per draw — cosi' l'incertezza dei rifit resta
        dentro e il resto della pipeline non deve sapere niente.

        E' un prior, non una previsione: chi lo usa deve dirlo (vedi il
        silenzio `fuori_modello` in `pipeline.score_fixture`). Prima di questo
        metodo la partita veniva semplicemente scartata, e sei partite di
        Champions su sei diventavano due — la Roma non ha storico in Champions
        nella finestra del modello, ma la partita della Roma si gioca lo stesso.
        """
        if team in self.teams:
            i = self.teams.index(team)
            return self.attack[:, i], self.defence[:, i]
        return self.attack.mean(axis=1), self.defence.mean(axis=1)

    def rates(self, home: str, away: str) -> tuple[np.ndarray, np.ndarray]:
        """(lambda_casa, lambda_ospite) per tutti i draw, vettorizzato.

        Per una squadra fuori dal modello valgono i parametri medi: vedi
        `_params`.
        """
        att_h, dif_h = self._params(home)
        att_a, dif_a = self._params(away)
        return (
            np.exp(att_h + dif_a + self.home_adv),
            np.exp(att_a + dif_h),
        )

    def team_spread(self, team: str) -> float:
        """Quanto ballano i parametri di una squadra fra un draw e l'altro.

        E' la traduzione diretta di "poco storico affidabile": una squadra
        neopromossa, o che ha giocato poche partite dentro la finestra pesata,
        ha attacco e difesa mal determinati e i suoi 300 rifit si sparpagliano.
        Serve al messaggio di silenzio `sigma_max`, che deve dire **quale**
        delle due squadre rende instabile la stima: il frontend non ha modo di
        saperlo, e "queste squadre" e' esattamente l'informazione che manca.

        Si combinano attacco e difesa perche' entrambi entrano nei due lambda
        della partita: l'attacco della squadra nei suoi gol, la difesa in quelli
        dell'avversario.
        """
        i = self.teams.index(team)
        ddof = 1 if self.draws > 1 else 0
        return float(
            np.hypot(
                self.attack[:, i].std(ddof=ddof), self.defence[:, i].std(ddof=ddof)
            )
        )

    def least_reliable(self, *teams: str) -> str | None:
        """La squadra con i parametri piu' instabili fra quelle indicate."""
        known = [t for t in teams if t in self.teams]
        if not known:
            return None
        return max(known, key=self.team_spread)

    def to_dict(self) -> dict:
        return {
            "teams": list(self.teams),
            "draws": self.draws,
            "converged": self.converged,
            "seed": self.seed,
            "point": self.point.to_dict(),
            # 5 decimali: la sd bootstrap non ha piu' cifre significative di
            # cosi', e il file finisce in un repository pubblico.
            "attack": np.round(self.attack, 5).tolist(),
            "defence": np.round(self.defence, 5).tolist(),
            "home_adv": np.round(self.home_adv, 5).tolist(),
            "rho": np.round(self.rho, 5).tolist(),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> BootstrapResult:
        return cls(
            point=DCParams.from_dict(payload["point"]),
            attack=np.asarray(payload["attack"], dtype=float),
            defence=np.asarray(payload["defence"], dtype=float),
            home_adv=np.asarray(payload["home_adv"], dtype=float),
            rho=np.asarray(payload["rho"], dtype=float),
            teams=tuple(payload["teams"]),
            converged=int(payload["converged"]),
            seed=int(payload["seed"]),
        )


def run_bootstrap(
    data: MatchData,
    *,
    draws: int = DEFAULT_DRAWS,
    seed: int = 20260808,
    point: DCParams | None = None,
) -> BootstrapResult:
    """Rifitta il modello su `draws` ricampionamenti parametrici.

    Ogni rifit parte dal fit puntuale (**warm start**): i draw sono per
    definizione vicini al punto stimato, e questo e' l'intervento col
    rapporto guadagno/sforzo piu' alto fra quelli del brief 5.3.
    """
    if point is None:
        point, _ = fit(data)

    rng = np.random.default_rng(seed)
    lam = np.exp(
        point.attack[data.home_idx] + point.defence[data.away_idx] + point.home_adv
    )
    mu = np.exp(point.attack[data.away_idx] + point.defence[data.home_idx])

    n = data.n_teams
    attack = np.empty((draws, n))
    defence = np.empty((draws, n))
    home_adv = np.empty(draws)
    rho = np.empty(draws)
    converged = 0

    for b in range(draws):
        resampled = data.with_goals(
            rng.poisson(lam).astype(float), rng.poisson(mu).astype(float)
        )
        params, info = fit(resampled, start=point)
        attack[b] = params.attack
        defence[b] = params.defence
        home_adv[b] = params.home_adv
        rho[b] = params.rho
        converged += int(info["converged"])

    return BootstrapResult(
        point=point,
        attack=attack,
        defence=defence,
        home_adv=home_adv,
        rho=rho,
        teams=data.teams,
        converged=converged,
        seed=seed,
    )
