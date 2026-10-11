import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body><div id='root'></div></body></html>", {
  url: "http://localhost/disease",
  pretendToBeVisual: true,
});

globalThis.window = dom.window;
globalThis.document = dom.window.document;
Object.defineProperty(globalThis, "navigator", {
  value: dom.window.navigator,
  configurable: true,
});
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.HTMLInputElement = dom.window.HTMLInputElement;
globalThis.HTMLButtonElement = dom.window.HTMLButtonElement;
globalThis.Node = dom.window.Node;
globalThis.Element = dom.window.Element;
globalThis.Event = dom.window.Event;
globalThis.MouseEvent = dom.window.MouseEvent;
globalThis.KeyboardEvent = dom.window.KeyboardEvent;
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
const vite = await createServer({
  server: { middlewareMode: true },
  appType: "custom",
  logLevel: "error",
});

const React = (await import("react")).default;
const { createRoot } = await import("react-dom/client");
const { act } = await import("react");
const { MemoryRouter } = await import("react-router-dom");

const diseaseSvc = await vite.ssrLoadModule("/src/services/disease.ts");
const catalogueSvc = await vite.ssrLoadModule("/src/services/catalogue.ts");
const pageMod = await vite.ssrLoadModule("/src/pages/CropDisease.tsx");

// --- Fixtures: a small catalogue slice, super-set of what the model supports ---
const CATALOGUE = [
  {
    key: "tomato",
    display_name: "Tomato",
    category: "vegetable",
    category_label: "Vegetables",
    synonyms: ["tamatar", "thakkali"],
    model_supported: true,
  },
  {
    key: "rice",
    display_name: "Rice",
    category: "cereal",
    category_label: "Cereals",
    synonyms: ["paddy", "dhan"],
    model_supported: false,
  },
  {
    key: "horse_gram",
    display_name: "Horse Gram",
    category: "pulse",
    category_label: "Pulses",
    synonyms: ["kollu", "kulthi"],
    model_supported: false,
  },
  {
    key: "turmeric",
    display_name: "Turmeric",
    category: "spice",
    category_label: "Spices",
    synonyms: ["haldi"],
    model_supported: false,
  },
];

const MODEL_CROPS = [
  {
    key: "tomato",
    label: "Tomato",
    diseases: [
      { class_name: "Tomato___healthy", disease_label: "Healthy", is_healthy: true },
      {
        class_name: "Tomato___Late_blight",
        disease_label: "Late blight",
        is_healthy: false,
      },
    ],
  },
];

diseaseSvc.diseaseApi.crops = async () => MODEL_CROPS;
diseaseSvc.diseaseApi.history = async () => [];

// Mimic the backend: case-insensitive substring over name / key / synonyms.
let searchCalls = 0;
let searchImpl = async (query) => {
  const q = String(query || "").trim().toLowerCase();
  return CATALOGUE.filter(
    (crop) =>
      q === "" ||
      crop.display_name.toLowerCase().includes(q) ||
      crop.key.includes(q) ||
      crop.synonyms.some((s) => s.includes(q))
  );
};
catalogueSvc.catalogueApi.search = async (params = {}) => {
  searchCalls += 1;
  const items = await searchImpl(params.q ?? "");
  return {
    items,
    total: items.length,
    limit: params.limit ?? 100,
    offset: params.offset ?? 0,
    catalogue_size: CATALOGUE.length,
    model_supported_count: 1,
    categories: [],
  };
};

const container = document.getElementById("root");
const root = createRoot(container);

let checks = 0;
let failures = 0;
function check(label, condition) {
  checks += 1;
  if (!condition) failures += 1;
  console.log(`${condition ? "PASS" : "FAIL"}: ${label}`);
}

const body = () => document.body.textContent || "";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function flush(ms = 300) {
  await act(async () => {
    await sleep(ms);
  });
}

function input() {
  return document.getElementById("disease-crop");
}

const valueSetter = Object.getOwnPropertyDescriptor(
  dom.window.HTMLInputElement.prototype,
  "value"
).set;

async function type(value) {
  const el = input();
  await act(async () => {
    valueSetter.call(el, value);
    el.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
  });
  await flush();
}

function options() {
  return [...document.querySelectorAll('[role="option"]')];
}

function optionByLabel(label) {
  return options().find((el) => (el.textContent || "").includes(label));
}

async function click(el) {
  await act(async () => {
    el.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true, cancelable: true, button: 0 }));
  });
  await flush();
}

async function key(el, keyName) {
  await act(async () => {
    el.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: keyName, bubbles: true, cancelable: true }));
  });
  await flush(60);
}

const UNSUPPORTED_MESSAGE =
  "This crop is in ANNADATA's crop catalogue, but the current AI disease model has not been trained or verified for it. Disease predictions are unavailable for this crop yet.";

try {
  await act(async () => {
    root.render(
      React.createElement(MemoryRouter, null, React.createElement(pageMod.default))
    );
  });
  await flush();

  // 1. The selector replaces the old native <select>.
  check("combobox input rendered", !!input());
  check(
    "combobox exposes combobox role + list autocomplete",
    input().getAttribute("role") === "combobox" &&
      input().getAttribute("aria-autocomplete") === "list"
  );
  check(
    "no native crop <select> remains",
    ![...document.querySelectorAll("select")].some((s) =>
      (s.getAttribute("aria-label") || "").toLowerCase().includes("crop")
    )
  );

  // 2. Opening shows catalogue matches (not just model crops).
  await act(async () => {
    input().focus();
  });
  await flush();
  check("listbox opens on focus", !!document.querySelector('[role="listbox"]'));
  check("catalogue matches listed", options().length === CATALOGUE.length);
  check(
    "listbox is scroll-capped for long lists",
    (document.querySelector('[role="listbox"]').getAttribute("class") || "").includes("max-h-72")
  );

  // 3. Empty results message.
  await type("zzzzz");
  check("empty search shows a helpful message", body().includes("No crops match that search"));

  // 4. Partial + case-insensitive full name.
  await type("Tom");
  const tomato = optionByLabel("Tomato");
  check("partial case-insensitive match finds Tomato", !!tomato);
  check(
    "model-supported crop is badged as Disease AI",
    !!tomato && (tomato.textContent || "").includes("Disease AI")
  );

  // 5. Synonym search returns a catalogue-only crop with NO Disease AI badge.
  await type("paddy");
  const rice = optionByLabel("Rice");
  check("regional synonym 'paddy' finds Rice", !!rice);
  check("catalogue-only crop is NOT badged as Disease AI", !!rice && !(rice.textContent || "").includes("Disease AI"));

  // 6. Keyboard navigation: Down/Up then Enter selects.
  await type("tom");
  await key(input(), "ArrowDown");
  await key(input(), "ArrowDown");
  await key(input(), "ArrowUp");
  await key(input(), "Enter");
  check("keyboard Enter selects the active option", input().value === "Tomato");
  check(
    "supported crop reveals the conditions the model detects",
    body().includes("Conditions the model can detect on Tomato")
  );
  check("supported crop enables the upload + analyse controls", body().includes("Analyse photo"));

  // 7. Clear selection hides the upload flow again.
  const clearBtn = document.querySelector('[aria-label="Clear selection"]');
  check("clear control is present once a crop is chosen", !!clearBtn);
  await click(clearBtn);
  check("clearing removes the analyse controls", !body().includes("Analyse photo"));
  await key(input(), "Escape");
  check(
    "search hint explains the catalogue is broader than the model",
    body().includes("full catalogue by any common or regional name")
  );

  // 8. Selecting an unsupported catalogue crop shows the exact notice, no upload.
  await type("paddy");
  await click(optionByLabel("Rice"));
  check("choosing a non-model crop shows the exact unsupported notice", body().includes(UNSUPPORTED_MESSAGE));
  check("unsupported crop shows no analyse button", !body().includes("Analyse photo"));
  check("unsupported notice still names the crop", body().includes("Rice"));

  // 9. Synonym for another catalogue-only crop.
  await type("kollu");
  const horseGram = optionByLabel("Horse Gram");
  check("synonym 'kollu' finds Horse Gram", !!horseGram);
  await click(horseGram);
  check("Horse Gram is reported as unsupported", body().includes(UNSUPPORTED_MESSAGE) && body().includes("Horse Gram"));

  // 10. Upper-case synonym still matches.
  await type("HALDI");
  check("upper-case synonym 'HALDI' finds Turmeric", !!optionByLabel("Turmeric"));

  // 11. Catalogue API failure surfaces an error, not a crash.
  searchImpl = async () => {
    throw new Error("network down");
  };
  await type("tomato");
  check(
    "catalogue search errors are shown to the user",
    body().includes("The crop catalogue could not be loaded")
  );
  searchImpl = async (query) => {
    const q = String(query || "").trim().toLowerCase();
    return CATALOGUE.filter(
      (crop) =>
        q === "" ||
        crop.display_name.toLowerCase().includes(q) ||
        crop.key.includes(q) ||
        crop.synonyms.some((s) => s.includes(q))
    );
  };

  check("search endpoint was actually exercised", searchCalls > 5);
  console.log("\nnew errors:", errors.length ? "\n" + errors.slice(-6).join("\n") : "none");
} catch (e) {
  console.log("THREW:", e?.stack || e);
  failures += 1;
}

console.log(`\n${checks - failures}/${checks} checks passed`);
await vite.close();
process.exit(failures === 0 ? 0 : 1);
