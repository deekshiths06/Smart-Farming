import { JSDOM } from "jsdom";
import { readFileSync } from "node:fs";

const dom = new JSDOM("<!doctype html><html><body><div id='root'></div></body></html>", {
  url: "http://localhost/crops",
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
globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
globalThis.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} };
globalThis.requestAnimationFrame = (cb) => setTimeout(() => cb(Date.now()), 0);
globalThis.cancelAnimationFrame = (id) => clearTimeout(id);
dom.window.matchMedia =
  dom.window.matchMedia ||
  (() => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}, dispatchEvent() {} }));
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
const vite = await createServer({ server: { middlewareMode: true }, appType: "custom", logLevel: "error" });

const React = (await import("react")).default;
const { createRoot } = await import("react-dom/client");
const { act } = await import("react");
const { MemoryRouter, Routes, Route } = await import("react-router-dom");

const dump = JSON.parse(readFileSync("../compare_dump.json", "utf-8"));

const fieldsMod = await vite.ssrLoadModule("/src/services/fields.ts");
const cropsSvc = await vite.ssrLoadModule("/src/services/crops.ts");
const actionsSvc = await vite.ssrLoadModule("/src/services/actions.ts");
const fieldsHook = await vite.ssrLoadModule("/src/hooks/useFields.tsx");
const pageMod = await vite.ssrLoadModule("/src/pages/CropRecommendations.tsx");
const plannerMod = await vite.ssrLoadModule("/src/pages/ActionPlanner.tsx");

const field = {
  id: 1,
  user_id: 1,
  field_name: "North Field",
  latitude: 12.9716,
  longitude: 77.5946,
  location_accuracy: 18,
  location_confirmed: true,
  address: null,
  locality: null,
  sub_district: null,
  district: "Bengaluru",
  state: "Karnataka",
  country: "India",
  boundary: null,
  area: 2.5,
  area_unit: "acre",
  area_source: "manual",
  water_source: "rain_fed",
  water_availability: "seasonal",
  soil_status: "not_provided",
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};

let generateCount = 0;
fieldsMod.fieldsApi.list = async () => [field];
cropsSvc.cropsApi.history = async () => [];
cropsSvc.cropsApi.generate = async () => {
  generateCount += 1;
  return dump.batch;
};
cropsSvc.cropsApi.compare = async () => dump.compare;
cropsSvc.cropsApi.batch = async () => [];

const mockPlan = {
  field_id: 1,
  field_name: "North Field",
  planner_version: "2.0.0",
  has_assessment: true,
  assessment_at: "2026-10-10T00:00:00",
  top_crop: "Ragi",
  updated_at: "2026-10-11T00:00:00",
  disclaimer: "This plan is general guidance - not a guarantee.",
  actions: [
    {
      id: 10,
      action_key: "weather:heavy_rain:global:2026-10-11",
      category: "weather",
      group_key: "do_first",
      title: "Get the field ready before heavy rain",
      explanation: "120 mm is forecast. Check drainage before the rain.",
      priority: "high",
      timing: "2026-10-11",
      reason: "Daily precipitation forecast >= 50 mm",
      source: "Open-Meteo forecast (issued 2026-10-11T06:00)",
      steps: ["Clear the drains so water can flow out."],
      materials: ["A spade or hoe"],
      check_first: ["Where does water stand after heavy rain?"],
      avoid: ["Do not add fertiliser just before heavy rain."],
      done_when: "Water can drain out and the low spots are clear.",
      details: null,
      completed: false,
      completed_at: null,
      created_at: "2026-10-11T00:00:00",
      updated_at: "2026-10-11T00:00:00",
    },
  ],
};
actionsSvc.actionsApi.plan = async () => mockPlan;
actionsSvc.actionsApi.refresh = async () => mockPlan;
actionsSvc.actionsApi.setCompleted = async (_fieldId, actionId, completed) => ({
  ...mockPlan.actions[0],
  id: actionId,
  completed,
});

const container = document.getElementById("root");
const root = createRoot(container);

let checks = 0;
let failures = 0;
function check(label, condition) {
  checks += 1;
  if (!condition) failures += 1;
  console.log(`${condition ? "PASS" : "FAIL"}: ${label}`);
}

async function flush() {
  await act(async () => {
    await new Promise((r) => setTimeout(r, 40));
  });
}

try {
  await act(async () => {
    root.render(
      React.createElement(
        MemoryRouter,
        { initialEntries: ["/crops"] },
        React.createElement(
          fieldsHook.FieldsProvider,
          null,
          React.createElement(
            Routes,
            null,
            React.createElement(Route, { path: "/crops", element: React.createElement(pageMod.default) }),
            React.createElement(Route, { path: "/actions", element: React.createElement(plannerMod.default) })
          )
        )
      )
    );
  });
  await flush();

  const body = () => document.body.textContent || "";

  // Generation is deliberately user-initiated on first load: click it.
  const runBtn = [...document.querySelectorAll("button")].find((b) =>
    (b.textContent || "").includes("Run recommendations now")
  );
  check("'Run recommendations now' button present", !!runBtn);
  if (runBtn) {
    await act(async () => {
      runBtn.dispatchEvent(
        new dom.window.MouseEvent("click", { bubbles: true, cancelable: true, button: 0 })
      );
    });
    await flush();
  }

  check(
    "crop page renders the grouped discovery list",
    body().includes("Every crop, grouped by fit")
  );
  check("selected location with coordinates is shown", body().includes("12.972, 77.595"));
  check("assessment date is shown", body().includes("Assessed "));
  check("the location forecast is displayed", body().includes("forecast scored for this location"));

  // Match-category groups and their per-group counts.
  check("Good match group present", body().includes("Good match"));
  check("Important limitations group present", body().includes("Important limitations"));
  check("group counts shown", body().includes("(20)") && body().includes("(9)"));
  check("overall tally shown", body().includes("29 of 29 shown"));
  check("suitable / not-recommended tallies shown", body().includes("20 potentially suitable") && body().includes("9 not recommended"));

  // Search control + category + season filters.
  const searchInput = document.getElementById("crop-search");
  const categorySelect = [...document.querySelectorAll("select")].find((s) =>
    s.getAttribute("aria-label") === "Filter by crop category"
  );
  const seasonSelect = [...document.querySelectorAll("select")].find((s) =>
    s.getAttribute("aria-label") === "Filter by season"
  );
  check("search box rendered", !!searchInput);
  check("category filter rendered", !!(categorySelect && [...categorySelect.options].some((o) => o.value === "millet")));
  check("season filter rendered", !!(seasonSelect && [...seasonSelect.options].some((o) => o.value === "rabi")));

  // "Show more" appears because the Good match group has 20 crops (> GROUP_LIMIT 6).
  const showAll = [...document.querySelectorAll("button")].find((b) =>
    (b.textContent || "").includes("Show all 20 in Good match")
  );
  check("'Show all 20 in Good match' button present", !!showAll);

  // Search narrows the discovery list.
  if (searchInput) {
    const setter = Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, "value").set;
    await act(async () => {
      setter.call(searchInput, "Rice");
      searchInput.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
    });
    await flush();
    check("search filter narrows the results", body().includes("1 of 29 shown"));
    check("matching crop remains visible", body().includes("Rice"));
    await act(async () => {
      setter.call(searchInput, "");
      searchInput.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
    });
    await flush();
  }

  // Category filter narrows the discovery list.
  if (categorySelect) {
    await act(async () => {
      categorySelect.value = "millet";
      categorySelect.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
    });
    await flush();
    check("category filter narrows the results", body().includes(" of 29 shown") && !body().includes("29 of 29 shown"));
    await act(async () => {
      categorySelect.value = "all";
      categorySelect.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
    });
    await flush();
  }

  if (showAll) {
    const latest = [...document.querySelectorAll("button")].find((b) =>
      (b.textContent || "").includes("Show all 20 in Good match")
    );
    await act(async () => {
      latest.dispatchEvent(
        new dom.window.MouseEvent("click", { bubbles: true, cancelable: true, button: 0 })
      );
    });
    await flush();
    check("expanding a group hides its 'Show all' button", ![...document.querySelectorAll("button")].some((b) => (b.textContent || "").includes("Show all 20 in Good match")));
  }

  const plannerLinks = [...document.querySelectorAll('a[href="/actions"]')];
  check("exactly one Action Planner link", plannerLinks.length === 1);
  check(
    "exactly one 'View Action Planner' text",
    (body().match(/View Action Planner/g) || []).length === 1
  );
  check(
    "the link has exactly one arrow",
    plannerLinks.length === 1 && plannerLinks[0].querySelectorAll("svg").length === 1
  );
  check("planner is NOT embedded on the crop page", !body().includes("Your Farming Action Plan"));

  // Clicking the link opens the dedicated planner page.
  await act(async () => {
    plannerLinks[0].dispatchEvent(
      new dom.window.MouseEvent("click", { bubbles: true, cancelable: true, button: 0 })
    );
  });
  await flush();
  check("clicking the link opens the Action Planner page", body().includes("Your Farming Action Plan"));
  check("planner page shows the action", body().includes("Get the field ready before heavy rain"));
  check("generate was not triggered by navigation", generateCount === 1);

  console.log("\nnew errors:", errors.length ? "\n" + errors.slice(-6).join("\n") : "none");
} catch (e) {
  console.log("THREW:", e?.stack || e);
  failures += 1;
}

console.log(`\n${checks - failures}/${checks} checks passed`);
await vite.close();
process.exit(failures === 0 ? 0 : 1);
