"""Torschützen-Wahrscheinlichkeiten und Ausfall-Faktoren (Ligainsider-Aufstellung ↔ FotMob-Saisonwerte)."""

from __future__ import annotations

import math
import re
import unicodedata

MIN_MINUTES = 270
NON_OWN_GOALS = 0.97  # Anteil der Tore, die nicht als Eigentor fallen
START_MIN, SPLIT_START, SPLIT_ALT = 80, 45, 35
PRIOR = {"Sturm": 0.22, "Mittelfeld": 0.08, "Abwehr": 0.03, "Tor": 0.0}
POS_GROUP = {**{p: "Sturm" for p in ("ST", "CF", "LW", "RW", "SS")}, **{p: "Mittelfeld" for p in ("AM", "CM", "DM", "LM", "RM", "CAM", "CDM")},
             **{p: "Abwehr" for p in ("CB", "LB", "RB", "LWB", "RWB")}, "GK": "Tor", "TW": "Tor"}
ATT_PER_SHARE, DEF_PER_REGULAR, CAP = 0.5, 0.06, 0.25


def _norm(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return [t for t in re.split(r"[^a-z0-9]+", s) if t and not t.isdigit()]


def _li_tokens(p: dict) -> list[str]:
    pid = p.get("id") or ""
    return _norm(pid.split("_")[0]) if pid else _norm(p.get("name", ""))


def match_player(li: dict, candidates: list[dict]) -> dict | None:
    """Ligainsider-Spieler (Slug 'vorname-nachname_123' oder nur Name) einem FotMob-Spieler desselben Teams zuordnen."""
    want = set(_li_tokens(li))
    if not want:
        return None
    exact = [c for c in candidates if set(_norm(c["name"])) == want]
    if len(exact) == 1:
        return exact[0]
    loose = [c for c in candidates if want <= set(_norm(c["name"])) or set(_norm(c["name"])) <= want]
    if len(loose) == 1:
        return loose[0]
    short = _norm(li.get("name", ""))
    if short:
        last = [c for c in candidates if _norm(c["name"])[-len(short):] == short]
        if len(last) == 1:
            return last[0]
    return None


def player_season(files: list[dict], season: str) -> dict[str, list[dict]]:
    acc: dict[int, dict] = {}
    team_of: dict[int, str] = {}
    for m in files:
        if m.get("season") != season:
            continue
        for p in m.get("players") or []:
            if not p.get("id") or not p.get("minutes"):
                continue
            e = acc.setdefault(p["id"], {"id": p["id"], "name": p.get("name"), "minutes": 0, "xg": 0.0, "keeper": bool(p.get("keeper"))})
            e["minutes"] += p["minutes"]
            e["xg"] = round(e["xg"] + (p.get("xg") or 0.0), 4)
            team_of[p["id"]] = p.get("team")
    out: dict[str, list[dict]] = {}
    for pid, e in acc.items():
        out.setdefault(team_of[pid], []).append(e)
    return out


def _row_group(row: int, rows: int) -> str:
    """Positionsgruppe aus der Reihe der Ligainsider-Aufstellung (0 = Torwart, 1 = Abwehr, letzte = Sturm)."""
    return "Tor" if row == 0 else "Abwehr" if row == 1 else "Sturm" if row == rows - 1 else "Mittelfeld"


def _share(fm: dict | None, team_xg_pg: float, pos: dict, row: int, rows: int) -> float:
    if fm and fm.get("keeper") or row == 0:
        return 0.0
    if fm and fm["minutes"] >= MIN_MINUTES and team_xg_pg > 0:
        return (fm["xg"] / fm["minutes"] * 90) / team_xg_pg
    group = POS_GROUP.get(pos.get(fm["id"])) if fm and pos.get(fm["id"]) else None
    return PRIOR[group or _row_group(row, rows)]


def scorers(lineup: dict, season_players: list[dict], team_xg_pg: float, lam: float, pos: dict) -> list[dict]:
    """Wahrscheinlichkeit für mindestens ein Tor je Spieler der voraussichtlichen Aufstellung."""
    entries = []
    rows = lineup.get("rows") or []
    for r, row in enumerate(rows):
        for s in row:
            alts = s.get("alternatives") or []
            people = [(s["player"], START_MIN)] if not alts else [(s["player"], SPLIT_START)] + [(a, SPLIT_ALT / len(alts)) for a in alts]
            for p, minutes in people:
                fm = match_player(p, season_players)
                lp = lam * NON_OWN_GOALS * _share(fm, team_xg_pg, pos, r, len(rows)) * minutes / 90
                entries.append({"name": p.get("name"), "li_id": p.get("id"), "fm_id": fm["id"] if fm else None,
                                "photo": p.get("photo"), "minutes": minutes, "lam": lp})
    total = sum(e["lam"] for e in entries)
    if total > NON_OWN_GOALS * lam > 0:
        k = NON_OWN_GOALS * lam / total
        for e in entries:
            e["lam"] *= k
    for e in entries:
        e["p"] = 1 - math.exp(-e["lam"])
    return sorted(entries, key=lambda e: -e["p"])


def absence_factors(missing: list[dict], season_players: list[dict]) -> tuple[float, float, list[dict]]:
    """(Faktor eigene Tore, Faktor Gegentore, Zuordnung) aus der Ausfallliste – Näherung."""
    team_xg = sum(p["xg"] for p in season_players) or 1.0
    full = max((p["minutes"] for p in season_players), default=0) or 1
    xg_share = regulars = 0.0
    info = []
    for m in missing:
        fm = match_player({"name": m.get("name", "")}, season_players)
        info.append({"name": m.get("name"), "fm_id": fm["id"] if fm else None,
                     "xg_share": round(fm["xg"] / team_xg, 3) if fm else 0.0,
                     "minutes_share": round(fm["minutes"] / full, 3) if fm else 0.0})
        if fm:
            xg_share += fm["xg"] / team_xg
            regulars += fm["minutes"] / full
    att = max(1 - ATT_PER_SHARE * xg_share, 1 - CAP)
    dfn = min(1 + DEF_PER_REGULAR * regulars, 1 + CAP)
    return round(att, 4), round(dfn, 4), info
