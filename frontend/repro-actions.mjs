import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body></body></html>", {
  url: "http://localhost/actions",
  pretendToBeVisual: true,
});

globalThis.window = dom.window;
globalThis.document = dom.window.document;
Object.defineProperty(globalThis, "navigator", { value: dom.window.navigator, configurable: true });
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
const { MemoryRouter } = await import("react-router-dom");

const fieldsSvc = await vite.ssrLoadModule("/src/services/fields.ts");
const actionsSvc = await vite.ssrLoadModule("/src/services/actions.ts");
const fieldsHook = await vite.ssrLoadModule("/src/hooks/useFields.tsx");
const pageMod = await vite.ssrLoadModule("/src/pages/ActionPlanner.tsx");

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
fieldsSvc.fieldsApi.list = async () => [field];

const baseAction = (over) => ({
  id: 1,
  action_key: "soil:add_test",
  category: "soil",
  group_key: "do_next",
  title: "Get your soil tested and add the report",
  explanation: "A soil test shows whether your soil is acidic or alkaline.",
  priority: "medium",
  timing: "Best before sowing.",
  reason: "No soil test has been recorded for this field.",
  source: "Soil Intelligence",
  steps: [
    "Collect soil from 5 to 6 different spots.",
    "Mix all the soil together in a clean bucket.",
    "Take about 500 g and give it to the lab.",
  ],
  materials: ["A clean bucket or cloth", "A clean bag for the sample"],
  check_first: ["Take the sample before adding fertiliser."],
  avoid: ["Do not send wet soil."],
  done_when: "The soil test shows in Soil Intelligence with its test date.",
  details: null,
  completed: false,
  completed_at: null,
  created_at: "2026-10-11T00:00:00",
  updated_at: "2026-10-11T00:00:00",
  ...over,
});

const planWith = (actions, extra = {}) => ({
  field_id: 1,
  field_name: "North Field",
  planner_version: "2.0.0",
  has_assessment: true,
  assessment_at: "2026-10-10T00:00:00",
  top_crop: "Ragi",
  updated_at: "2026-10-11T00:00:00",
  actions,
  disclaimer: "This plan is general guidance - not a guarantee.",
  ...extra,
});

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

async function render(children) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(children);
  });
  await flush();
  return { container, root };
}

function withProviders(node) {
  return React.createElement(
    MemoryRouter,
    { initialEntries: ["/actions"] },
    React.createElement(fieldsHook.FieldsProvider, null, node)
  );
}

const weatherRisk = baseAction({
  id: 10,
  action_key: "weather:heavy_rain:global:2026-10-11",
  category: "weather",
  group_key: "do_first",
  title: "Get the field ready before heavy rain",
  explanation: "120 mm is forecast. Heavy rain can flood low spots.",
  priority: "high",
  timing: "2026-10-11",
  reason: "Daily precipitation forecast >= 50 mm",
  source: "Open-Meteo forecast (issued 2026-10-11T06:00)",
  steps: ["Clear the drains so water can flow out."],
  materials: ["A spade or hoe"],
  check_first: ["Where does water stand after heavy rain?"],
  avoid: ["Do not add fertiliser just before heavy rain."],
  done_when: "Water can drain out and the low spots are clear.",
});
const rainCheck = baseAction({
  id: 11,
  action_key: "water:check_irrigation",
  category: "water",
  group_key: "do_next",
  title: "Check if your crop needs watering before you water",
  priority: "low",
  steps: ["Push a finger about 5 cm into the soil."],
});
const doneAction = baseAction({
  id: 20,
  action_key: "crop:confirm:7",
  group_key: "check_later",
  category: "crop",
  title: "Confirm Ragi with your local expert",
  priority: "low",
  completed: true,
  completed_at: "2026-10-11T08:00:00",
});
const checkLater = baseAction({
  id: 30,
  action_key: "information:record_region",
  group_key: "check_later",
  category: "information",
  title: "Add the state or region of your field",
  priority: "low",
});

try {
  // --- Loaded state ----------------------------------------------------------
  actionsSvc.actionsApi.plan = async () =>
    planWith([weatherRisk, rainCheck, baseAction({}), checkLater, doneAction]);

  const { container } = await render(withProviders(React.createElement(pageMod.default)));
  const text = () => container.textContent || "";

  check("renders page title", text().includes("Your Farming Action Plan"));
  check("renders field summary crop", text().includes("Ragi"));
  check("renders Do First group", text().includes("Do First"));
  check("renders Do Next group", text().includes("Do Next"));
  check("renders Check Later group", text().includes("Check Later"));
  check("renders weather risk title", text().includes("Get the field ready before heavy rain"));
  check("renders Completed section", text().includes("Completed"));
  check("shows to-do count", text().includes("4 to do"));
  check("shows done count", text().includes("1 done"));
  check("renders priority label", text().includes("High priority"));
  check("renders when", text().includes("When: 2026-10-11"));
  check("renders disclaimer", text().includes("not a guarantee"));
  check("has a back link to Crop Recommendations", Boolean(container.querySelector('a[href="/crops"]')));

  const checkboxes = [...container.querySelectorAll('[role="checkbox"]')];
  check("renders a checkbox per action", checkboxes.length === 5);
  check("completed action checkbox is checked", checkboxes.some((c) => c.getAttribute("aria-checked") === "true"));

  // --- Expand / collapse detail ---------------------------------------------
  check("steps hidden before expanding", !text().includes("How to do it"));
  const showSteps = [...container.querySelectorAll("button")].find((b) =>
    (b.textContent || "").includes("Show steps")
  );
  await act(async () => {
    showSteps.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  });
  await flush();
  check("expanding reveals the how-to steps", text().includes("How to do it"));
  check("expanding reveals what you need", text().includes("What you need"));
  check("expanding reveals what to avoid", text().includes("What to avoid"));
  check("expanding reveals done condition", text().includes("How you know it is done"));
  check("expanding reveals source", text().includes("Where this comes from"));
  check("expanding reveals forecast issue time", text().includes("issued 2026-10-11T06:00"));

  // --- Toggle completion -----------------------------------------------------
  let patchArgs = null;
  actionsSvc.actionsApi.setCompleted = async (fieldId, actionId, completed) => {
    patchArgs = [fieldId, actionId, completed];
    return baseAction({ id: actionId, completed, completed_at: completed ? "2026-10-11T09:00:00" : null });
  };
  const soilBox = checkboxes.find((c) =>
    c.getAttribute("aria-label")?.includes("soil tested")
  );
  await act(async () => {
    soilBox.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  });
  await flush();
  check("toggle calls setCompleted with the action id", patchArgs && patchArgs[1] === 1 && patchArgs[2] === true);
  check("to-do count updates after completion", text().includes("3 to do"));
  check("done count updates after completion", text().includes("2 done"));

  // --- Empty state -----------------------------------------------------------
  actionsSvc.actionsApi.plan = async () => planWith([]);
  const empty = await render(withProviders(React.createElement(pageMod.default)));
  check("empty state message", (empty.container.textContent || "").includes("No actions needed right now"));

  // --- No-assessment hint ----------------------------------------------------
  actionsSvc.actionsApi.plan = async () =>
    planWith([baseAction({})], { has_assessment: false, top_crop: null, assessment_at: null });
  const noAssessment = await render(withProviders(React.createElement(pageMod.default)));
  check("no-assessment hint shown", (noAssessment.container.textContent || "").includes("No crop assessment has been run"));

  // --- Error state -----------------------------------------------------------
  actionsSvc.actionsApi.plan = async () => {
    throw { response: { data: { detail: "Field not found" } } };
  };
  const errored = await render(withProviders(React.createElement(pageMod.default)));
  check("error alert title", (errored.container.textContent || "").includes("Action plan unavailable"));
  check("error detail surfaced", (errored.container.textContent || "").includes("Field not found"));

  // --- Refresh button --------------------------------------------------------
  actionsSvc.actionsApi.plan = async () => planWith([baseAction({})]);
  let refreshed = 0;
  actionsSvc.actionsApi.refresh = async () => {
    refreshed += 1;
    return planWith([baseAction({ id: 2, action_key: "soil:refresh_test", title: "Get a fresh soil test" })]);
  };
  const fresh = await render(withProviders(React.createElement(pageMod.default)));
  const refreshBtn = [...fresh.container.querySelectorAll("button")].find((b) =>
    (b.textContent || "").includes("Refresh plan")
  );
  await act(async () => {
    refreshBtn.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
  });
  await flush();
  check("refresh calls the API", refreshed === 1);
  check("refresh updates the list", (fresh.container.textContent || "").includes("Get a fresh soil test"));
} catch (e) {
  console.log("THREW:", e?.stack || e);
  failures += 1;
}

console.log(`\n${checks - failures}/${checks} checks passed`);
console.log("new errors:", errors.length ? "\n" + errors.slice(-6).join("\n") : "none");

await vite.close();
process.exit(failures === 0 ? 0 : 1);
