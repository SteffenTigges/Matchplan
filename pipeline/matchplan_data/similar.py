"""Ähnliche Spieler (Spielstil) und „Könnte so gut werden wie …“ (Wirkung) aus den FotMob-Profilen."""

from __future__ import annotations

import math

MIN_SHARED = 8
YOUNG_MAX, TOP_AGE = 24, (25, 30)
YOUNG_MIN_MIN = 450
TOP_MIN_SHARE = 0.6  # Topspieler: mindestens 60 % der bisher möglichen Minuten
TOP_SHARE = 0.10
GROUP = {**{p: "Abwehr" for p in ("CB", "LB", "RB", "LWB", "RWB")},
         **{p: "Mittelfeld" for p in ("DM", "CM", "AM", "LM", "RM", "CDM", "CAM")},
         **{p: "Angriff" for p in ("ST", "CF", "LW", "RW", "SS")}, "GK": "Tor"}
IMPACT = {"Angriff": ["expected_goals", "expected_assists", "chances_created", "touches_opp_box"],
          "Mittelfeld": ["expected_goals", "expected_assists", "chances_created", "touches_opp_box"],
          "Abwehr": ["interceptions", "recoveries", "duel_won", "successful_passes"]}


def group_of(p: dict) -> str | None:
    main = next((x for x in p.get("positions") or [] if x.get("main")), None)
    return GROUP.get((main or {}).get("short") or "")


def _pcts(p: dict) -> dict[str, float]:
    return {s["key"]: s["pct"] for s in p.get("stats") or [] if s.get("pct") is not None}


def _per90(p: dict) -> dict[str, float]:
    return {s["key"]: s["per90"] for s in p.get("stats") or [] if s.get("per90") is not None}


def _cos(a: dict[str, float], b: dict[str, float]) -> float | None:
    keys = [k for k in a if k in b]
    if len(keys) < MIN_SHARED:
        return None
    x = [a[k] - 50 for k in keys]
    y = [b[k] - 50 for k in keys]
    nx, ny = math.sqrt(sum(v * v for v in x)), math.sqrt(sum(v * v for v in y))
    if not nx or not ny:
        return None
    return sum(i * j for i, j in zip(x, y)) / (nx * ny)


def _brief(p: dict) -> dict:
    return {"id": p["id"], "name": p.get("name"), "team": p.get("team"), "team_name": p.get("team_name"), "age": p.get("age")}


def style_similar(target: dict, pool: list[dict], n: int = 5) -> list[dict]:
    g = group_of(target)
    if not g:
        return []
    tp = _pcts(target)
    out = []
    for p in pool:
        if p["id"] == target["id"] or group_of(p) != g:
            continue
        c = _cos(tp, _pcts(p))
        if c is not None:
            out.append({**_brief(p), "score": round(max(c, -1.0) * 100, 1)})
    return sorted(out, key=lambda x: -x["score"])[:n]


def could_be(target: dict, pool: list[dict], rows: dict, n: int = 3, min_score: float = 60.0, top_min: float | None = None) -> list[dict]:
    g = group_of(target)
    if g not in IMPACT or (target.get("age") or 99) > YOUNG_MAX or (rows.get(target["id"]) or {}).get("minutes", 0) < YOUNG_MIN_MIN:
        return []
    if top_min is None:
        top_min = TOP_MIN_SHARE * max((r.get("minutes") or 0 for r in rows.values()), default=0)
    tops = [p for p in pool if p["id"] != target["id"] and group_of(p) == g and TOP_AGE[0] <= (p.get("age") or 0) <= TOP_AGE[1]
            and (rows.get(p["id"]) or {}).get("minutes", 0) >= top_min and (rows.get(p["id"]) or {}).get("rating")]
    tops.sort(key=lambda p: -rows[p["id"]]["rating"])
    tops = tops[:max(1, math.ceil(len(tops) * TOP_SHARE))] if len(tops) > 10 else tops
    mine = _per90(target)
    out = []
    for p in tops:
        theirs = _per90(p)
        ratios = [min(mine[k] / theirs[k], 1.2) for k in IMPACT[g] if k in mine and theirs.get(k)]
        if len(ratios) < 3:
            continue
        score = sum(ratios) / len(ratios) * 100
        if score >= min_score:
            out.append({**_brief(p), "rating": rows[p["id"]]["rating"], "score": round(min(score, 100.0), 1), "keys": len(ratios)})
    # Die größten Vorbilder zuerst (beste Note), solange die Wirkung schon nah dran ist.
    return sorted(out, key=lambda x: (-x["rating"], -x["score"]))[:n]


def build_similar(profiles: list[dict], rows: dict) -> dict[int, dict]:
    top_min = TOP_MIN_SHARE * max((r.get("minutes") or 0 for r in rows.values()), default=0)
    return {p["id"]: {"style": style_similar(p, profiles), "could_be": could_be(p, profiles, rows, top_min=top_min)} for p in profiles if p.get("id")}
