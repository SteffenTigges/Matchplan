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

export interface CrestTeam { short: string; color: string; crest?: string | null }

const shield = (t: CrestTeam, size: number): string =>
  `<svg class="crest" width="${size}" height="${Math.round(size * 1.15)}" viewBox="0 0 40 46" aria-hidden="true"><path d="M20 1 L38 7 V22 C38 34 30 41 20 45 C10 41 2 34 2 22 V7 Z" fill="${esc(t.color)}"/><text x="20" y="29" text-anchor="middle" font-size="17" font-weight="800" fill="#fff" font-family="Barlow Condensed,Arial Narrow,sans-serif">${esc(t.short[0] ?? "?")}</text></svg>`;

/** Wappen von der Quelle; schlägt das Laden fehl, ersetzt ein Farbwappen das Bild. */
export function crest(t: CrestTeam, size = 28): string {
  if (!t.crest) return shield(t, size);
  const fallback = esc(shield(t, size)).replace(/&quot;/g, "&#34;");
  return `<img class="crest" src="${esc(t.crest)}" width="${size}" height="${size}" alt="" loading="lazy" onerror="this.outerHTML=this.dataset.f" data-f="${fallback}">`;
}

const initials = (name: string): string =>
  name.split(/\s+/).filter(Boolean).map((w) => w[0]!.toUpperCase()).slice(0, 2).join("");

/** Spielerfoto; ohne oder mit kaputtem Bild erscheinen die Initialen. */
export function photo(url: string | null | undefined, name: string, size = 40): string {
  const ini = `<span class="ini" style="width:${size}px;height:${size}px">${esc(initials(name))}</span>`;
  if (!url) return ini;
  return `<img class="photo" src="${esc(url)}" width="${size}" height="${size}" alt="${esc(name)}" loading="lazy" onerror="this.outerHTML=this.dataset.f" data-f="${esc(ini)}">`;
}
