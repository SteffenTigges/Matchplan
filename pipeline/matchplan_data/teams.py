"""Die 18 Vereine der Bundesliga 2026/27 mit ihren Kennungen in den einzelnen Quellen."""

from __future__ import annotations

from dataclasses import dataclass

LI = "https://www.ligainsider.de"


@dataclass(frozen=True)
class Team:
    key: str
    name: str
    short: str
    oldb_id: int
    li_url: str
    color: str
    fotmob_id: int = 0

    @property
    def crest(self) -> str:
        slug = self.li_url.rstrip("/").split("/")[-2]
        return f"https://cdn.ligainsider.de/images/teams/medium/{CREST_SLUG.get(self.key, slug)}-wappen.png"


# Ligainsider nutzt für einige Wappen andere Dateinamen als in der Vereins-URL.
CREST_SLUG = {
    "TSG": "tsg-1899-hoffenheim",
    "M05": "fsv-mainz-05",
    "FCU": "1fc-union-berlin",
}

TEAMS: list[Team] = [
    Team("FCB", "FC Bayern München", "Bayern", 40, f"{LI}/fc-bayern-muenchen/1/", "#dc052d", 9823),
    Team("BVB", "Borussia Dortmund", "Dortmund", 7, f"{LI}/borussia-dortmund/14/", "#e3b505", 9789),
    Team("RBL", "RB Leipzig", "Leipzig", 1635, f"{LI}/rb-leipzig/1311/", "#c8102e", 178475),
    Team("VFB", "VfB Stuttgart", "Stuttgart", 16, f"{LI}/vfb-stuttgart/12/", "#e32219", 10269),
    Team("TSG", "TSG Hoffenheim", "Hoffenheim", 175, f"{LI}/tsg-hoffenheim/10/", "#1961b5", 8226),
    Team("B04", "Bayer 04 Leverkusen", "Leverkusen", 6, f"{LI}/bayer-04-leverkusen/4/", "#e32221", 8178),
    Team("SCF", "SC Freiburg", "Freiburg", 112, f"{LI}/sc-freiburg/18/", "#2b2b2b", 8358),
    Team("SGE", "Eintracht Frankfurt", "Frankfurt", 91, f"{LI}/eintracht-frankfurt/3/", "#1a1a1a", 9810),
    Team("FCA", "FC Augsburg", "Augsburg", 95, f"{LI}/fc-augsburg/21/", "#ba3733", 8406),
    Team("M05", "1. FSV Mainz 05", "Mainz", 81, f"{LI}/1-fsv-mainz-05/17/", "#c3141e", 9905),
    Team("FCU", "1. FC Union Berlin", "Union", 80, f"{LI}/1-fc-union-berlin/1246/", "#d4011d", 8149),
    Team("BMG", "Borussia Mönchengladbach", "Gladbach", 87, f"{LI}/borussia-moenchengladbach/5/", "#1b1b1b", 9788),
    Team("HSV", "Hamburger SV", "HSV", 100, f"{LI}/hamburger-sv/9/", "#0a3f86", 9790),
    Team("KOE", "1. FC Köln", "Köln", 65, f"{LI}/1-fc-koeln/15/", "#ed1c24", 8722),
    Team("SVW", "SV Werder Bremen", "Bremen", 134, f"{LI}/sv-werder-bremen/2/", "#1d9053", 8697),
    Team("S04", "FC Schalke 04", "Schalke", 9, f"{LI}/fc-schalke-04/13/", "#004d9d", 10189),
    Team("SVE", "SV 07 Elversberg", "Elversberg", 198, f"{LI}/sv-07-elversberg/1331/", "#1c1c1c", 8232),
    Team("SCP", "SC Paderborn 07", "Paderborn", 31, f"{LI}/sc-paderborn-07/1249/", "#005ca9", 8460),
]

_BY_OLDB = {t.oldb_id: t for t in TEAMS}
_BY_NAME = {t.name: t for t in TEAMS}
_BY_KEY = {t.key: t for t in TEAMS}
_BY_FOTMOB = {t.fotmob_id: t for t in TEAMS}


def team_by_oldb(oldb_id: int) -> Team:
    return _BY_OLDB[oldb_id]


def team_by_name(name: str) -> Team:
    return _BY_NAME[name]


def team_by_key(key: str) -> Team:
    return _BY_KEY[key]


def team_by_fotmob(fotmob_id: int | str) -> Team:
    return _BY_FOTMOB[int(fotmob_id)]


# Schreibweise bei football-data.co.uk (Quoten, Vorsaison-Ergebnisse)
FD_NAMES = {
    "Bayern Munich": "FCB", "Dortmund": "BVB", "RB Leipzig": "RBL", "Stuttgart": "VFB", "Hoffenheim": "TSG",
    "Leverkusen": "B04", "Freiburg": "SCF", "Ein Frankfurt": "SGE", "Augsburg": "FCA", "Mainz": "M05",
    "Union Berlin": "FCU", "M'gladbach": "BMG", "Hamburg": "HSV", "FC Koln": "KOE", "Werder Bremen": "SVW",
    "Schalke 04": "S04", "Elversberg": "SVE", "Paderborn": "SCP",
}
