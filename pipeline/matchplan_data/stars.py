"""Vorbilder für „Könnte so gut werden wie …“: Topspieler der großen Ligen und ihr Werdegang Saison für Saison."""

from __future__ import annotations

import json
from datetime import date

LEAGUES = {47: "premier-league", 87: "laliga", 55: "serie", 53: "ligue-1"}
TOP_LEAGUE_IDS = {47, 87, 55, 53, 54}
PER_LEAGUE = 15
MIN_APPS_THEN = 10
MIN_APPS_NOW = 5


def stats_rating_url(nd: dict) -> str | None:
    for x in ((nd.get("props") or {}).get("pageProps") or {}).get("stats", {}).get("players") or []:
        if str(x.get("fetchAllUrl", "")).endswith("/rating.json"):
            return x["fetchAllUrl"]
    return None


def top_rated(text: str, n: int = PER_LEAGUE) -> list[dict]:
    """Bestbewertete Spieler einer Liga mit mindestens der Hälfte der Minuten des Spitzenwerts."""
    lists = json.loads(text).get("TopLists") or []
    rows = lists[0]["StatList"] if lists else []
    if not rows:
        return []
    max_min = max(r.get("MinutesPlayed") or 0 for r in rows)
    ok = [r for r in rows if (r.get("MinutesPlayed") or 0) >= 0.5 * max_min]
    ok.sort(key=lambda r: -(r.get("StatValue") or 0))
    return [{"id": r["ParticiantId"], "name": r["ParticipantName"], "team": r.get("TeamName"), "rating": r.get("StatValue")} for r in ok[:n]]


def age_in_season(birth: str | None, season: str | None) -> int | None:
    """Alter am 1. September des Saisonbeginns ('2021/2022' → 1.9.2021)."""
    try:
        y = int(str(season)[:4])
        b = date.fromisoformat(str(birth)[:10])
    except (TypeError, ValueError):
        return None
    ref = date(y, 9, 1)
    return ref.year - b.year - ((ref.month, ref.day) < (b.month, b.day))


def _league_row(season: dict, min_apps: int) -> dict | None:
    rows = [c for c in season.get("competitions") or [] if c.get("league_id") in TOP_LEAGUE_IDS and (c.get("apps") or 0) >= min_apps and c.get("rating")]
    return max(rows, key=lambda c: c["apps"]) if rows else None


def now_values(profile: dict, season_name: str) -> dict | None:
    s = next((x for x in profile.get("seasons") or [] if x.get("season") == season_name), None)
    row = _league_row(s, MIN_APPS_NOW) if s else None
    if not row:
        return None
    return {"rating": row["rating"], "ga": ((row.get("goals") or 0) + (row.get("assists") or 0)) / row["apps"], "apps": row["apps"], "league": row["league"]}


def then_values(profile: dict, age: int) -> dict | None:
    best = None
    for s in profile.get("seasons") or []:
        if age_in_season(profile.get("birth_date"), s.get("season")) != age:
            continue
        row = _league_row(s, MIN_APPS_THEN)
        if row and (best is None or row["apps"] > best["apps"]):
            best = {"season": s["season"], "league": row["league"], "apps": row["apps"], "rating": row["rating"],
                    "ga": ((row.get("goals") or 0) + (row.get("assists") or 0)) / row["apps"]}
    return best


def same_age(target: dict, models: list[dict], season_name: str, group_of, n: int = 3, min_score: float = 70.0) -> list[dict]:
    """Vergleich mit Topspielern in der Saison, in der sie so alt waren wie der Spieler heute."""
    age = age_in_season(target.get("birth_date"), season_name)
    if age is None or age > 24:
        return []
    mine = now_values(target, season_name)
    g = group_of(target)
    if not mine or not g or g == "Tor":
        return []
    out = []
    for m in models:
        if m.get("id") == target.get("id") or group_of(m) != g:
            continue
        then = then_values(m, age)
        if not then:
            continue
        r = min(max((mine["rating"] - 6) / max(then["rating"] - 6, 0.3), 0), 1.2)
        ga = min(mine["ga"] / then["ga"], 1.2) if then["ga"] > 0.05 else 1.0
        score = round((0.6 * r + 0.4 * ga) * 100, 1)
        if score >= min_score:
            out.append({"id": m["id"], "name": m.get("name"), "team": m.get("team"), "team_name": m.get("team_name"), "age": m.get("age"),
                        "score": min(score, 100.0), "then": {**then, "age": age, "ga": round(then["ga"], 2)},
                        "now": {"rating": mine["rating"], "ga": round(mine["ga"], 2), "league": mine["league"]},
                        "star": m.get("star_rating") or 0})
    out.sort(key=lambda x: (-x["star"], -x["score"]))
    return out[:n]
