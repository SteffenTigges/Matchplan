"""Saisonwerte je Team aus den FotMob-Spieldaten, mit Ligarang je Kennzahl und xPunkten."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

CATEGORIES = ["Allgemein", "Offensive", "Schüsse", "Passspiel & Aufbau", "Defensive", "Gegen den Ball",
              "Standards", "Zweikämpfe & Disziplin", "Glück & Effizienz"]


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    category: str
    higher_is_better: bool
    fmt: str  # "int" | "dec1" | "dec2" | "pct" | "signed1"
    approx: bool = False


METRICS: list[Metric] = [
    Metric("points", "Punkte", "Allgemein", True, "int"),
    Metric("possession", "Ballbesitz Ø", "Allgemein", True, "pct"),
    Metric("goal_diff", "Tordifferenz", "Allgemein", True, "signed0"),
    Metric("goals_pg", "Tore pro Spiel", "Offensive", True, "dec2"),
    Metric("xg_pg", "xG pro Spiel", "Offensive", True, "dec2"),
    Metric("big_chances_pg", "Großchancen pro Spiel", "Offensive", True, "dec1"),
    Metric("box_touches_pg", "Ballaktionen im gegn. Strafraum pro Spiel", "Offensive", True, "dec1"),
    Metric("field_tilt", "Field Tilt", "Offensive", True, "pct", approx=True),
    Metric("shots_pg", "Schüsse pro Spiel", "Schüsse", True, "dec1"),
    Metric("on_target_pg", "Schüsse aufs Tor pro Spiel", "Schüsse", True, "dec1"),
    Metric("inside_box_share", "Anteil Schüsse aus dem Strafraum", "Schüsse", True, "pct"),
    Metric("xg_per_shot", "xG pro Schuss", "Schüsse", True, "dec2"),
    Metric("xgot_pg", "xGOT pro Spiel", "Schüsse", True, "dec2"),
    Metric("passes_pg", "Pässe pro Spiel", "Passspiel & Aufbau", True, "int"),
    Metric("pass_accuracy", "Passquote", "Passspiel & Aufbau", True, "pct"),
    Metric("opp_half_share", "Anteil Pässe in der gegn. Hälfte", "Passspiel & Aufbau", True, "pct"),
    Metric("long_ball_accuracy", "Lange Bälle angekommen", "Passspiel & Aufbau", True, "pct"),
    Metric("cross_accuracy", "Flankenquote", "Passspiel & Aufbau", True, "pct"),
    Metric("against_pg", "Gegentore pro Spiel", "Defensive", False, "dec2"),
    Metric("xga_pg", "Zugelassene xG pro Spiel", "Defensive", False, "dec2"),
    Metric("shots_against_pg", "Zugelassene Schüsse pro Spiel", "Defensive", False, "dec1"),
    Metric("big_chances_against_pg", "Zugelassene Großchancen pro Spiel", "Defensive", False, "dec1"),
    Metric("clean_sheets", "Spiele ohne Gegentor", "Defensive", True, "int"),
    Metric("ppda", "PPDA", "Gegen den Ball", False, "dec1", approx=True),
    Metric("tackles_pg", "Tacklings pro Spiel", "Gegen den Ball", True, "dec1"),
    Metric("interceptions_pg", "Abgefangene Bälle pro Spiel", "Gegen den Ball", True, "dec1"),
    Metric("xg_setplay_pg", "xG nach Standards pro Spiel", "Standards", True, "dec2"),
    Metric("xga_setplay_pg", "Zugelassene xG nach Standards pro Spiel", "Standards", False, "dec2"),
    Metric("corners_pg", "Ecken pro Spiel", "Standards", True, "dec1"),
    Metric("duel_rate", "Zweikampfquote", "Zweikämpfe & Disziplin", True, "pct"),
    Metric("aerial_rate", "Luftzweikämpfe gewonnen", "Zweikämpfe & Disziplin", True, "pct"),
    Metric("dribbles_pg", "Erfolgreiche Dribblings pro Spiel", "Zweikämpfe & Disziplin", True, "dec1"),
    Metric("fouls_pg", "Fouls pro Spiel", "Zweikämpfe & Disziplin", False, "dec1"),
    Metric("yellow_pg", "Gelbe Karten pro Spiel", "Zweikämpfe & Disziplin", False, "dec2"),
    Metric("goals_minus_xg", "Tore minus xG", "Glück & Effizienz", True, "signed1"),
    Metric("against_minus_xga", "Gegentore minus zugelassene xG", "Glück & Effizienz", False, "signed1"),
    Metric("points_minus_xpoints", "Punkte minus xPunkte", "Glück & Effizienz", True, "signed1"),
]


def _goal_dist(xgs: list[float]) -> list[float]:
    """Wahrscheinlichkeit für 0, 1, 2 … Tore bei unabhängigen Schüssen (Poisson-Binomial)."""
    dist = [1.0]
    for p in xgs:
        p = min(max(p or 0.0, 0.0), 1.0)
        nxt = [0.0] * (len(dist) + 1)
        for k, q in enumerate(dist):
            nxt[k] += q * (1 - p)
            nxt[k + 1] += q * p
        dist = nxt
    return dist


def xpoints(home_xg: list[float], away_xg: list[float]) -> tuple[float, float]:
    h, a = _goal_dist(home_xg), _goal_dist(away_xg)
    win = sum(ph * pa for i, ph in enumerate(h) for j, pa in enumerate(a) if i > j)
    draw = sum(ph * pa for i, ph in enumerate(h) for j, pa in enumerate(a) if i == j)
    loss = 1 - win - draw
    return 3 * win + draw, 3 * loss + draw


def _n(v) -> float:
    if isinstance(v, dict):
        return float(v.get("n") or 0)
    return float(v or 0)


def _attempts(v) -> float:
    """Versuche aus 'angekommen (x%)'."""
    if isinstance(v, dict) and v.get("pct"):
        return v["n"] / (v["pct"] / 100)
    return 0.0


def aggregate(pairs: list[tuple[dict, dict]]) -> dict[str, dict[str, float]]:
    s: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for m, fm in pairs:
        if not m.get("finished") or not m.get("score"):
            continue
        st = fm.get("stats") or {}
        shots = fm.get("shots") or []
        sides = [(m["home"], 0, 1), (m["away"], 1, 0)]
        xp = xpoints([x["xg"] or 0 for x in shots if x["team"] == m["home"] and not x["own_goal"]],
                     [x["xg"] or 0 for x in shots if x["team"] == m["away"] and not x["own_goal"]]) if shots else None

        def v(key: str, i: int) -> float:
            vals = st.get(key)
            return _n(vals[i]) if vals else 0.0

        for team, i, j in sides:
            t = s[team]
            gf, ga = m["score"][i], m["score"][j]
            t["matches"] += 1
            t["points"] += 3 if gf > ga else 1 if gf == ga else 0
            t["gf"] += gf
            t["ga"] += ga
            t["clean_sheets"] += 1 if ga == 0 else 0
            if "expected_goals" in st:
                t["gf_xg"] += gf
                t["ga_xg"] += ga
            if all(k in st for k in ("tackles", "interceptions", "fouls", "own_half_passes")):
                t["defacts"] += v("tackles", i) + v("interceptions", i) + v("fouls", i)
                t["opp_own_half"] += v("own_half_passes", j)
            for key, name in [("expected_goals", "xg"), ("big_chance", "bc"), ("touches_opp_box", "box"), ("total_shots", "shots"),
                              ("ShotsOnTarget", "sot"), ("shots_inside_box", "inbox"), ("expected_goals_on_target", "xgot"),
                              ("passes", "passes"), ("accurate_passes", "acc"), ("opposition_half_passes", "opph"),
                              ("tackles", "tackles"), ("interceptions", "inter"), ("expected_goals_set_play", "xgsp"),
                              ("corners", "corners"), ("duel_won", "duels"), ("aerials_won", "aerials"),
                              ("dribbles_succeeded", "dribbles"), ("fouls", "fouls"), ("yellow_cards", "yellow"),
                              ("BallPossesion", "poss")]:
                if key in st:  # fehlende Werte zählen nicht als 0
                    t[name] += v(key, i)
                    t[name + "_opp"] += v(key, j)
                    t["n_" + name] += 1
            for key, name in [("long_balls_accurate", "long"), ("accurate_crosses", "cross")]:
                vals = st.get(key)
                if vals:
                    t[name] += _n(vals[i])
                    t[name + "_att"] += _attempts(vals[i])
            if xp:
                t["xpoints"] += xp[i]
                t["xp_matches"] += 1

    def div(a: float, b: float) -> float | None:
        return a / b if b else None

    out: dict[str, dict[str, float | None]] = {}
    for team, t in s.items():
        n = t["matches"]

        def pg(name: str, opp: bool = False) -> float | None:  # pro Spiel, nur Spiele mit diesem Wert
            return div(t[name + ("_opp" if opp else "")], t["n_" + name])

        def share(a: float, b: float, name: str) -> float | None:
            return div(a, b) if t["n_" + name] else None

        poss = pg("poss")
        out[team] = {
            "matches": int(n),
            "points": int(t["points"]),
            "possession": poss / 100 if poss is not None else None,
            "goal_diff": t["gf"] - t["ga"],
            "goals_pg": div(t["gf"], n),
            "xg_pg": pg("xg"),
            "big_chances_pg": pg("bc"),
            "box_touches_pg": pg("box"),
            "field_tilt": share(t["box"], t["box"] + t["box_opp"], "box"),
            "shots_pg": pg("shots"),
            "on_target_pg": pg("sot"),
            "inside_box_share": share(t["inbox"], t["shots"], "inbox"),
            "xg_per_shot": share(t["xg"], t["shots"], "xg"),
            "xgot_pg": pg("xgot"),
            "passes_pg": pg("passes"),
            "pass_accuracy": share(t["acc"], t["passes"], "acc"),
            "opp_half_share": share(t["opph"], t["passes"], "opph"),
            "long_ball_accuracy": div(t["long"], t["long_att"]),
            "cross_accuracy": div(t["cross"], t["cross_att"]),
            "against_pg": div(t["ga"], n),
            "xga_pg": pg("xg", opp=True),
            "shots_against_pg": pg("shots", opp=True),
            "big_chances_against_pg": pg("bc", opp=True),
            "clean_sheets": int(t["clean_sheets"]),
            "ppda": div(t["opp_own_half"], t["defacts"]),
            "tackles_pg": pg("tackles"),
            "interceptions_pg": pg("inter"),
            "xg_setplay_pg": pg("xgsp"),
            "xga_setplay_pg": pg("xgsp", opp=True),
            "corners_pg": pg("corners"),
            "duel_rate": share(t["duels"], t["duels"] + t["duels_opp"], "duels"),
            "aerial_rate": share(t["aerials"], t["aerials"] + t["aerials_opp"], "aerials"),
            "dribbles_pg": pg("dribbles"),
            "fouls_pg": pg("fouls"),
            "yellow_pg": pg("yellow"),
            "goals_minus_xg": t["gf_xg"] - t["xg"] if t["n_xg"] else None,
            "against_minus_xga": t["ga_xg"] - t["xg_opp"] if t["n_xg"] else None,
            "points_minus_xpoints": t["points"] - t["xpoints"] if t["xp_matches"] == n else None,
        }
    return out


def rank(values: dict[str, float], higher_is_better: bool) -> dict[str, int]:
    """Platz 1 = bester Wert; gleiche Werte teilen sich den besseren Platz."""
    better = (lambda a, b: a > b) if higher_is_better else (lambda a, b: a < b)
    return {k: 1 + sum(1 for o in values.values() if better(o, v)) for k, v in values.items()}


def build_teamstats(values: dict[str, dict[str, float]]) -> dict:
    teams: dict[str, dict] = {k: {"matches": v["matches"]} for k, v in values.items()}
    for m in METRICS:
        col = {k: round(v[m.key], 4) for k, v in values.items() if v[m.key] is not None}
        ranks = rank(col, m.higher_is_better)
        for k in values:
            teams[k][m.key] = {"value": col.get(k), "rank": ranks.get(k)}
    return {"categories": CATEGORIES, "metrics": [asdict(m) for m in METRICS], "teams": teams}
