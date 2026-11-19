export const esc = (s: unknown): string =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

const WD: Record<string, string> = { Sun: "So.", Mon: "Mo.", Tue: "Di.", Wed: "Mi.", Thu: "Do.", Fri: "Fr.", Sat: "Sa." };

/** "Sa. 21.11., 15:30" in deutscher Zeit. */
export function berlin(iso: string): string {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/Berlin", weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
    }).formatToParts(new Date(iso)).map((p) => [p.type, p.value]),
  );
  return `${WD[parts.weekday] ?? ""} ${parts.day}.${parts.month}., ${parts.hour}:${parts.minute}`;
}

export interface CrestTeam { short: string; color: string; crest?: string | null; key?: string }

const teamAttr = (t: CrestTeam): string => (t.key ? ` data-team="${esc(t.key)}" role="link" aria-label="${esc(t.short)}: Teamseite"` : "");

const shield = (t: CrestTeam, size: number): string =>
  `<svg class="crest"${teamAttr(t)} width="${size}" height="${Math.round(size * 1.15)}" viewBox="0 0 40 46" aria-hidden="true"><path d="M20 1 L38 7 V22 C38 34 30 41 20 45 C10 41 2 34 2 22 V7 Z" fill="${esc(t.color)}"/><text x="20" y="29" text-anchor="middle" font-size="17" font-weight="800" fill="#fff" font-family="Barlow Condensed,Arial Narrow,sans-serif">${esc(t.short[0] ?? "?")}</text></svg>`;

/** Wappen von der Quelle; schlägt das Laden fehl, ersetzt ein Farbwappen das Bild. */
export function crest(t: CrestTeam, size = 28): string {
  if (!t.crest) return shield(t, size);
  const fallback = esc(shield(t, size)).replace(/&quot;/g, "&#34;");
  return `<img class="crest"${teamAttr(t)} src="${esc(t.crest)}" width="${size}" height="${size}" alt="" loading="lazy" onerror="this.outerHTML=this.dataset.f" data-f="${fallback}">`;
}

const initials = (name: string): string =>
  name.split(/\s+/).filter(Boolean).map((w) => w[0]!.toUpperCase()).slice(0, 2).join("");

/** Spielerfoto; ohne oder mit kaputtem Bild erscheinen die Initialen. */
export function photo(url: string | null | undefined, name: string, size = 40): string {
  const ini = `<span class="ini" style="width:${size}px;height:${size}px">${esc(initials(name))}</span>`;
  if (!url) return ini;
  return `<img class="photo" src="${esc(url)}" width="${size}" height="${size}" alt="${esc(name)}" loading="lazy" onerror="this.outerHTML=this.dataset.f" data-f="${esc(ini)}">`;
}

export const normName = (s: string): string =>
  s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().split(/[^a-z0-9]+/).filter(Boolean).join(" ");

/** FotMob-Spieler-ID zu einem Namen („Harry Kane“, „H. Kane“, „Kane“), zuerst im genannten Team, sonst ligaweit; nur eindeutige Treffer. */
export function findPlayer(links: { names: Record<string, Record<string, number>> } | null | undefined, name: string, team?: string | null): number | null {
  if (!links || !name) return null;
  const want = normName(name).split(" ");
  if (!want.length) return null;
  const last = want[want.length - 1]!;
  const initial = want.length > 1 && want[0]!.length === 1 ? want[0] : null;
  const pools = team && links.names[team] ? [links.names[team]!, ...Object.values(links.names)] : Object.values(links.names);
  for (const pool of pools) {
    const exact = pool[want.join(" ")];
    if (exact) return exact;
    const hits = Object.entries(pool).filter(([k]) => {
      const t = k.split(" ");
      return t[t.length - 1] === last && (!initial || t[0]!.startsWith(initial));
    });
    if (hits.length === 1) return hits[0]![1];
    if (hits.length > 1) return null;
  }
  return null;
}

/** Name (und optional Bild) als Link aufs Spielerprofil, wenn die ID bekannt ist. */
export const playerLink = (id: number | null | undefined, inner: string): string =>
  id ? `<a class="plink" href="#spieler/${id}">${inner}</a>` : inner;
