export type Route =
  | { view: "spiele"; matchday?: number }
  | { view: "spiel"; id: number }
  | { view: "prognose"; id: number }
  | { view: "teams" }
  | { view: "team"; key: string }
  | { view: "rang"; metric: string; key: string }
  | { view: "spieler"; id?: number }
  | { view: "status" }
  | { view: "verein"; key?: string; change?: boolean }
  | { view: "scouting"; key?: string; section?: string };

export function parseRoute(hash: string): Route {
  const [name, arg, arg2] = hash.replace(/^#/, "").split("/");
  const n = Number(arg);
  if (name === "spiele" && arg !== undefined) {
    return Number.isInteger(n) && n >= 1 && n <= 34 ? { view: "spiele", matchday: n } : { view: "spiele" };
  }
  if (name === "spiel") return Number.isInteger(n) && n > 0 ? { view: "spiel", id: n } : { view: "spiele" };
  if (name === "prognose") return Number.isInteger(n) && n > 0 ? { view: "prognose", id: n } : { view: "spiele" };
  if (name === "rang" && arg && /^[a-z0-9_]+$/.test(arg) && arg2 && /^[A-Z0-9]{3}$/.test(arg2)) return { view: "rang", metric: arg, key: arg2 };
  if (name === "teams") return { view: "teams" };
  if (name === "team" && arg && /^[A-Z0-9]{3}$/.test(arg)) return { view: "team", key: arg };
  if (name === "spieler") return Number.isInteger(n) && n > 0 ? { view: "spieler", id: n } : { view: "spieler" };
  if (name === "status") return { view: "status" };
  if (name === "verein") {
    if (arg === "wechseln") return { view: "verein", change: true };
    return arg && /^[A-Z0-9]{3}$/.test(arg) ? { view: "verein", key: arg } : { view: "verein" };
  }
  if (name === "scouting") {
    if (!arg || !/^[A-Z0-9]{3}$/.test(arg)) return { view: "scouting" };
    return arg2 && /^[a-z]+$/.test(arg2) ? { view: "scouting", key: arg, section: arg2 } : { view: "scouting", key: arg };
  }
  if (name === "") return { view: "verein" };
  return { view: "spiele" };
}
