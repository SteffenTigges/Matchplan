import { readFileSync } from "node:fs";
import { expect, test } from "vitest";

// Lädt public/sw.js mit nachgebauten Service-Worker-Globals und liefert den fetch-Handler.
function loadSw(cached: Record<string, string>, network: (url: string) => Promise<Response>) {
  const handlers: Record<string, (e: any) => void> = {};
  const store = new Map(Object.entries(cached).map(([k, v]) => [k, new Response(v)]));
  const cache = { put: async (req: { url: string }, res: Response) => { store.set(req.url, res); }, addAll: async () => {} };
  const self = { location: { origin: "https://x.test" }, addEventListener: (t: string, h: any) => (handlers[t] = h),
    skipWaiting: () => {}, clients: { claim: () => {} } };
  const caches = { open: async () => cache, match: async (req: { url: string }) => store.get(req.url)?.clone(), keys: async () => [], delete: async () => true };
  const src = readFileSync(new URL("../public/sw.js", import.meta.url), "utf8");
  new Function("self", "caches", "fetch", src)(self, caches, (req: { url: string }) => network(req.url));
  return async (url: string, mode: string) => {
    let p!: Promise<Response>;
    handlers.fetch({ request: { url, mode, method: "GET", clone() { return this; } }, respondWith: (r: Promise<Response>) => (p = r) });
    return p ? (await p).text() : null;
  };
}

test("navigation_prefers_network_so_new_deploys_arrive", async () => {
  const fetchEv = loadSw({ "https://x.test/matchplan/": "ALT" }, async () => new Response("NEU"));
  expect(await fetchEv("https://x.test/matchplan/", "navigate")).toBe("NEU");
});

test("navigation_falls_back_to_cache_when_offline", async () => {
  const fetchEv = loadSw({ "https://x.test/matchplan/": "ALT" }, async () => { throw new TypeError("offline"); });
  expect(await fetchEv("https://x.test/matchplan/", "navigate")).toBe("ALT");
});

test("hashed_assets_come_from_cache", async () => {
  const fetchEv = loadSw({ "https://x.test/matchplan/assets/index-abc.js": "CACHED" }, async () => new Response("NET"));
  expect(await fetchEv("https://x.test/matchplan/assets/index-abc.js", "no-cors")).toBe("CACHED");
});
