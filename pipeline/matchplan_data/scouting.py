"""Gegner-Bericht: regelbasierte Auswertung je Team; jede Aussage trägt die Zahlen, auf denen sie beruht."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Callable

SITUATIONS = {"RegularPlay": "Spielaufbau", "FastBreak": "Konter", "SetPiece": "Standard", "FromCorner": "Standard",
              "FreeKick": "Standard", "ThrowInSetPiece": "Standard", "IndividualPlay": "Spielaufbau", "Penalty": "Elfmeter"}
GROUPS = ["Spielaufbau", "Konter", "Standard", "Elfmeter"]
BANDS = ["1–15", "16–30", "31–45", "46–60", "61–75", "76–90"]
KEY_MIN = 450
LINE = {**{p: "Abwehr" for p in ("CB", "LB", "RB", "LWB", "RWB")},
        **{p: "Mittelfeld" for p in ("DM", "CM", "AM", "LM", "RM", "CDM", "CAM")},
        **{p: "Angriff" for p in ("ST", "CF", "LW", "RW", "SS")}}

RESULT_METRICS = {"points", "goal_diff"}  # Ergebnis, keine Spielweise
Pair = tuple[dict, dict]  # (OpenLigaDB-Spiel, FotMob-Datei)


def _side(m: dict, team: str) -> str:
    return "home" if m["home"] == team else "away"


def situation_split(shot_lists: list[list[dict]], team: str, against: bool = False) -> dict | None:
    acc = {g: {"goals": 0, "xg": 0.0, "shots": 0} for g in GROUPS}
    seen = False
    for shots in shot_lists:
        for s in shots or []:
            if s.get("own_goal") or (s.get("team") == team) == against:
                continue
            seen = True
            g = SITUATIONS.get(s.get("situation") or "", "Spielaufbau")
            acc[g]["shots"] += 1
            acc[g]["xg"] += s.get("xg") or 0.0
            acc[g]["goals"] += s.get("result") == "goal"
    if not seen:
        return None
    goals = sum(v["goals"] for v in acc.values())
    xg = sum(v["xg"] for v in acc.values()) or 1.0
    for v in acc.values():
        v["xg"] = round(v["xg"], 2)
        v["share"] = round(v["goals"] / goals, 3) if goals else round(v["xg"] / xg, 3)
    return acc


def minute_bands(minutes: list[int | None]) -> list[int]:
    out = [0] * 6
    for mi in minutes:
        if mi is None:
            continue
        idx = 5 if mi > 75 else 4 if mi > 60 else 3 if mi > 45 else min((max(mi, 1) - 1) // 15, 2)
        out[idx] += 1
    return out


def formation_usage(pairs: list[Pair], team: str) -> list[dict]:
    c = Counter()
    for m, fm in pairs:
        lu = (fm.get("lineups") or {}).get(_side(m, team)) if fm else None
        if lu and lu.get("formation"):
            c[lu["formation"]] += 1
    return [{"formation": f, "games": n} for f, n in sorted(c.items(), key=lambda x: (-x[1], x[0]))]


def _points(gf: int, ga: int) -> int:
    return 3 if gf > ga else 1 if gf == ga else 0


def reaction(games: list[dict], team: str) -> dict:
    r = {"ht_lead": {"games": 0, "points": 0}, "ht_draw": {"games": 0, "points": 0}, "ht_trail": {"games": 0, "points": 0},
         "points_from_behind": 0, "points_dropped": 0, "late_for": 0, "late_against": 0, "goals_for": 0, "goals_against": 0,
         "for_minutes": [], "against_minutes": []}
    for m in games:
        if not m.get("finished") or not m.get("score"):
            continue
        home = m["home"] == team
        gf, ga = (m["score"][0], m["score"][1]) if home else (m["score"][1], m["score"][0])
        pts = _points(gf, ga)
        if m.get("halftime"):
            hf, ha = (m["halftime"][0], m["halftime"][1]) if home else (m["halftime"][1], m["halftime"][0])
            key = "ht_lead" if hf > ha else "ht_trail" if hf < ha else "ht_draw"
            r[key]["games"] += 1
            r[key]["points"] += pts
        f = a = 0
        trailed = led = False
        for g in sorted(m.get("goals") or [], key=lambda g: g.get("minute") or 0):
            mine = g["team"] == team
            f, a = (f + 1, a) if mine else (f, a + 1)
            (r["for_minutes"] if mine else r["against_minutes"]).append(g.get("minute"))
            if (g.get("minute") or 0) > 75:
                r["late_for" if mine else "late_against"] += 1
            trailed |= f < a
            led |= f > a
        if trailed:
            r["points_from_behind"] += pts
        if led:
            r["points_dropped"] += 3 - pts
        r["goals_for"] += gf
        r["goals_against"] += ga
    r["for_bands"] = minute_bands(r.pop("for_minutes"))
    r["against_bands"] = minute_bands(r.pop("against_minutes"))
    return r


def _player_totals(pairs: list[Pair], team: str) -> dict[int, dict]:
    acc: dict[int, dict] = {}
    for _, fm in pairs:
        for p in (fm or {}).get("players") or []:
            if p.get("team") != team or not p.get("id") or not p.get("minutes"):
                continue
            e = acc.setdefault(p["id"], {"id": p["id"], "name": p.get("name"), "minutes": 0, "xg": 0.0, "xa": 0.0,
                                         "goals": 0, "assists": 0, "ratings": []})
            e["minutes"] += p["minutes"]
            for k in ("xg", "xa"):
                e[k] += p.get(k) or 0.0
            for k in ("goals", "assists"):
                e[k] += p.get(k) or 0
            if p.get("rating") is not None:
                e["ratings"].append(p["rating"])
    return acc


def _why(profile: dict | None) -> list[str]:
    stats = [s for s in (profile or {}).get("stats") or [] if s.get("pct") is not None and s["pct"] >= 80]
    return [f"{s['title']} ({round(s['pct'])}. Perzentil)" for s in sorted(stats, key=lambda s: -s["pct"])[:2]]


def key_players(pairs: list[Pair], team: str, index: dict, profile: Callable[[int], dict | None], n: int = 5) -> list[dict]:
    out = []
    for e in _player_totals(pairs, team).values():
        if e["minutes"] < KEY_MIN:
            continue
        rating = round(sum(e["ratings"]) / len(e["ratings"]), 2) if e["ratings"] else None
        out.append({"id": e["id"], "name": e["name"], "pos": (index.get(e["id"]) or {}).get("pos"), "minutes": e["minutes"],
                    "goals": e["goals"], "assists": e["assists"], "rating": rating,
                    "xg90": round(e["xg"] / e["minutes"] * 90, 2), "xa90": round(e["xa"] / e["minutes"] * 90, 2),
                    "why": _why(profile(e["id"]))})
    out.sort(key=lambda p: (-(p["xg90"] + p["xa90"]), -(p["rating"] or 0)))
    return out[:n]


def best_per_line(pairs: list[Pair], team: str, index: dict) -> dict[str, dict]:
    best: dict[str, dict] = {}
    for e in _player_totals(pairs, team).values():
        line = LINE.get((index.get(e["id"]) or {}).get("pos") or "")
        if not line or e["minutes"] < KEY_MIN or not e["ratings"]:
            continue
        rating = round(sum(e["ratings"]) / len(e["ratings"]), 2)
        if line not in best or rating > best[line]["rating"]:
            best[line] = {"id": e["id"], "name": e["name"], "rating": rating, "minutes": e["minutes"]}
    return best


def last_load(pairs: list[Pair], team: str, n: int = 3) -> list[dict]:
    recent = sorted(pairs, key=lambda p: (p[1] or {}).get("matchday") or 0)[-n:]
    tot = _player_totals(recent, team)
    rows = [{"id": e["id"], "name": e["name"], "minutes": e["minutes"], "full": e["minutes"] >= 250} for e in tot.values()]
    return sorted(rows, key=lambda r: -r["minutes"])[:14]


def _metric(ts: dict, team: str, key: str) -> tuple[dict | None, dict | None]:
    meta = next((m for m in ts.get("metrics", []) if m["key"] == key), None)
    e = (ts.get("teams", {}).get(team) or {}).get(key)
    if not meta or not isinstance(e, dict) or e.get("value") is None or e.get("rank") is None:
        return meta, None
    return meta, e


def _ev(ts: dict, team: str, key: str) -> dict | None:
    meta, e = _metric(ts, team, key)
    return {"key": key, "label": meta["label"], "value": e["value"], "fmt": meta["fmt"], "rank": e["rank"]} if e else None


def strengths_weaknesses(ts: dict, team: str, n: int = 4) -> tuple[list[dict], list[dict]]:
    evs = [x for x in (_ev(ts, team, m["key"]) for m in ts.get("metrics", []) if m["key"] not in RESULT_METRICS) if x]
    strong = sorted([x for x in evs if x["rank"] <= 3], key=lambda x: x["rank"])[:n]
    weak = sorted([x for x in evs if x["rank"] >= 16], key=lambda x: -x["rank"])[:n]
    return strong, weak


def matchplan_rules(ts: dict, team: str, react: dict, opp_zones: dict | None, scoring: dict | None) -> list[dict]:
    """Ideen gegen dieses Team, je mit Belegen. Stärkste zuerst, höchstens 5."""
    out: list[tuple[float, dict]] = []

    def rank_rule(key: str, cond: Callable[[int], bool], rkey: str, text: str, weight: Callable[[int], float]):
        ev = _ev(ts, team, key)
        if ev and cond(ev["rank"]):
            out.append((weight(ev["rank"]), {"key": rkey, "text": text, "evidence": [ev]}))

    rank_rule("xga_setplay_pg", lambda r: r >= 13, "setpieces", "Standards suchen: Bei ruhenden Bällen lassen sie viel zu.", lambda r: r)
    rank_rule("ppda", lambda r: r <= 4, "press", "Sie pressen früh: lange Bälle hinter die erste Pressinglinie, schnelle Ablagen.", lambda r: 19 - r)
    rank_rule("aerial_rate", lambda r: r >= 13, "aerial", "Schwach in der Luft: Flanken und hohe Bälle in den Strafraum.", lambda r: r)
    rank_rule("big_chances_against_pg", lambda r: r >= 13, "depth", "Lassen viele Großchancen zu: Läufe in die Tiefe suchen.", lambda r: r)
    rank_rule("possession", lambda r: r <= 3, "possession", "Wollen den Ball: Passwege ins Zentrum zustellen, Ballgewinne für Umschaltmomente nutzen.", lambda r: 15 - r)

    ga = react.get("goals_against") or 0
    late = react.get("late_against") or 0
    if ga >= 4 and late / ga >= 0.3:
        out.append((14 + 10 * late / ga, {"key": "late", "text": "Kassieren spät: in der Schlussphase Druck machen, Wechsel offensiv denken.",
                                          "evidence": [{"label": "Gegentore ab der 76. Minute", "value": late, "fmt": "int"},
                                                       {"label": "Anteil an allen Gegentoren", "value": late / ga, "fmt": "pct"}]}))
    if opp_zones:
        side, share = max(((k, v) for k, v in opp_zones.items() if k != "center"), key=lambda x: x[1])
        if share >= 40:
            human = "links" if side == "left" else "rechts"
            out.append((share / 3, {"key": "side", "text": f"Gegner kommen am häufigsten über {human} durch: dort angreifen (ihre {'rechte' if side == 'left' else 'linke'} Abwehrseite).",
                                    "evidence": [{"label": f"Angriffe der Gegner über {human}", "value": share / 100, "fmt": "pct"}]}))
    if scoring and scoring.get("Konter", {}).get("share", 0) >= 0.25:
        k = scoring["Konter"]
        out.append((15, {"key": "counter", "text": "Gefährlich im Konter: Restverteidigung sichern, Ballverluste im Zentrum vermeiden.",
                         "evidence": [{"label": "Anteil Tore nach Kontern", "value": k["share"], "fmt": "pct"}, {"label": "Tore nach Kontern", "value": k["goals"], "fmt": "int"}]}))
    out.sort(key=lambda x: -x[0])
    return [r for _, r in out[:5]]


def style_tags(ts: dict, team: str, scoring: dict | None) -> list[dict]:
    tags = []

    def tag(key: str, cond: Callable[[int], bool], text: str):
        ev = _ev(ts, team, key)
        if ev and cond(ev["rank"]):
            tags.append({"text": text, "evidence": [ev]})

    tag("possession", lambda r: r <= 5, "Ballbesitzteam")
    tag("possession", lambda r: r >= 14, "Überlässt dem Gegner den Ball")
    tag("ppda", lambda r: r <= 5, "Hohes Pressing")
    tag("ppda", lambda r: r >= 14, "Abwartend gegen den Ball")
    tag("field_tilt", lambda r: r <= 5, "Drückt den Gegner in die eigene Hälfte")
    tag("opp_half_share", lambda r: r <= 5, "Spielt viel in der gegnerischen Hälfte")
    if scoring:
        if scoring["Konter"]["share"] >= 0.2:
            tags.append({"text": "Gefährlich im Konter", "evidence": [{"label": "Anteil Tore nach Kontern", "value": scoring["Konter"]["share"], "fmt": "pct"}]})
        if scoring["Standard"]["share"] >= 0.35:
            tags.append({"text": "Standardstark", "evidence": [{"label": "Anteil Tore nach Standards", "value": scoring["Standard"]["share"], "fmt": "pct"}]})
    return tags


def _avg_zones(pairs: list[Pair], team: str, own: bool) -> dict | None:
    acc = defaultdict(float)
    n = 0
    for m, fm in pairs:
        z = (fm or {}).get("zones")
        if not z:
            continue
        side = _side(m, team) if own else ("away" if _side(m, team) == "home" else "home")
        if z.get(side):
            n += 1
            for k in ("left", "center", "right"):
                acc[k] += z[side].get(k) or 0
    return {k: round(v / n, 1) for k, v in acc.items()} if n else None


def _avg_stat(pairs: list[Pair], team: str, key: str, opp: bool = False) -> float | None:
    vals = []
    for m, fm in pairs:
        v = ((fm or {}).get("stats") or {}).get(key)
        if not v:
            continue
        i = 0 if (_side(m, team) == "home") != opp else 1
        x = v[i]
        x = x.get("n") if isinstance(x, dict) else x
        if isinstance(x, (int, float)):
            vals.append(float(x))
    return round(sum(vals) / len(vals), 2) if vals else None


def build_report(team: str, games: list[dict], fm_by_id: dict, ts: dict, index_rows: list[dict],
                 profile: Callable[[int], dict | None], lineup: dict | None, next_info: dict | None) -> dict:
    played = [m for m in games if m.get("finished") and m.get("score") and team in (m["home"], m["away"])]
    pairs: list[Pair] = [(m, fm_by_id[m["id"]]) for m in played if m["id"] in fm_by_id]
    index = {r["id"]: r for r in index_rows}
    shots = [fm.get("shots") or [] for _, fm in pairs]
    scoring = situation_split(shots, team)
    conceding = situation_split(shots, team, against=True)
    react = reaction(played, team)
    opp_zones = _avg_zones(pairs, team, own=False)
    strong, weak = strengths_weaknesses(ts, team)
    rules = matchplan_rules(ts, team, react, opp_zones, scoring)
    box = [s for sh in shots for s in sh if s.get("team") == team and not s.get("own_goal")]
    return {
        "team": team, "matches": len(played), "fotmob_matches": len(pairs),
        "idea": {"formations": formation_usage(pairs, team), "tags": style_tags(ts, team, scoring)},
        "next": next_info,
        "strengths": strong, "weaknesses": weak, "matchplan": rules,
        "findings": (rules + [{"key": "strength", "text": f"Stark: {s['label']} (Platz {s['rank']})", "evidence": [s]} for s in strong])[:3],
        "buildup": {
            "metrics": [x for x in (_ev(ts, team, k) for k in ("possession", "pass_accuracy", "opp_half_share", "long_ball_accuracy", "cross_accuracy", "field_tilt")) if x],
            "zones": _avg_zones(pairs, team, own=True),
        },
        "scoring": {"situations": scoring, "bands": react["for_bands"], "goals": react["goals_for"],
                    "inside_box": round(sum(1 for s in box if (s.get("x") or 0) >= 88.5) / len(box), 3) if box else None,
                    "metrics": [x for x in (_ev(ts, team, k) for k in ("goals_pg", "xg_pg", "big_chances_pg", "xg_per_shot", "goals_minus_xg")) if x]},
        "conceding": {"situations": conceding, "bands": react["against_bands"], "goals": react["goals_against"], "opp_zones": opp_zones,
                      "metrics": [x for x in (_ev(ts, team, k) for k in ("against_pg", "xga_pg", "shots_against_pg", "big_chances_against_pg", "clean_sheets")) if x]},
        "setpieces": {"metrics": [x for x in (_ev(ts, team, k) for k in ("xg_setplay_pg", "xga_setplay_pg", "corners_pg")) if x],
                      "goals_for": (scoring or {}).get("Standard", {}).get("goals"), "goals_against": (conceding or {}).get("Standard", {}).get("goals"),
                      "corners_against": _avg_stat(pairs, team, "corners", opp=True)},
        "key_players": key_players(pairs, team, index, profile),
        "lines": best_per_line(pairs, team, index),
        "load": last_load(pairs, team),
        "absences": (lineup or {}).get("missing") or [],
        "reaction": react,
    }
