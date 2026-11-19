"""Ergebnisprognose: Teamstärken aus xG, Poisson mit Dixon-Coles-Korrektur, Tipp, Märkte, Kalibrierung."""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_GOALS = 10
SHRINK = 4  # Spiele, mit denen der Ligaschnitt am Saisonanfang gewichtet wird
RECENT = 5
RECENT_WEIGHT = 0.3
DEFAULT_CAL = {"home": 1.70, "away": 1.35, "rho": -0.05}


@dataclass(frozen=True)
class TeamGame:
    matchday: int
    team: str
    opp: str
    home: bool
    xg_for: float
    xg_against: float
    goals_for: int
    goals_against: int


@dataclass(frozen=True)
class Means:
    home: float
    away: float


def _pois(lam: float, k: int) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def _tau(i: int, j: int, lh: float, la: float, rho: float) -> float:
    if i == 0 and j == 0:
        return 1 - lh * la * rho
    if i == 0 and j == 1:
        return 1 + lh * rho
    if i == 1 and j == 0:
        return 1 + la * rho
    if i == 1 and j == 1:
        return 1 - rho
    return 1.0


def score_matrix(lh: float, la: float, rho: float, n: int = MAX_GOALS) -> list[list[float]]:
    """m[i][j] = P(Heim i Tore, Gast j Tore), 0..n, auf Summe 1 normiert."""
    m = [[max(_tau(i, j, lh, la, rho), 0.0) * _pois(lh, i) * _pois(la, j) for j in range(n + 1)] for i in range(n + 1)]
    s = sum(sum(r) for r in m)
    return [[v / s for v in r] for r in m]


def outcome_probs(m: list[list[float]]) -> tuple[float, float, float]:
    h = sum(v for i, r in enumerate(m) for j, v in enumerate(r) if i > j)
    d = sum(m[i][i] for i in range(len(m)))
    return h, d, 1 - h - d


def tip(m: list[list[float]]) -> tuple[int, int]:
    """Häufigstes Ergebnis innerhalb des wahrscheinlichsten Ausgangs."""
    h, d, a = outcome_probs(m)
    best = max((h, 0), (d, 1), (a, 2))[1]
    side = (lambda i, j: i > j, lambda i, j: i == j, lambda i, j: i < j)[best]
    cells = [(v, i, j) for i, r in enumerate(m) for j, v in enumerate(r) if side(i, j)]
    _, i, j = max(cells)
    return i, j


def markets(m: list[list[float]]) -> dict[str, float]:
    cells = [(i, j, v) for i, r in enumerate(m) for j, v in enumerate(r)]
    return {
        "over25": sum(v for i, j, v in cells if i + j > 2),
        "btts": sum(v for i, j, v in cells if i > 0 and j > 0),
        "home_clean_sheet": sum(v for i, j, v in cells if j == 0),
        "away_clean_sheet": sum(v for i, j, v in cells if i == 0),
    }


def _blend(values: list[float]) -> float:
    season = sum(values) / len(values)
    recent = values[-RECENT:]
    return (1 - RECENT_WEIGHT) * season + RECENT_WEIGHT * sum(recent) / len(recent)


def strengths(games: list[TeamGame], teams: list[str]) -> dict[str, dict]:
    """Angriff/Abwehr relativ zum Ligaschnitt (1.0 = Schnitt; Abwehr < 1 = besser), zum Schnitt hin gestaucht."""
    league = [x.xg_for for x in games]
    mean = sum(league) / len(league) if league else 1.0
    out: dict[str, dict] = {}
    for t in teams:
        own = sorted((x for x in games if x.team == t), key=lambda x: x.matchday)
        n = len(own)
        if not n or mean <= 0:
            out[t] = {"att": 1.0, "def": 1.0, "n": n, "xgf": mean, "xga": mean}
            continue
        xgf, xga = _blend([x.xg_for for x in own]), _blend([x.xg_against for x in own])
        w = n / (n + SHRINK)
        out[t] = {"att": 1 + (xgf / mean - 1) * w, "def": 1 + (xga / mean - 1) * w, "n": n, "xgf": xgf, "xga": xga}
    return out


def expected_goals(home: str, away: str, st: dict[str, dict], means: Means) -> tuple[float, float]:
    return means.home * st[home]["att"] * st[away]["def"], means.away * st[away]["att"] * st[home]["def"]


def season_means(games: list[TeamGame], cal: dict, matchdays_played: int) -> Means:
    """Tore pro Spiel heim/auswärts; bis zum 10. Spieltag mit den Vorsaisons gemischt."""
    home = [x.goals_for for x in games if x.home]
    away = [x.goals_for for x in games if not x.home]
    w = min(matchdays_played / 10, 1.0) if home and away else 0.0
    mh = sum(home) / len(home) if home else cal["home"]
    ma = sum(away) / len(away) if away else cal["away"]
    return Means(w * mh + (1 - w) * cal["home"], w * ma + (1 - w) * cal["away"])


def fit_calibration(results: list[tuple[int, int]]) -> dict[str, float]:
    """Heim-/Auswärtstorschnitt und rho (Dixon-Coles, Gitter −0.20…0.05) per Maximum-Likelihood."""
    if not results:
        return dict(DEFAULT_CAL)
    lh = sum(h for h, _ in results) / len(results)
    la = sum(a for _, a in results) / len(results)
    counts: dict[tuple[int, int], int] = {}
    for h, a in results:
        key = (h, a) if h <= 1 and a <= 1 else (9, 9)
        counts[key] = counts.get(key, 0) + 1

    def ll(rho: float) -> float:
        # Nur die vier Zellen 0/1 hängen von rho ab; die Normierung über die volle Matrix.
        m = score_matrix(lh, la, rho)
        return sum(c * math.log(m[i][j]) for (i, j), c in counts.items() if (i, j) != (9, 9)) + counts.get((9, 9), 0) * math.log(
            1 - sum(m[i][j] for i in (0, 1) for j in (0, 1)))

    rho = max((r / 100 for r in range(-20, 6)), key=ll)
    return {"home": round(lh, 4), "away": round(la, 4), "rho": rho}
