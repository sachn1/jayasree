/**
 * demo.js - interactive demo for jayasree, one page with a tab per language.
 *
 * To add a language, add an entry to LANGUAGES below (its data files, the
 * words to suggest, its default word, ...). Nothing else in this file or in
 * index.html is language-specific. A language's data is fetched the first
 * time its tab is opened, not at page load - Hindi's stroke data alone is
 * ~16MB, which a visitor who only wants Malayalam should never download.
 *
 * Each language gets its own writer on its own stage element (a writer
 * clears its container, so two languages can't share one). STROKE_LIBRARY is
 * module-global in index.js, which is fine: scripts don't share cluster keys.
 */

import { createStrokeWriter, STROKE_LIBRARY } from "../js/src/index.js";

// ---------------------------------------------------------------------------
// Languages
// ---------------------------------------------------------------------------

/**
 * @typedef {object} LanguageConfig
 * @property {string} code            URL-hash id (#ml) and <html lang>-style tag.
 * @property {string} tabLabel        Text on the language's tab.
 * @property {string} tagline
 * @property {string} sub
 * @property {string} defaultWord     Traced on first open.
 * @property {(string | {word: string, label: string})[]} words  "Try:" suggestions.
 * @property {string[]} [letters]     If set, shows the letter browser with these.
 * @property {string} speechLang      BCP-47 tag for speech input.
 * @property {string} glyphData       Path to the language's glyph-data file.
 * @property {string} strokeData      Processed strokes - awaited before the first trace.
 * @property {string} strokeDataRaw   Raw strokes - fetched but not awaited (see ensureLanguage).
 * @property {string} [fontStrokes]   The designers' own pen strokes, chosen per letter from fonts. If set, a
 *   "Strokes" switch offers Handwriting or Font-based. Font-based uses only these strokes: a cluster the fonts
 *   do not cover is drawn as an outline, and the page says which, rather than borrowing handwriting.
 * @property {number} strokeWidth     Initial ink thickness (fraction of unitsPerEm).
 * @property {number} [speed]         Writer base pen speed; omit for index.js's default.
 * @property {{word: string, speed: number}} [logo]
 *   Draw the wordmark live for this language (see "Wordmark"). Omit to keep
 *   the page's static, pre-exported Malayalam wordmark.
 */

/** @type {LanguageConfig[]} */
const LANGUAGES = [
  {
    code: "ml",
    tabLabel: "മലയാളം · Malayalam",
    tagline: "Malayalam handwriting, animated stroke by stroke",
    sub:
      "Type any word and watch it be written, as handwriting or with the designers' own pen strokes " +
      "from the Manjari, Chilanka and Nupuram fonts. The letter browser below traces one letter at a time.",
    defaultWord: "നന്ദി",
    words: [
      { word: "അമ്മ", label: "അമ്മ (mother)" },
      { word: "അച്ഛൻ", label: "അച്ഛൻ (father)" },
      { word: "നന്ദി", label: "നന്ദി (thanks)" },
      { word: "മലയാളം", label: "മലയാളം (Malayalam)" },
      { word: "കേരളം", label: "കേരളം (Kerala)" },
      { word: "ഫലം", label: "ഫലം (fruit)" },
      { word: "ഭാഷ", label: "ഭാഷ (language)" },
      { word: "പുസ്തകം", label: "പുസ്തകം (book)" },
      { word: "വിദ്യാലയം", label: "വിദ്യാലയം (school)" },
      { word: "സ്നേഹം", label: "സ്നേഹം (love)" },
      { word: "ക്ഷമിക്കണം", label: "ക്ഷമിക്കണം (sorry)" },
      { word: "ആലയം", label: "ആലയം (abode)" },
      { word: "ജയശ്രീ", label: "ജയശ്രീ (Jayasree)" },
      { word: "ധൃഷ്ടദ്യുമ്നൻ", label: "ധൃഷ്ടദ്യുമ്നൻ" },
      { word: "പ്രദ്യുമ്നൻ", label: "പ്രദ്യുമ്നൻ" },
      { word: "പൃഥ്വി", label: "പൃഥ്വി (earth)" },
      { word: "ബൃഹത്", label: "ബൃഹത് (large)" },
      { word: "മൃഗം", label: "മൃഗം (animal)" },
      { word: "വൃക്ഷം", label: "വൃക്ഷം (tree)" },
    ],
    letters: [
      ...["അ", "ആ", "ഇ", "ഈ", "ഉ", "ഊ", "ഋ", "എ", "ഏ", "ഐ", "ഒ", "ഓ", "ഔ"],
      ...[
        "ക",
        "ഖ",
        "ഗ",
        "ഘ",
        "ങ",
        "ച",
        "ഛ",
        "ജ",
        "ഝ",
        "ഞ",
        "ട",
        "ഠ",
        "ഡ",
        "ഢ",
        "ണ",
      ],
      ...["ത", "ഥ", "ദ", "ധ", "ന", "പ", "ഫ", "ബ", "ഭ", "മ", "യ", "ര", "ല", "വ"],
      ...["ശ", "ഷ", "സ", "ഹ", "ള", "ഴ", "റ"],
      ...["ൺ", "ൻ", "ർ", "ൽ", "ൾ", "ൿ"],
      ...[
        "ക്ഷ",
        "ങ്ക",
        "ഞ്ച",
        "ണ്ട",
        "ന്ത",
        "മ്പ",
        "ത്ത",
        "ല്ല",
        "ള്ള",
        "സ്ത",
        "ശ്ര",
        "ന്ന",
      ],
      ...["ക്ക", "ച്ച", "പ്പ", "ട്ട", "യ്യ", "ദ്ധ", "ച്ഛ"],
    ],
    speechLang: "ml-IN",
    glyphData: "../js/src/glyph-data.json",
    strokeData: "../js/src/stroke-data.json",
    strokeDataRaw: "../js/src/stroke-data.raw.json",
    // Half of index.js's default pen speed (6000, unchanged there); the speed slider reads "1x" at this pace.
    speed: 3000,
    fontStrokes: "../js/src/stroke-data.font.json",
    strokeWidth: 0.022,
  },
  {
    code: "hi",
    tabLabel: "हिन्दी · Hindi",
    tagline: "Devanagari (Hindi) handwriting, animated stroke by stroke",
    sub:
      "All of Hindi's strokes are recorded and cleaned against the font. " +
      "The letter browser below traces one letter at a time.",
    defaultWord: "भारत",
    words: [
      { word: "भारत", label: "भारत (India)" },
      { word: "कमल", label: "कमल (lotus)" },
      { word: "गणेश", label: "गणेश (Ganesha)" },
      { word: "राम", label: "राम (Ram)" },
    ],
    letters: [
      ...["अ", "आ", "इ", "ई", "उ", "ऊ", "ऋ", "ए", "ऐ", "ओ", "औ"],
      ...["क", "ख", "ग", "घ", "ङ", "च", "छ", "ज", "झ", "ञ", "ट", "ठ", "ड", "ढ"],
      ...["ण", "त", "थ", "द", "ध", "न", "प", "फ", "ब", "भ", "म", "य", "र", "ल"],
      ...["व", "श", "ष", "स", "ह"],
    ],
    speechLang: "hi-IN",
    glyphData: "../js/src/glyph-data.hi.json",
    strokeData: "../js/src/stroke-data.hi.json",
    strokeDataRaw: "../js/src/stroke-data.hi.raw.json",
    // Slightly thicker than index.js's default (0.022, unchanged there), to suit
    // Noto Sans Devanagari's heavier ink.
    strokeWidth: 0.03,
    // An eighth of index.js's default pen speed (6000, unchanged there):
    // some strokes were too fast to watch, especially single letters. The
    // speed slider reads "1x" at this pace.
    speed: 750,
    // "Jayasree" in Devanagari: ज य श्री.
    logo: { word: "जयश्री", speed: 42000 },
  },
];

// Malayalam's ജയശ്രീ wordmark is a plain <img src="jayasree.svg"> in the HTML
// - the same pre-exported, self-animating (SMIL, no JS) asset the homepage
// uses. See "Wordmark" below for how other languages get theirs.

// ---------------------------------------------------------------------------
// DOM
// ---------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);
const tabsEl = $("langTabs");
const taglineEl = $("tagline");
const subEl = $("sub");
const form = $("traceForm");
const input = $("wordInput");
const status = $("status");
const btn = $("traceBtn");
const stageHost = $("stage");
const logoImg = $("logo-stage");
const logoLive = $("logo-live");
const wordChips = $("wordChips");
const letterBrowser = $("letterBrowser");
const letterChips = $("letterChips");
const speedCtl = $("speedCtl");
const speedVal = $("speedVal");
const thicknessCtl = $("thicknessCtl");
const thicknessVal = $("thicknessVal");
const countCtl = $("countCtl");
const strokeLabel = $("strokeLabel");
const strokeCtl = $("strokeCtl");
const strokeNote = $("strokeNote");
const strokeCoverage = $("strokeCoverage");

// ---------------------------------------------------------------------------
// Per-language state
// ---------------------------------------------------------------------------

/**
 * @typedef {object} LanguageState
 * @property {LanguageConfig} config
 * @property {HTMLElement} stageEl
 * @property {Promise<object> | null} glyphReady  Glyph data, set once its fetch starts.
 * @property {Promise<void> | null} ready  Everything incl. strokes, set once loading starts.
 * @property {ReturnType<typeof createStrokeWriter> | null} logoWriter
 * @property {boolean} logoDrawn
 * @property {object | null} glyphData
 * @property {ReturnType<typeof createStrokeWriter> | null} writer
 * @property {number} strokeWidth   Current thickness for this language.
 * @property {string} word          Last word in the input for this language.
 * @property {"handwriting" | "font"} strokeMode  Which stroke set a language with `fontStrokes` is showing.
 * @property {{hand: object, font: object} | null} sets  Both stroke sets, once loaded (only with `fontStrokes`).
 */

/** @type {Map<string, LanguageState>} */
const states = new Map();
for (const config of LANGUAGES) {
  const stageEl = document.createElement("div");
  stageEl.className = "lang-stage";
  stageEl.hidden = true;
  stageHost.appendChild(stageEl);
  states.set(config.code, {
    config,
    stageEl,
    glyphReady: null,
    ready: null,
    glyphData: null,
    logoWriter: null,
    logoDrawn: false,
    writer: null,
    strokeWidth: config.strokeWidth,
    word: config.defaultWord,
    strokeMode: "handwriting",
    sets: null,
  });
}

/** @type {LanguageState} */
let active = states.get(LANGUAGES[0].code);

/** Build a writer for a language at its current thickness. */
function makeWriter(state) {
  const options = {
    glyphData: state.glyphData,
    strokeWidth: state.strokeWidth,
  };
  if (state.config.speed !== undefined) options.speed = state.config.speed;
  // A language with two stroke sets shows only what the chosen set has: nothing is traced in their place.
  if (state.config.fontStrokes) options.outlineFallback = false;
  return createStrokeWriter(state.stageEl, options);
}

/**
 * Fetch a language's glyph data and create its writer, once. Cheap enough
 * (a few MB) that the wordmark can draw from it without waiting for strokes.
 *
 * @param {LanguageState} state
 * @returns {Promise<object>}
 */
function ensureGlyphData(state) {
  state.glyphReady ??= (async () => {
    const { config } = state;
    const resp = await fetch(`${config.glyphData}?v=${Date.now()}`);
    if (!resp.ok) throw new Error(`Failed to load ${config.glyphData}: ${resp.status}`);
    state.glyphData = await resp.json();
    state.writer = makeWriter(state);
    return state.glyphData;
  })().catch((err) => {
    state.glyphReady = null; // allow a retry the next time the tab is opened
    throw err;
  });
  return state.glyphReady;
}

/**
 * Load everything a language needs to trace words: glyph data, then strokes.
 *
 * The processed stroke data is awaited - it alone covers every suggested
 * word and the default word, so the first trace can start as soon as it's
 * ready. The raw file (hand-recorded strokes not yet through the pipeline) is
 * fetched but deliberately not awaited: loadStrokes() never overwrites a
 * cluster already in STROKE_LIBRARY, so it only fills coverage the processed
 * file lacks, and nothing shown on load depends on it.
 *
 * @param {LanguageState} state
 * @returns {Promise<void>}
 */
function ensureLanguage(state) {
  state.ready ??= (async () => {
    await ensureGlyphData(state);
    const { config } = state;
    if (config.fontStrokes) {
      state.sets = await loadStrokeSets(config);
      applyStrokeMode(state);
      return;
    }
    await state.writer.loadStrokes(`${config.strokeData}?v=${Date.now()}`);
    state.writer.loadStrokes(`${config.strokeDataRaw}?v=${Date.now()}`);
  })().catch((err) => {
    state.ready = null;
    throw err;
  });
  return state.ready;
}

/**
 * Fetch a language's handwriting and font-based stroke sets.
 *
 * Handwriting is the processed file with the raw file filling what it lacks, the way the runtime merges them.
 *
 * @param {LanguageConfig} config
 * @returns {Promise<{hand: object, font: object}>}
 */
async function loadStrokeSets(config) {
  const get = async (url) => {
    const resp = await fetch(`${url}?v=${Date.now()}`);
    if (!resp.ok) throw new Error(`Failed to load ${url}: ${resp.status}`);
    return resp.json();
  };
  const [processed, raw, font] = await Promise.all([
    get(config.strokeData),
    get(config.strokeDataRaw),
    get(config.fontStrokes),
  ]);
  const hand = {};
  for (const [cluster, entry] of Object.entries({ ...raw, ...processed })) {
    if (!cluster.startsWith("_")) hand[cluster] = entry;
  }
  return { hand, font };
}

/**
 * Put the language's chosen stroke set into the shared STROKE_LIBRARY.
 *
 * Font-based means only the designers' strokes: no handwriting is mixed in, and the engine builds combinations
 * (a letter with a vowel sign, say) from the font strokes. The library is shared by all languages, so only
 * Malayalam's clusters are cleared.
 * All of them are cleared, not just the two sets' keys: the engine caches every cluster it composes (a letter
 * with a vowel sign, say) back into the library, and a cluster composed from the other set's strokes would
 * otherwise stay.
 *
 * @param {LanguageState} state
 */
function applyStrokeMode(state) {
  const { hand, font } = state.sets;
  const isMalayalam = (cluster) => /[\u0d00-\u0d7f]/.test(cluster);
  for (const cluster of Object.keys(STROKE_LIBRARY)) {
    if (isMalayalam(cluster)) delete STROKE_LIBRARY[cluster];
  }
  Object.assign(STROKE_LIBRARY, state.strokeMode === "font" ? font : hand);
}

// ---------------------------------------------------------------------------
// Wordmark
// ---------------------------------------------------------------------------

// Malayalam shows a pre-exported SVG. For a language with a `logo` config we
// draw the equivalent live, the way demo/logo-preview.html does: the library's
// outline-only mode draws the ink outline of the word, then the purple fill is
// revealed left to right through a clip rect. It only needs the language's
// glyph data (already fetched for the tab), not its strokes.

/** Bumped to abandon an in-flight reveal when the tab changes or replays. */
let logoRun = 0;

/**
 * Show the right wordmark for the active language and (re)play it.
 *
 * @param {LanguageState} state
 */
async function showLogo(state) {
  const live = state.config.logo;
  const imgWasHidden = logoImg.hidden;
  logoImg.hidden = Boolean(live);
  logoLive.hidden = !live;
  // A self-animating SVG shown again after display:none doesn't reliably
  // restart; reloading it does (the homepage replays its logo the same way).
  if (!live && imgWasHidden) logoImg.src = `jayasree.svg?${Date.now()}`;
  logoRun++;
  for (const s of states.values()) s.logoWriter?.cancel();
  if (!live) return;

  const run = logoRun;
  try {
    await ensureGlyphData(state);
  } catch {
    return; // the trace area already reports a load failure
  }
  if (run !== logoRun) return;

  state.logoWriter ??= createStrokeWriter(logoLive, {
    glyphData: state.glyphData,
    speed: live.speed,
    outlineOnly: true,
  });
  const replay = state.logoDrawn;
  state.logoDrawn = true;
  // play()/replay() build the SVG synchronously before their first await, so
  // the ghost layer exists right after the call - same assumption as
  // logo-preview.html.
  const drawn = replay ? state.logoWriter.replay() : state.logoWriter.play(live.word);
  const svg = logoLive.querySelector("svg");
  const ghost = svg?.querySelector(".ms-ghost");
  if (!ghost) return;

  const bbox = ghost.getBBox();
  const ns = "http://www.w3.org/2000/svg";
  const clip = document.createElementNS(ns, "clipPath");
  clip.id = "logo-reveal-clip";
  const rect = document.createElementNS(ns, "rect");
  rect.setAttribute("x", String(bbox.x));
  rect.setAttribute("y", String(bbox.y - 4));
  rect.setAttribute("width", "0");
  rect.setAttribute("height", String(bbox.height + 8));
  clip.appendChild(rect);
  svg.appendChild(clip);
  ghost.setAttribute("clip-path", "url(#logo-reveal-clip)");

  await drawn;
  if (run !== logoRun) return;
  const duration = 650;
  const start = performance.now();
  const step = (now) => {
    if (run !== logoRun) return;
    const t = Math.min(1, (now - start) / duration);
    rect.setAttribute("width", String(bbox.width * (1 - (1 - t) ** 3)));
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

logoLive.addEventListener("click", () => showLogo(active));

// ---------------------------------------------------------------------------
// Controls - speed / thickness / repeat
// ---------------------------------------------------------------------------

/** Current per-play options from the speed slider + repeat select. */
function playOptions() {
  return { speed: Number(speedCtl.value), count: Number(countCtl.value) };
}

speedCtl.addEventListener("input", () => {
  speedVal.textContent = `${Number(speedCtl.value)}×`;
});
// `change` (not `input`) so it fires once per adjustment, not per pixel of
// slider drag - same reasoning as thicknessCtl's `change` listener below.
speedCtl.addEventListener("change", () => traceWord(input.value));

/**
 * Rough human label for a strokeWidth fraction, so the slider reads as
 * "thin/medium/thick" instead of an opaque number like 0.022.
 *
 * @param {number} v
 * @returns {string}
 */
function thicknessLabel(v) {
  if (v < 0.018) return "thin";
  if (v < 0.03) return "medium";
  if (v < 0.042) return "thick";
  return "marker";
}

function showThickness(value) {
  thicknessCtl.value = String(value);
  thicknessVal.textContent = thicknessLabel(Number(thicknessCtl.value));
}

// strokeWidth is fixed at writer creation (it sizes every stroke element the
// stage builds), so changing it means a fresh writer on the same stage -
// cheap, since the parsed glyphData object is shared and STROKE_LIBRARY is
// module-global. `change` (not `input`) so it fires once per adjustment.
thicknessCtl.addEventListener("input", () => {
  thicknessVal.textContent = thicknessLabel(Number(thicknessCtl.value));
});
thicknessCtl.addEventListener("change", () => {
  const state = active;
  if (!state.writer) return;
  state.writer.cancel();
  state.strokeWidth = Number(thicknessCtl.value);
  state.writer = makeWriter(state);
  traceWord(input.value);
});

/**
 * In font-based mode, say whether every cluster of the word came from the fonts, and name those that did not.
 *
 * @param {LanguageState} state
 * @param {string} word
 */
function showCoverage(state, word) {
  const font = state.strokeMode === "font";
  strokeCoverage.hidden = !state.config.fontStrokes;
  if (!state.config.fontStrokes) return;
  // the writer resolves which clusters lack strokes while it builds the stage, just after play() starts
  setTimeout(() => {
    if (state !== active || state.word !== word) return;
    const missing = [...new Set(state.writer.getFallbackClusters())];
    strokeCoverage.classList.toggle("partial", missing.length > 0);
    strokeCoverage.textContent = missing.length
      ? `No ${font ? "font" : "handwriting"} strokes for these, so they are left blank: ${missing.join("  ")}`
      : font
        ? "Every letter here is drawn from the fonts' strokes."
        : "Every letter here is drawn from the recorded handwriting.";
  }, 50);
}

/** Show the Strokes switch (and its note) for a language that has font-based strokes. */
function showStrokeControl(state) {
  const has = Boolean(state.config.fontStrokes);
  strokeLabel.hidden = !has;
  strokeNote.hidden = !has;
  strokeCoverage.hidden = true;
  if (!has) return;
  strokeCtl.value = state.strokeMode;
  strokeNote.textContent =
    state.strokeMode === "font"
      ? "Font-based: only the pen strokes drawn by the designers of the Manjari, Chilanka and Nupuram fonts " +
        "(Swathanthra Malayalam Computing, SIL Open Font License), chosen letter by letter. No handwriting " +
        "is mixed in, and nothing is traced in place of a missing stroke."
      : "Handwriting: strokes recorded by hand, one letter at a time.";
}

strokeCtl.addEventListener("change", () => {
  const state = active;
  if (!state.sets) return;
  state.strokeMode = strokeCtl.value;
  applyStrokeMode(state);
  showStrokeControl(state);
  state.writer?.cancel();
  state.writer = makeWriter(state);
  traceWord(input.value);
});

// ---------------------------------------------------------------------------
// Trace
// ---------------------------------------------------------------------------

/**
 * Trace the given word with the active language's writer and handle errors.
 *
 * @param {string} word
 */
async function traceWord(word) {
  word = word.trim();
  if (!word) return;
  const state = active;
  state.word = word;
  status.textContent = "";
  btn.disabled = true;
  try {
    await ensureLanguage(state);
    if (state !== active) return; // the user switched tabs while this loaded
    const playing = state.writer.play(word, playOptions());
    showCoverage(state, word);
    await playing;
  } catch (err) {
    if (state === active) status.textContent = err.message;
  } finally {
    if (state === active) btn.disabled = false;
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  traceWord(input.value);
});

$("replay").addEventListener("click", () =>
  active.writer?.replay(playOptions()),
);

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

/** (Re)build a row of suggestion-chip buttons, optionally led by a text label. */
function fillChips(container, items, prefix = "") {
  container.replaceChildren(
    ...(prefix ? [document.createTextNode(prefix)] : []),
  );
  for (const item of items) {
    const { word, label } =
      typeof item === "string" ? { word: item, label: item } : item;
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.word = word;
    b.textContent = label;
    container.appendChild(b);
  }
}

// One delegated listener per chip row; the rows are rebuilt on every switch.
for (const row of [wordChips, letterChips]) {
  row.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-word]");
    if (!b) return;
    input.value = b.dataset.word;
    traceWord(input.value);
  });
}

for (const config of LANGUAGES) {
  const tab = document.createElement("button");
  tab.type = "button";
  tab.role = "tab";
  tab.id = `tab-${config.code}`;
  tab.dataset.lang = config.code;
  tab.textContent = config.tabLabel;
  tab.addEventListener("click", () => activate(config.code));
  tabsEl.appendChild(tab);
}

/**
 * Switch the page to a language: swap the tab, text, chips, stage and
 * controls, then trace that language's last word.
 *
 * @param {string} code
 */
function activate(code) {
  const state = states.get(code);
  if (!state) return;
  active.writer?.cancel();
  active = state;
  const { config } = state;

  for (const tab of tabsEl.children) {
    const selected = tab.dataset.lang === code;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
  }
  for (const s of states.values()) s.stageEl.hidden = s !== state;

  taglineEl.textContent = config.tagline;
  subEl.textContent = config.sub;
  input.lang = config.code;
  input.value = state.word;
  fillChips(wordChips, config.words, "Try: \u00a0");
  letterBrowser.hidden = !config.letters;
  if (config.letters) fillChips(letterChips, config.letters);
  showThickness(state.strokeWidth);
  showStrokeControl(state);
  status.textContent = "";

  // Keep the URL shareable without adding a history entry per tab click.
  try {
    window.history.replaceState(null, "", `#${code}`);
  } catch {
    /* file:// or sandboxed - the hash is a convenience only */
  }
  showLogo(state);
  traceWord(state.word);
}

/** The language named by the URL hash, else the first (Malayalam). */
function languageFromHash() {
  const code = window.location.hash.slice(1);
  return states.has(code) ? code : LANGUAGES[0].code;
}

window.addEventListener("hashchange", () => {
  const code = languageFromHash();
  if (code !== active.config.code) activate(code);
});

// ---------------------------------------------------------------------------
// Speech input - say a word instead of typing it
// ---------------------------------------------------------------------------

// Chrome/Edge/Safari only expose this as the prefixed webkitSpeechRecognition;
// Firefox doesn't implement it at all. The button stays `hidden` (see
// index.html) on any browser where neither exists, rather than showing a
// control that would just fail on click.
const SpeechRecognitionAPI =
  window.SpeechRecognition ?? window.webkitSpeechRecognition;
const speakBtn = $("speakBtn");

if (SpeechRecognitionAPI && speakBtn) {
  speakBtn.hidden = false;

  /** The in-progress recognition session, or null when idle. */
  let recognition = null;

  speakBtn.addEventListener("click", () => {
    // Second click while listening cancels instead of starting a new
    // session - onend below (fired by both a real result and abort())
    // handles resetting the button either way.
    if (recognition) {
      recognition.abort();
      return;
    }

    recognition = new SpeechRecognitionAPI();
    recognition.lang = active.config.speechLang;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    speakBtn.title = "Listening… click to stop";
    speakBtn.setAttribute("aria-label", "Listening… click to stop");
    speakBtn.classList.add("listening");
    status.textContent = "";

    recognition.addEventListener("result", (e) => {
      const transcript = e.results[0][0].transcript.trim();
      if (transcript) {
        input.value = transcript;
        traceWord(transcript);
      }
    });

    recognition.addEventListener("error", (e) => {
      // "aborted" is our own abort() call above, not a real failure - no
      // message needed for that one.
      if (e.error === "aborted") return;
      status.textContent =
        e.error === "not-allowed" || e.error === "service-not-allowed"
          ? "Microphone access denied - allow it in the browser to use speech input."
          : e.error === "no-speech"
            ? "Didn't catch that - try again."
            : "Speech recognition failed - try again.";
    });

    recognition.addEventListener("end", () => {
      recognition = null;
      speakBtn.title = "Speak a word";
      speakBtn.setAttribute("aria-label", "Speak a word");
      speakBtn.classList.remove("listening");
    });

    recognition.start();
  });
}

// ---------------------------------------------------------------------------
// Stroke library drag-and-drop
// ---------------------------------------------------------------------------

const libDrop = $("lib-drop");
const libFile = $("lib-file");
const libStatus = $("lib-status");

/**
 * Merge a stroke-data JSON file into the active STROKE_LIBRARY and replay.
 *
 * @param {File} file
 */
function loadLibrary(file) {
  const reader = new FileReader();
  reader.onload = (ev) => {
    try {
      const data = JSON.parse(ev.target.result);
      const count = Object.keys(data).length;
      Object.assign(STROKE_LIBRARY, data);
      libStatus.textContent = `✓ Loaded ${count} glyph${count !== 1 ? "s" : ""} - replay to see authored strokes`;
      libDrop.style.borderColor = "#6d28d9";
      active.writer?.replay();
    } catch {
      libStatus.textContent =
        "Could not parse JSON - is this a stroke-data export?";
    }
  };
  reader.readAsText(file);
}

libDrop.addEventListener("click", () => libFile.click());
libFile.addEventListener(
  "change",
  () => libFile.files[0] && loadLibrary(libFile.files[0]),
);
libDrop.addEventListener("dragover", (e) => {
  e.preventDefault();
  libDrop.style.borderColor = "#6d28d9";
});
libDrop.addEventListener("dragleave", () => {
  libDrop.style.borderColor = "#c4b5e8";
});
libDrop.addEventListener("drop", (e) => {
  e.preventDefault();
  libDrop.style.borderColor = "#c4b5e8";
  if (e.dataTransfer.files[0]) loadLibrary(e.dataTransfer.files[0]);
});

// Open the language named in the URL (default: Malayalam) and trace its
// default word.
activate(languageFromHash());
