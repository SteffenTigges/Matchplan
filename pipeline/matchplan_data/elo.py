"""Eigene Elo-Wertung (Methode wie ClubElo/World Football Elo) aus den Ergebnissen von 1. und 2. Bundesliga."""

from __future__ import annotations


from datetime import datetime

K = 20
HOME = 65
START = {"D1": 1500.0, "D2": 1350.0}


def expected(home: float, away: float) -> float:
    """Erwartete Punktausbeute des Heimteams (Sieg = 1, Remis = 0,5)."""
    return 1 / (1 + 10 ** (-(home + HOME - away) / 400))


def _date(s: str) -> datetime | None:
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt)
        except (TypeError, ValueError):
            continue
    return None


def game_rows(rows: list[dict]) -> list[tuple]:
    out = []
    for r in rows:
        d = _date(r.get("Date") or "")
        try:
            hg, ag = int(r["FTHG"]), int(r["FTAG"])
        except (KeyError, TypeError, ValueError):
            continue
        if d and r.get("HomeTeam") and r.get("AwayTeam"):
            out.append((d, r["HomeTeam"], r["AwayTeam"], hg, ag, r.get("Div") or "D1"))
    return sorted(out, key=lambda x: x[0])


def _margin(gd: int) -> float:
    gd = abs(gd)
    return 1.0 if gd <= 1 else 1.5 if gd == 2 else (11 + gd) / 8


def run_elo(games: list[tuple], base: dict[str, float] | None = None) -> dict[str, float]:
    r: dict[str, float] = dict(base or {})
    for _, h, a, hg, ag, div in games:
        r.setdefault(h, START.get(div, 1500.0))
        r.setdefault(a, START.get(div, 1500.0))
        we = expected(r[h], r[a])
        w = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
        delta = K * _margin(hg - ag) * (w - we)
        r[h] += delta
        r[a] -= delta
    return r


def win_draw_loss(home: float, away: float) -> tuple[float, float, float]:
    """Grobe Aufteilung der Elo-Erwartung in Sieg/Remis/Niederlage (Remisanteil sinkt mit dem Abstand)."""
    we = expected(home, away)
    draw = max(0.12, 0.28 - 0.5 * abs(we - 0.5) * 0.6)
    win = max(we - draw / 2, 0.0)
    loss = max(1 - win - draw, 0.0)
    s = win + draw + loss
    return win / s, draw / s, loss / s


def rank(ratings: dict[str, float]) -> dict[str, int]:
    order = sorted(ratings, key=lambda k: -ratings[k])
    return {k: i + 1 for i, k in enumerate(order)}


