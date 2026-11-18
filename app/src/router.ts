export type Route =
  | { view: "spiele"; matchday?: number }
  | { view: "spiel"; id: number }
  | { view: "teams" }
  | { view: "team"; key: string }
  | { view: "spieler"; id?: number }
  | { view: "status" };

export function parseRoute(hash: string): Route {
  const [name, arg] = hash.replace(/^#/, "").split("/");
  const n = Number(arg);
  if (name === "spiele" && arg !== undefined) {
    return Number.isInteger(n) && n >= 1 && n <= 34 ? { view: "spiele", matchday: n } : { view: "spiele" };
  }
  if (name === "spiel") return Number.isInteger(n) && n > 0 ? { view: "spiel", id: n } : { view: "spiele" };
  if (name === "teams") return { view: "teams" };
  if (name === "team" && arg && /^[A-Z0-9]{3}$/.test(arg)) return { view: "team", key: arg };
  if (name === "spieler") return Number.isInteger(n) && n > 0 ? { view: "spieler", id: n } : { view: "spieler" };
  if (name === "status") return { view: "status" };
  return { view: "spiele" };
}
