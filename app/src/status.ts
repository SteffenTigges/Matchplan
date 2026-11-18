export interface ProbeSource {
  key: string;
  name: string;
  url: string;
  ok: boolean;
  status: number | null;
  elapsed_ms: number | null;
  bytes: number | null;
  error: string | null;
  purpose: string;
}

export interface ProbeReport {
  checked_at: string;
  ok_count: number;
  total: number;
  sources: ProbeSource[];
}

const STALE_MS = 36 * 60 * 60 * 1000;

const esc = (s: unknown): string =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

const berlin = (d: Date): string =>
  new Intl.DateTimeFormat("de-DE", {
    timeZone: "Europe/Berlin", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
  }).format(d);

export function renderStatus(report: ProbeReport | null, now: Date): string {
  if (!report) {
    return `<section class="card"><h2>Quellen-Check</h2><p class="muted">Noch kein Abruf gelaufen.</p></section>`;
  }
  const checked = new Date(report.checked_at);
  const stale = now.getTime() - checked.getTime() > STALE_MS;
  const rows = report.sources
    .map(
      (s) => `<li class="src ${s.ok ? "ok" : "bad"}">
        <span class="dot" aria-hidden="true"></span>
        <span class="txt"><b>${esc(s.name)}</b><span class="muted">${esc(s.purpose)}</span></span>
        <span class="res">${s.ok ? "erreichbar" : esc(s.error ?? "Fehler")}<span class="muted">${s.elapsed_ms != null ? `${esc(s.elapsed_ms)} ms` : ""}</span></span>
      </li>`,
    )
    .join("");
  return `<section class="card">
    <h2>Quellen-Check</h2>
    <p class="big">${esc(report.ok_count)} von ${esc(report.total)} Quellen erreichbar</p>
    <p class="muted">Stand: ${esc(berlin(checked))} Uhr${stale ? ' <span class="chip bad">veraltet</span>' : ""}</p>
    <ul class="srcs">${rows}</ul>
  </section>`;
}
