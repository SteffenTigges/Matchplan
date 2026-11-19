"""Einmalige Erkundung alternativer Quellen (läuft nur auf einem Erkundungszweig, wird nicht zusammengeführt)."""
import csv, io, json, re, sys
sys.path.insert(0, ".")
from matchplan_data.probe import http_fetch
from matchplan_data.fotmob import next_data


def get(u):
    try:
        r = http_fetch(u)
        print(f"\n=== {u} -> {r.status} {len(r.text)} chars")
        return r.text if r.status == 200 else None
    except Exception as e:
        print(f"\n=== {u} -> ERROR {e}")
        return None


def find(obj, pat, path="", out=None, limit=12):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if re.search(pat, k, re.I):
                out.append((p, json.dumps(v, ensure_ascii=False)[:300]))
            find(v, pat, p, out, limit)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:40]):
            find(v, pat, f"{path}[{i}]", out, limit)
    elif isinstance(obj, str) and re.search(pat, obj, re.I) and len(out) < limit:
        out.append((path, obj[:300]))
    return out


# 1) Liga-Statistikseiten (andere Ligen, frühere Saisons)
for lid, slug in ((54, "bundesliga"), (47, "premier-league")):
    h = get(f"https://www.fotmob.com/leagues/{lid}/stats/{slug}")
    nd = next_data(h) if h else None
    if nd:
        for p, v in find(nd, r"data\.fotmob\.com/stats|fetchAllUrl|seasonStatLinks|statsLinks", limit=8):
            print("  ", p, v)
urls = []
h = get("https://www.fotmob.com/leagues/47/stats/premier-league")
nd = next_data(h) if h else None
if nd:
    urls = re.findall(r"https://data\.fotmob\.com/stats/[^\"']+\.json", json.dumps(nd))
print("stats json urls:", len(urls), urls[:6])
for u in urls[:2]:
    t = get(u)
    if t:
        try:
            d = json.loads(t)
            print("  keys", list(d)[:10])
            print("  sample", json.dumps(d, ensure_ascii=False)[:1200])
        except Exception as e:
            print("  not json", e, t[:200])

# 2) Spielerseite: Saisonwerte?
h = get("https://www.fotmob.com/players/1219540/x")
nd = next_data(h) if h else None
if nd:
    d = nd["props"]["pageProps"]["data"]
    print("  data keys", list(d))
    te = d["careerHistory"]["careerItems"]["senior"]["teamEntries"][0]
    print("  teamEntry keys", list(te))
    for p, v in find(d, r"season", limit=15):
        print("  ", p, v)
get("https://www.fotmob.com/api/playerData?id=1219540")
get("https://www.fotmob.com/api/data/playerData?id=1219540")

# 3) Schiedsrichter in Spielseiten
for mid in (5881219, 5881147):
    h = get(f"https://www.fotmob.com/match/{mid}")
    nd = next_data(h) if h else None
    if nd:
        for p, v in find(nd, r"referee", limit=6):
            print("  ", p, v)
h = get("https://www.fotmob.com/leagues/54/fixtures/bundesliga")
nd = next_data(h) if h else None
if nd:
    ms = [m for m in re.findall(r'"id":"?(\d{7})"?,"pageUrl"', json.dumps(nd))]
    print("  match ids", len(ms))

# 4) Understat, ClubElo
t = get("https://understat.com/league/Bundesliga/2026")
if t:
    print("  playersData" in t, "datesData" in t, t[:300].replace("\n", " "))
t = get("http://api.clubelo.com/Bayern")
if t:
    print("  ", t[:300])
t = get("http://clubelo.com/")
if t:
    print("  ", t[:200])

# 5) football-data: Quoten der nächsten Spiele, 2. Liga
t = get("https://www.football-data.co.uk/fixtures.csv")
if t:
    rows = list(csv.DictReader(io.StringIO(t.lstrip("﻿"))))
    from collections import Counter
    print("  divs", Counter(r.get("Div") for r in rows).most_common(12))
    print("  dates", sorted({r.get("Date") for r in rows})[:10])
for y in ("2526", "1617"):
    t = get(f"https://www.football-data.co.uk/mmz4281/{y}/D2.csv")
    if t:
        rows = list(csv.DictReader(io.StringIO(t.lstrip("﻿"))))
        print("  D2", y, len(rows), sorted({r["HomeTeam"] for r in rows}))
t = get("https://www.football-data.co.uk/mmz4281/1617/D1.csv")
if t:
    rows = list(csv.DictReader(io.StringIO(t.lstrip("﻿"))))
    print("  D1 1617", len(rows), list(rows[0])[:12])
