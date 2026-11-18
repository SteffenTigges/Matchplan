import { expect, test } from "vitest";
import type { PlayerProfile, PlayerRow, Season } from "../data";
import { filterPlayers, renderPlayer, renderPlayerList } from "./players";

const season: Season = { season: 2026, current_matchday: 10, updated_at: "", teams: {
  TSG: { name: "TSG Hoffenheim", short: "Hoffenheim", color: "#1961b5", crest: "" },
  S04: { name: "FC Schalke 04", short: "Schalke", color: "#004d9d", crest: "" } } };
const rows: PlayerRow[] = [
  { id: 1219540, name: "Fisnik Asllani", team: "TSG", pos: "ST", age: 24, minutes: 399, apps: 7, rating: 7.32 },
  { id: 2, name: "Dejan Ljubičić", team: "S04", pos: "CM", age: 28, minutes: 700, apps: 9, rating: 6.9 },
];
const prof: PlayerProfile = {
  id: 1219540, name: "Fisnik Asllani", team: "TSG", team_name: "Hoffenheim", birth_date: "2002-08-08", age: 24, height_cm: 191,
  foot: "beidfüßig", country: "Kosovo", shirt: 11, market_value: 33943829, contract_end: "2029-06-30",
  positions: [{ label: "Stürmer", short: "ST", main: true }],
  stats: [{ group: "Abschluss", key: "expected_goals", title: "xG", value: 2.42, per90: 0.546, pct: 87.3 }],
  career: { senior: [{ team: "Hoffenheim", start: "2025-07-01", end: null, apps: 47, goals: 13, kind: "Leihende" }],
    youth: [{ team: "1. FC Union Berlin Under 17", start: "2018-07-01", end: "2019-06-30", apps: 23, goals: 23, kind: null }],
    national: [], national_youth: [] },
  transfers: [{ from: "Hoffenheim", to: "Elversberg", date: "2024-07-23", fee: "Leihe", loan: true }], fetched_at: "2026-11-18T16:00:00+00:00",
};

test("search_ignores_diacritics", () => {
  expect(filterPlayers(rows, "ljubicic").map((r) => r.id)).toEqual([2]);
  expect(filterPlayers(rows, "ASLL").map((r) => r.id)).toEqual([1219540]);
  expect(filterPlayers(rows, "").length).toBe(2);
});

test("list_groups_by_team_and_links", () => {
  const html = renderPlayerList(rows, season, "");
  expect(html).toContain('href="#spieler/1219540"');
  expect(html.indexOf("Hoffenheim")).toBeLessThan(html.indexOf("Schalke"));
});

test("renders_percentile_bars", () => {
  const html = renderPlayer(prof, rows[0], season);
  expect(html).toContain("0,55 /90");
  expect(html).toContain('style="width:87%');
  expect(html).toContain("87");
});

test("renders_bio_and_value", () => {
  const html = renderPlayer(prof, rows[0], season);
  expect(html).toContain("191 cm");
  expect(html).toContain("33,9 Mio. €");
  expect(html).toContain("Vertrag bis 2029");
  expect(html).toContain("images.fotmob.com/image_resources/playerimages/1219540.png");
});

test("career_open_end_label", () => {
  const html = renderPlayer(prof, rows[0], season);
  expect(html).toContain("seit 2025");
  expect(html).toContain("2018–2019");
  expect(html).not.toContain("undefined");
  expect(html.indexOf("Union Berlin")).toBeLessThan(html.indexOf("seit 2025"));
});

test("hides_empty_sections", () => {
  const bare = { ...prof, stats: [], transfers: [], career: { senior: [], youth: [], national: [], national_youth: [] } };
  const html = renderPlayer(bare, rows[0], season);
  expect(html).not.toContain("Saisonwerte im Vergleich");
  expect(html).not.toContain("Transfers");
  expect(html).not.toContain("Karriere");
});

test("missing_profile_shows_basic_row", () => {
  expect(renderPlayer(null, rows[0], season)).toContain("Profil wird beim nächsten Abruf geladen");
});

test("percent_stats_show_percent_without_per90", () => {
  const p = { ...prof, stats: [{ group: "Passspiel", key: "successful_passes_accuracy", title: "Passquote", value: 75.5, per90: 75.52, pct: 30.2, fmt: "percent" }] };
  const html = renderPlayer(p, rows[0], season);
  expect(html).toContain("75,5 %");
  expect(html).not.toContain("75,52 /90");
});

test("player_outside_bundesliga_shows_new_club", () => {
  const p = { ...prof, team: null, team_name: "Austria Wien" };
  const html = renderPlayer(p, rows[0], season);
  expect(html).toContain("Austria Wien");
  expect(html).not.toContain("TSG Hoffenheim");
  expect(html).not.toContain("#1961b5");
});
