import { expect, test } from "vitest";
import { renderStatus, type ProbeReport } from "./status";

const base: ProbeReport = {
  checked_at: "2026-11-18T17:00:00+00:00", ok_count: 1, total: 2, sources: [
    { key: "openligadb", name: "OpenLigaDB", url: "u", ok: true, status: 200, elapsed_ms: 120, bytes: 5000, error: null, purpose: "Spielplan" },
    { key: "transfermarkt", name: "Transfermarkt", url: "u", ok: false, status: 403, elapsed_ms: 80, bytes: 0, error: "HTTP 403", purpose: "Karrieren" },
  ],
};

test("renders_empty_state_when_no_report", () => {
  expect(renderStatus(null, new Date())).toContain("Noch kein Abruf gelaufen.");
});

test("shows_ok_count_and_each_source", () => {
  const html = renderStatus(base, new Date("2026-11-18T18:00:00Z"));
  expect(html).toContain("1 von 2 Quellen erreichbar");
  expect(html).toContain("OpenLigaDB");
  expect(html).toContain("HTTP 403");
});

test("shows_check_time_in_berlin_time", () => {
  expect(renderStatus(base, new Date("2026-11-18T18:00:00Z"))).toContain("18.11.2026, 18:00");
});

test("marks_report_older_than_36h_as_stale", () => {
  expect(renderStatus(base, new Date("2026-11-20T05:00:01Z"))).toContain("veraltet");
  expect(renderStatus(base, new Date("2026-11-20T04:59:59Z"))).not.toContain("veraltet");
});

test("escapes_source_text", () => {
  const evil = { ...base, sources: [{ ...base.sources[1], error: "<img src=x>" }] };
  expect(renderStatus(evil, new Date())).not.toContain("<img src=x>");
});

test("unreadable_report_time_does_not_throw", () => {
  const broken = { ...base, checked_at: "kaputt" };
  expect(() => renderStatus(broken, new Date())).not.toThrow();
  expect(renderStatus(broken, new Date())).toContain("Abruf-Datei unlesbar.");
});

test("report_without_sources_does_not_throw", () => {
  const broken = { checked_at: base.checked_at } as unknown as ProbeReport;
  expect(renderStatus(broken, new Date())).toContain("Abruf-Datei unlesbar.");
});
