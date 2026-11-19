"""Buchmacherquoten und Vorsaison-Ergebnisse von football-data.co.uk (CSV)."""

from __future__ import annotations

import csv
import io

from .teams import FD_NAMES

FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"


def season_url(start_year: int) -> str:
    return f"https://www.football-data.co.uk/mmz4281/{start_year % 100:02d}{(start_year + 1) % 100:02d}/D1.csv"


def parse_csv(text: str) -> list[dict]:
    rows = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    return [r for r in rows if (r.get("Div") or "").strip()]


def _f(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x > 1.0 else None


def implied(h: float, d: float, a: float) -> tuple[float, float, float]:
    inv = (1 / h, 1 / d, 1 / a)
    s = sum(inv)
    return inv[0] / s, inv[1] / s, inv[2] / s


def _pick(r: dict, sets: list[tuple[str, tuple[str, str, str]]]) -> dict | None:
    for source, cols in sets:
        vals = [_f(r.get(c)) for c in cols]
        if all(vals):
            h, d, a = implied(*vals)  # type: ignore[arg-type]
            return {"home": h, "draw": d, "away": a, "source": source}
    return None


def _by_pair(rows: list[dict], sets) -> tuple[dict, list[str]]:
    out: dict[tuple[str, str], dict] = {}
    unknown: list[str] = []
    for r in rows:
        if r.get("Div") != "D1":
            continue
        h, a = FD_NAMES.get(r.get("HomeTeam", "")), FD_NAMES.get(r.get("AwayTeam", ""))
        for name, key in ((r.get("HomeTeam", ""), h), (r.get("AwayTeam", ""), a)):
            if key is None and name not in unknown:
                unknown.append(name)
        if h and a:
            p = _pick(r, sets)
            if p:
                out[(h, a)] = p
    return out, unknown


OPENING = [("Schnitt der Buchmacher", ("AvgH", "AvgD", "AvgA")), ("Bet365", ("B365H", "B365D", "B365A"))]
CLOSING = [("Schlussquote (Schnitt)", ("AvgCH", "AvgCD", "AvgCA")), ("Bet365 Schlussquote", ("B365CH", "B365CD", "B365CA"))] + OPENING


def odds_by_pair(rows: list[dict]) -> tuple[dict, list[str]]:
    """Aktuelle Quoten je (Heim, Gast) als implizite Wahrscheinlichkeiten; unbekannte Vereinsnamen separat."""
    return _by_pair(rows, OPENING)


def closing_odds(rows: list[dict]) -> tuple[dict, list[str]]:
    return _by_pair(rows, CLOSING)


def results(rows: list[dict]) -> list[tuple[int, int]]:
    out = []
    for r in rows:
        try:
            out.append((int(r["FTHG"]), int(r["FTAG"])))
        except (KeyError, TypeError, ValueError):
            continue
    return out
