import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body><div id='root'></div></body></html>", {
  url: "http://localhost/",
  pretendToBeVisual: true,
});

globalThis.window = dom.window;
globalThis.document = dom.window.document;
Object.defineProperty(globalThis, "navigator", {
  value: dom.window.navigator,
  configurable: true,
});
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.HTMLButtonElement = dom.window.HTMLButtonElement;
globalThis.Node = dom.window.Node;
globalThis.Element = dom.window.Element;
globalThis.Event = dom.window.Event;
globalThis.MouseEvent = dom.window.MouseEvent;
globalThis.MutationObserver = dom.window.MutationObserver;
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
globalThis.IntersectionObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
globalThis.requestAnimationFrame = (cb) => setTimeout(() => cb(Date.now()), 0);
globalThis.cancelAnimationFrame = (id) => clearTimeout(id);
dom.window.matchMedia =
  dom.window.matchMedia ||
  (() => ({
    matches: false,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() {},
  }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const errors = [];
const origError = console.error;
console.error = (...args) => {
  errors.push(args.map(String).join(" "));
  origError(...args);
};
process.on("uncaughtException", (e) => errors.push("uncaughtException: " + (e?.stack || e)));
process.on("unhandledRejection", (e) => errors.push("unhandledRejection: " + (e?.stack || e)));

const { createServer } = await import("vite");
const vite = await createServer({
  server: { middlewareMode: true },
  appType: "custom",
  logLevel: "error",
});

const React = (await import("react")).default;
const { createRoot } = await import("react-dom/client");
const { act } = await import("react");

const modalMod = await vite.ssrLoadModule("/src/components/crops/CompareModal.tsx");
const svcMod = await vite.ssrLoadModule("/src/services/crops.ts");

function crop(id, name, status, score) {
  return {
    crop_id: id,
    crop_name: name.toLowerCase(),
    display_name: name,
    category: "cereal",
    description: `${name} description`,
    status,
    status_label: status === "suitable" ? "Potentially suitable" : "Needs more information",
    score,
    coverage: 0.8,
    preliminary: true,
    factors: {
      ph: { factor: "ph", label: "Soil pH", status: "missing_input", score: null, weight: 1, input: null, detail: "No current soil pH", requirement: { factor: "ph", min_value: 6, max_value: 7, allowed_values: null, explanation: "x" }, is_essential: true },
      texture: { factor: "texture", label: "Soil texture", status: "missing_input", score: null, weight: 1, input: null, detail: "No texture", requirement: { factor: "texture", min_value: null, max_value: null, allowed_values: ["loam"], explanation: "x" }, is_essential: false },
      water: { factor: "water", label: "Water availability", status: "evaluated", score: 0.75, weight: 1, input: "moderate", detail: "ok", requirement: { factor: "water", min_value: null, max_value: null, allowed_values: ["medium"], explanation: "x" }, is_essential: true },
      season: { factor: "season", label: "Season", status: "evaluated", score: 1, weight: 0.8, input: "kharif", detail: "ok", requirement: { factor: "season", min_value: null, max_value: null, allowed_values: ["kharif"], explanation: "x" }, is_essential: false },
      region: { factor: "region", label: "Region", status: "not_required", score: null, weight: 0.6, input: null, detail: "none", requirement: null, is_essential: false },
    },
    context_factors: {},
    reasons: ["because"],
    next_steps: ["do this"],
    risks: [],
    notes: [],
    source: "KB",
    source_url: null,
    date_reviewed: null,
  };
}

import { readFileSync } from "node:fs";
const dump = JSON.parse(readFileSync("../compare_dump.json", "utf-8"));
const candidates = dump.batch.results;
const fakeComparison = dump.compare;

svcMod.cropsApi.compare = async () => fakeComparison;

const container = document.getElementById("root");
const root = createRoot(container);

function report(label) {
  const text = document.body.textContent || "";
  console.log(`\n=== ${label} ===`);
  console.log("rendered length:", text.length);
  console.log("has 'Compare crops':", text.includes("Compare crops"));
  console.log("has 'Ranking':", text.includes("Ranking"));
  console.log(
    "new errors:",
    errors.length ? "\n" + errors.slice(-8).join("\n") : "none"
  );
}

try {
  await act(async () => {
    root.render(
      React.createElement(modalMod.CompareModal, {
        open: true,
        fieldId: 1,
        fieldName: "Test Field",
        onClose() {},
        candidates,
        seed: [],
      })
    );
  });
  report("after opening modal (pick view)");
} catch (e) {
  console.log("RENDER THREW:", e?.stack || e);
}

// Click the Compare button
try {
  const buttons = [...document.querySelectorAll("button")];
  const compareBtn = buttons.find((b) => b.textContent.trim() === "Compare");
  console.log("\nfound Compare button:", !!compareBtn);
  if (compareBtn) {
    await act(async () => {
      compareBtn.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });
    report("after clicking Compare (result view)");
  }
} catch (e) {
  console.log("CLICK THREW:", e?.stack || e);
}

await vite.close();
process.exit(0);
