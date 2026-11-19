import json, re, sys
sys.path.insert(0, ".")
from matchplan_data.probe import http_fetch
from matchplan_data.fotmob import next_data, parse_league


def get(u):
    r = http_fetch(u)
    print(f"\n=== {u} -> {r.status} {len(r.text)}")
    return r.text if r.status == 200 else None


def find(obj, pat, path="", out=None, limit=10):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if re.search(pat, k, re.I):
                out.append((p, json.dumps(v, ensure_ascii=False)[:400]))
            find(v, pat, p, out, limit)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:30]):
            find(v, pat, f"{path}[{i}]", out, limit)
    return out


nd = next_data(get("https://www.fotmob.com/leagues/54/stats/bundesliga"))
st = nd["props"]["pageProps"]["stats"]
print("players stats:", [(x.get("name") or x.get("header"), x["fetchAllUrl"].split("/")[-1]) for x in st["players"]])
print("teams stats:", [(x.get("name") or x.get("header"), x["fetchAllUrl"].split("/")[-1]) for x in st.get("teams", [])])
print("seasons:", [(s["Name"], s["RelativePath"]) for s in st["seasonStatLinks"]][:12])
for name in [x["fetchAllUrl"] for x in st["players"] if "phys" in x["fetchAllUrl"]][:4] + [x["fetchAllUrl"] for x in st.get("teams", []) if "phys" in x["fetchAllUrl"]][:3]:
    t = get(name)
    if t:
        d = json.loads(t)
        tl = d["TopLists"][0]
        print("  ", tl.get("Title"), tl.get("Subtitle"), len(tl["StatList"]), json.dumps(tl["StatList"][:2], ensure_ascii=False)[:600])
# Vorsaison-Datei
rel = [s["RelativePath"] for s in st["seasonStatLinks"]][1]
t = get("https://data.fotmob.com/" + rel)
if t:
    d = json.loads(t)
    print("  topstats keys", list(d)[:5], json.dumps(d, ensure_ascii=False)[:500])
# Kommendes Spiel: Schiedsrichter / Quoten
lg = parse_league(next_data(get("https://www.fotmob.com/leagues/54/fixtures/bundesliga")))
up = [m for m in lg if not m["finished"]][:2]
for m in up:
    nd = next_data(get(f"https://www.fotmob.com/match/{m['fm_id']}"))
    if nd:
        for p, v in find(nd["props"]["pageProps"], r"referee|odds|betting|poll", limit=8):
            print("  ", p, v)
# Profil-Endpunkt
t = get("https://www.fotmob.com/api/data/playerData?id=1219540")
if t:
    d = json.loads(t)
    print("  keys", list(d)[:30])
