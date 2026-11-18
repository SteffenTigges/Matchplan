import "./style.css";
import { renderStatus, type ProbeReport } from "./status";

async function loadReport(): Promise<ProbeReport | null> {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}data/status/probe.json`, { cache: "no-store" });
    return res.ok ? ((await res.json()) as ProbeReport) : null;
  } catch {
    return null;
  }
}

async function start(): Promise<void> {
  const root = document.getElementById("app")!;
  root.innerHTML = renderStatus(await loadReport(), new Date());
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch(() => undefined);
  }
}

void start();
