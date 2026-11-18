import { expect, test } from "vitest";
import type { TeamInfo, TeamLineup } from "../data";
import { renderHistory, renderMissing, renderPitch } from "./lineup";

const team = (prefix: string, formation: number[], alt = false): TeamLineup => {
  let n = 0;
  const p = () => ({ id: `${prefix}-${++n}`, name: `${prefix}${n}`, photo: `https://cdn.ligainsider.de/${prefix}${n}.jpg` });
  const rows = [[{ player: p(), alternatives: [] }], ...formation.map((k) => Array.from({ length: k }, () => ({ player: p(), alternatives: [] as any[] })))];
  if (alt) rows[1][1].alternatives = [{ id: "x", name: "Castrop", photo: null }];
  return { team: prefix, formation: formation.join("-"), rows, missing: [{ name: "Kō Itakura", kind: "Gelb-Rote Karte", note: "Sperre" }],
    updated_label: "Gestern | 17.11.2026 21:02", opponent: null, home: true, fetched_at: "2026-11-18T16:00:00+00:00" };
};
const H: TeamInfo = { name: "Borussia Mönchengladbach", short: "Gladbach", color: "#1b1b1b", crest: "c.png" };
const A: TeamInfo = { name: "Borussia Dortmund", short: "Dortmund", color: "#e3b505", crest: "d.png" };

test("pitch_contains_all_22_names", () => {
  const svg = renderPitch(team("Heim", [3, 4, 3]), team("Gast", [4, 2, 3, 1]), H, A);
  for (let i = 1; i <= 11; i++) {
    expect(svg).toContain(`>Heim${i}<`);
    expect(svg).toContain(`>Gast${i}<`);
  }
});

test("pitch_marks_alternatives", () => {
  expect(renderPitch(team("Heim", [3, 4, 3], true), team("Gast", [4, 4, 2]), H, A)).toContain("oder Castrop");
});

test("photo_has_fallback_handler", () => {
  const svg = renderPitch(team("Heim", [3, 4, 3]), team("Gast", [4, 4, 2]), H, A);
  expect(svg).toContain('href="https://cdn.ligainsider.de/Heim1.jpg"');
  expect(svg).toContain("onerror");
});

test("missing_shows_kind_and_note", () => {
  const html = renderMissing(H, team("Heim", [3, 4, 3]));
  expect(html).toContain("Kō Itakura");
  expect(html).toContain("Gelb-Rote Karte");
  expect(html).toContain("Sperre");
});

test("history_lists_events_in_order", () => {
  const html = renderHistory(
    [
      { at: "2026-11-16T08:12:00+00:00", team: "BMG", kind: "first", text: "Erste Prognose: 3-4-3" },
      { at: "2026-11-18T13:30:00+00:00", team: "BMG", kind: "out", text: "Herold nicht mehr in der Startelf" },
    ],
    { BMG: H },
  );
  expect(html.indexOf("Erste Prognose")).toBeLessThan(html.indexOf("Herold nicht mehr"));
  expect(html).toContain("Mo. 16.11.<br>09:12");
});

test("history_empty_state", () => {
  expect(renderHistory([], { BMG: H })).toContain("Noch keine Änderungen");
});
