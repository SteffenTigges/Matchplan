"""Schiedsrichter-Werte dieser Saison aus den gespeicherten FotMob-Spielen."""

from __future__ import annotations


def _n(v) -> float:
    if isinstance(v, dict):
        v = v.get("n")
    return float(v) if isinstance(v, (int, float)) else 0.0


def build_referees(pairs: list[tuple[dict, dict]], upcoming: dict[str, dict]) -> dict:
    acc: dict[str, dict] = {}
    for m, fm in pairs:
        ref = (fm or {}).get("referee")
        if not ref or not m.get("score"):
            continue
        e = acc.setdefault(ref["name"], {"name": ref["name"], "id": ref.get("id"), "games": 0, "yellow": 0.0, "red": 0.0,
                                         "fouls": 0.0, "penalties": 0, "home": 0, "draw": 0, "away": 0, "teams": {}})
        st = fm.get("stats") or {}
        e["games"] += 1
        for k, f in (("yellow_cards", "yellow"), ("red_cards", "red"), ("fouls", "fouls")):
            v = st.get(k) or [0, 0]
            e[f] += _n(v[0]) + _n(v[1])
        e["penalties"] += sum(1 for s in fm.get("shots") or [] if s.get("situation") == "Penalty")
        h, a = m["score"]
        e["home" if h > a else "draw" if h == a else "away"] += 1
        for side, key in (("home", m["home"]), ("away", m["away"])):
            mine, theirs = (h, a) if side == "home" else (a, h)
            t = e["teams"].setdefault(key, {"games": 0, "points": 0})
            t["games"] += 1
            t["points"] += 3 if mine > theirs else 1 if mine == theirs else 0
    refs = {}
    for name, e in acc.items():
        g = e["games"]
        refs[name] = {"name": name, "id": e["id"], "games": g, "yellow_pg": round(e["yellow"] / g, 2), "red": int(e["red"]),
                      "fouls_pg": round(e["fouls"] / g, 1), "penalties": e["penalties"], "penalties_pg": round(e["penalties"] / g, 2),
                      "home_win": round(e["home"] / g, 3), "draw": round(e["draw"] / g, 3), "away_win": round(e["away"] / g, 3),
                      "teams": e["teams"]}
    games = sum(r["games"] for r in refs.values())
    league = {"yellow_pg": round(sum(acc[n]["yellow"] for n in acc) / games, 2) if games else None,
              "fouls_pg": round(sum(acc[n]["fouls"] for n in acc) / games, 1) if games else None,
              "penalties_pg": round(sum(acc[n]["penalties"] for n in acc) / games, 2) if games else None}
    return {"league": league, "referees": refs, "upcoming": upcoming}
