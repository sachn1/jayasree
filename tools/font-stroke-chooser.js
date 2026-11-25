// Font stroke chooser: for each letter, pick which designer strokes make up its font-based version.
// Every stroke of every font is its own card, shown alone on the Manjari outline; clicking a card adds it to (or
// removes it from) the letter. Choices are kept in this browser and exported as tools/font-stroke-choices.ml.json:
// {letter: ["Manjari:2", "Manjari:1~"]} - a stroke is "<option>:<number, from 1>", a trailing ~ means it is drawn
// the other way round, and the list is the order the letter is drawn in: the order you click the cards, which
// "Your letter" lets you change.
(function () {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  const PALETTE = [
    "#d62828",
    "#1d5fd6",
    "#1b9a4a",
    "#e08a00",
    "#8f3fbf",
    "#0a9aa8",
  ];
  const FONT_ORDER = ["Manjari", "Chilanka", "Nupuram"]; // the order of the cards
  const STORAGE_KEY = "jayasree-font-stroke-choices-v2";
  const UNITS_PER_SECOND = 1100;
  const MIN_STROKE_MS = 250;
  const PEN_LIFT_MS = 160;
  const PAD = 60;

  /** A font's name, without the " (part n)" of one group of its strokes. */
  const fontOf = (key) => key.replace(/ \(part \d+\)$/, "");
  /** A saved stroke id with a trailing ~ is drawn from its end to its start. */
  const isRev = (id) => id.endsWith("~");
  const baseId = (id) => id.replace(/~$/, "");

  const $ = (id) => document.getElementById(id);
  const state = {
    glyphs: null,
    candidates: null,
    shipped: null,
    fonts: [],
    letters: [],
    shown: [],
    index: 0,
    choices: {},
    token: 0,
  };

  // ── Loading ─────────────────────────────────────────────────────────

  async function fetchJson(url, optional) {
    const res = await fetch(url);
    if (!res.ok) {
      if (optional) return null;
      throw new Error(`${url}: HTTP ${res.status}`);
    }
    return res.json();
  }

  function useData(glyphs, candidates, shipped, saved) {
    state.glyphs = glyphs;
    state.candidates = candidates;
    state.shipped = shipped;
    const present = new Set(
      Object.values(candidates).flatMap((v) => Object.keys(v).map(fontOf)),
    );
    state.fonts = FONT_ORDER.filter((f) => present.has(f)).concat(
      [...present].filter((f) => !FONT_ORDER.includes(f)),
    );
    const known = new Set([
      ...Object.keys(glyphs.clusters),
      ...Object.keys(glyphs.marks || {}),
    ]);
    state.letters = [...known].filter((c) => candidates[c]);
    state.choices = { ...(saved || {}), ...loadChoices() };
    $("picker").hidden = true;
    $("error").hidden = true;
    renderBulk();
    applyFilter();
  }

  async function load() {
    try {
      const [glyphs, candidates, shipped, saved] = await Promise.all([
        fetchJson("../js/src/glyph-data.json"),
        fetchJson("../js/src/font-strokes.ml.json"),
        fetchJson("../js/src/stroke-data.json", true),
        fetchJson("font-stroke-choices.ml.json", true),
      ]);
      useData(glyphs, candidates, shipped, saved);
    } catch (err) {
      // Opened straight from disk, where fetch is blocked: ask for the files instead.
      $("error").textContent = `Could not load the data (${err.message}).`;
      $("error").hidden = false;
      $("picker").hidden = false;
    }
  }

  async function loadPicked(files) {
    const found = {};
    for (const f of files) {
      let json;
      try {
        json = JSON.parse(await f.text());
      } catch {
        $("error").textContent = `${f.name} is not valid JSON.`;
        $("error").hidden = false;
        return;
      }
      if (f.name === "glyph-data.json") found.glyphs = json;
      else if (f.name === "font-strokes.ml.json") found.candidates = json;
      else if (f.name === "stroke-data.json") found.shipped = json;
      else if (f.name === "font-stroke-choices.ml.json") found.saved = json;
    }
    if (!found.glyphs || !found.candidates) {
      $("error").textContent =
        "Pick glyph-data.json and font-strokes.ml.json (by those exact names).";
      $("error").hidden = false;
      return;
    }
    useData(
      found.glyphs,
      found.candidates,
      found.shipped || null,
      found.saved || null,
    );
  }

  // ── The strokes on offer for a letter ───────────────────────────────

  /**
   * Every stroke the fonts offer for a letter, each with an id ("Manjari (part 2):1") and a label.
   * Where a font's strokes were split into groups (it could not tell the copies apart), the groups are offered
   * and the combined list is not, so no stroke appears twice.
   */
  function strokesOf(letter) {
    const options = state.candidates[letter];
    const keys = Object.keys(options)
      .filter((k) => !options[`${k} (part 1)`])
      .sort(
        (a, b) =>
          FONT_ORDER.indexOf(fontOf(a)) - FONT_ORDER.indexOf(fontOf(b)) ||
          a.localeCompare(b, "en", { numeric: true }),
      );
    return keys.flatMap((key) =>
      options[key].map((d, i) => ({
        id: `${key}:${i + 1}`,
        font: fontOf(key),
        d,
        label: `${key} · stroke ${i + 1} of ${options[key].length}`,
      })),
    );
  }

  /** The strokes chosen for a letter, in the order the letter is drawn in (ids that no longer exist are dropped). */
  function chosenStrokes(letter) {
    const byId = new Map(strokesOf(letter).map((s) => [s.id, s]));
    return (state.choices[letter] || [])
      .filter((id) => byId.has(baseId(id)))
      .map((id) => ({ ...byId.get(baseId(id)), rev: isRev(id) }));
  }

  // ── Choices (kept in this browser) ──────────────────────────────────

  function loadChoices() {
    try {
      return JSON.parse(window.localStorage.getItem(STORAGE_KEY)) || {};
    } catch {
      return {};
    }
  }

  function saveChoices() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state.choices));
    } catch {
      // Blocked storage: choices last until the page closes; Export still works.
    }
  }

  function setChoice(letter, ids) {
    if (ids.length) state.choices[letter] = ids;
    else delete state.choices[letter];
    saveChoices();
    renderLetters();
    renderProgress();
    markPicked();
    renderPreview();
  }

  function toggle(letter, id) {
    const ids = state.choices[letter] || [];
    const has = ids.some((x) => baseId(x) === id);
    setChoice(letter, has ? ids.filter((x) => baseId(x) !== id) : [...ids, id]);
  }

  /** Draw the chosen stroke at position `at` the other way round (its start and end swap). */
  function flip(letter, at) {
    const ids = [...(state.choices[letter] || [])];
    ids[at] = isRev(ids[at]) ? baseId(ids[at]) : `${ids[at]}~`;
    setChoice(letter, ids);
  }

  /** Move the stroke at `from` of the letter's chosen list one place earlier (-1) or later (+1). */
  function move(letter, from, delta) {
    const ids = [...(state.choices[letter] || [])];
    const to = from + delta;
    if (to < 0 || to >= ids.length) return;
    [ids[from], ids[to]] = [ids[to], ids[from]];
    setChoice(letter, ids);
  }

  function useFont(letter, font) {
    setChoice(
      letter,
      strokesOf(letter)
        .filter((s) => s.font === font)
        .map((s) => s.id),
    );
  }

  // ── Rendering ───────────────────────────────────────────────────────

  function el(tag, attrs, text) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, v));
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function svgEl(tag, attrs) {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) =>
      node.setAttribute(k, String(v)),
    );
    return node;
  }

  /** The letters a cluster is built from when it has no choice of its own but every part does, else null. */
  function composedFrom(letter) {
    if (state.choices[letter]) return null;
    const parts = [...letter].filter((c) => !"\u0d4d\u200c\u200d".includes(c));
    return parts.length > 1 && parts.every((c) => state.choices[c])
      ? parts
      : null;
  }

  function applyFilter() {
    const mode = $("filter").value;
    const settled = (c) => Boolean(state.choices[c] || composedFrom(c));
    state.shown = state.letters.filter(
      (c) => mode === "all" || (mode === "done") === settled(c),
    );
    state.index = Math.min(state.index, Math.max(0, state.shown.length - 1));
    renderLetters();
    renderProgress();
    renderCards();
  }

  function renderLetters() {
    const nav = $("letters");
    nav.replaceChildren();
    state.shown.forEach((letter, i) => {
      const cls = [];
      if (i === state.index) cls.push("current");
      const parts = composedFrom(letter);
      if (state.choices[letter]) cls.push("chosen");
      else if (parts) cls.push("composed");
      const title = state.choices[letter]
        ? "chosen"
        : parts
          ? `built from ${parts.join(" + ")}`
          : "not chosen";
      const b = el("button", { class: cls.join(" "), title }, letter);
      b.addEventListener("click", () => select(i));
      nav.appendChild(b);
    });
  }

  function renderProgress() {
    const counts = {};
    state.letters.forEach((c) => {
      const first = baseId((state.choices[c] || [])[0] || "");
      if (first) {
        const f = fontOf(first.slice(0, first.lastIndexOf(":")));
        counts[f] = (counts[f] || 0) + 1;
      }
    });
    const done = Object.values(counts).reduce((a, b) => a + b, 0);
    const parts = state.fonts
      .filter((f) => counts[f])
      .map((f) => `${f} ${counts[f]}`);
    const composed = state.letters.filter((c) => composedFrom(c)).length;
    $("progress").textContent =
      `${done} of ${state.letters.length} letters chosen` +
      (parts.length ? ` (${parts.join(", ")})` : "") +
      (composed ? `, ${composed} built from their parts` : "");
  }

  function renderBulk() {
    const box = $("bulk");
    box.replaceChildren();
    state.fonts.forEach((font) => {
      const b = el("button", {}, `All unchosen → ${font}`);
      b.addEventListener("click", () => {
        state.letters.forEach((c) => {
          const ids = strokesOf(c)
            .filter((s) => s.font === font)
            .map((s) => s.id);
          // a letter whose copies could not be told apart is left for a person to choose stroke by stroke
          if (
            !state.choices[c] &&
            ids.length &&
            !state.candidates[c][`${font} (part 1)`]
          )
            state.choices[c] = ids;
        });
        saveChoices();
        applyFilter();
      });
      box.appendChild(b);
    });
  }

  function select(i) {
    state.index = i;
    renderLetters();
    renderCards();
  }

  /** Zoom a card to fit everything in it: the outline and every stroke, wherever the font put them. */
  function fitView(svg) {
    const b = svg.getBBox();
    svg.setAttribute(
      "viewBox",
      `${b.x - PAD} ${b.y - PAD} ${b.width + 2 * PAD} ${b.height + 2 * PAD}`,
    );
  }

  /** The outline shapes of a letter: its cluster glyphs, or a mark's own shape when it has no cluster. */
  function outline(letter) {
    const cluster = state.glyphs.clusters[letter];
    if (cluster) return cluster.glyphs;
    const mark = state.glyphs.marks[letter];
    return [...mark.prefix, ...mark.suffix];
  }

  /** An SVG of the letter's outline with the given strokes ({d, rev}) on it, numbered in drawing order. */
  function drawing(letter, strokes) {
    const svg = svgEl("svg", {});
    const ghost = svgEl("g", { fill: "#e6e6e6" });
    outline(letter).forEach((g) =>
      ghost.appendChild(
        svgEl("path", {
          d: g.d,
          transform: `translate(${g.x},${g.y})`,
          "fill-rule": "evenodd",
        }),
      ),
    );
    svg.appendChild(ghost);
    strokes.forEach(({ d, rev }, i) => {
      const color = PALETTE[i % PALETTE.length];
      svg.appendChild(
        svgEl("path", {
          d,
          "data-rev": rev ? "1" : "0",
          class: "ink",
          fill: "none",
          stroke: color,
          "stroke-width": 16,
          "stroke-linecap": "round",
          "stroke-linejoin": "round",
        }),
      );
      const dot = svgEl("g", { class: "num" });
      dot.dataset.d = d;
      dot.dataset.rev = rev ? "1" : "0";
      dot.dataset.color = color;
      dot.dataset.n = String(i + 1);
      svg.appendChild(dot);
    });
    return svg;
  }

  function card(letter, label, note, strokes, id) {
    const c = el("div", { class: `card${id ? "" : " ref"}` });
    if (id) c.dataset.id = id;
    c.appendChild(el("h3", {})).append(label, el("small", {}, note));
    c.appendChild(drawing(letter, strokes));
    if (id) c.addEventListener("click", () => toggle(letter, id));
    return c;
  }

  function renderCards() {
    state.token++;
    const box = $("cards");
    box.replaceChildren();
    $("preview").replaceChildren();
    $("use").replaceChildren();
    const letter = state.shown[state.index];
    if (!letter) {
      $("title").textContent = "Nothing to show";
      return;
    }
    $("title").textContent = letter;
    const built = composedFrom(letter);
    if (built) {
      $("use").appendChild(
        el(
          "p",
          { class: "composed-note" },
          `Nothing to choose: ${letter} is drawn from ${built.join(" + ")}, the strokes you chose for them. Leave it unchosen. The cards below are only for comparison.`,
        ),
      );
    }
    const strokes = strokesOf(letter);
    strokes.forEach((s, i) =>
      box.appendChild(
        card(
          letter,
          `${i + 1}. ${s.label}`,
          "",
          [{ d: s.d, rev: false }],
          s.id,
        ),
      ),
    );
    const shipped = state.shipped?.[letter]?.strokes?.map((s) => ({
      d: s.d,
      rev: false,
    }));
    if (shipped?.length)
      box.appendChild(
        card(
          letter,
          "Ships today",
          "handwriting, for reference",
          shipped,
          null,
        ),
      );
    // "use all" only where the font gave one set of strokes, not several copies to choose between
    state.fonts
      .filter((font) =>
        strokes.some((s) => s.font === font && !s.id.includes("(part")),
      )
      .forEach((font) => {
        const b = el("button", {}, `Use all ${font} strokes`);
        b.addEventListener("click", () => useFont(letter, font));
        $("use").appendChild(b);
      });
    const clear = el("button", {}, "Clear");
    clear.addEventListener("click", () => setChoice(letter, []));
    $("use").appendChild(clear);
    box.querySelectorAll("svg").forEach(fitView);
    markPicked();
    renderPreview();
    placeStartDots(box);
    play();
  }

  function renderPreview() {
    const letter = state.shown[state.index];
    const holder = $("preview");
    holder.replaceChildren();
    if (!letter) return;
    const chosen = chosenStrokes(letter);
    const title = chosen.length
      ? `Your ${letter}: ${chosen.length} stroke${chosen.length > 1 ? "s" : ""}`
      : `Your ${letter}: nothing chosen yet`;
    holder.appendChild(el("h3", {}, title));
    const chips = el("div", { class: "chips" });
    chosen.forEach((s, i) => {
      const chip = el("span", { class: "chip" });
      chip.appendChild(el("b", {}, `${i + 1}`));
      chip.append(` ${s.label}${s.rev ? " (reversed)" : ""} `);
      [
        ["◀", "earlier", () => move(letter, i, -1)],
        ["▶", "later", () => move(letter, i, 1)],
        ["⇄", "reverse: draw it from its other end", () => flip(letter, i)],
        ["✕", "remove", () => toggle(letter, s.id)],
      ].forEach(([text, title2, act]) => {
        const b = el("button", { title: title2, type: "button" }, text);
        b.addEventListener("click", act);
        chip.appendChild(b);
      });
      chips.appendChild(chip);
    });
    holder.appendChild(chips);
    const svg = drawing(
      letter,
      chosen.map((s) => ({ d: s.d, rev: s.rev })),
    );
    holder.appendChild(svg);
    fitView(svg);
    placeStartDots(svg);
    playSvg(svg, state.token);
  }

  function markPicked() {
    const letter = state.shown[state.index];
    const order = (state.choices[letter] || []).map(baseId);
    const picked = new Set(order);
    $("cards")
      .querySelectorAll(".card[data-id]")
      .forEach((c) => {
        c.classList.toggle("picked", picked.has(c.dataset.id));
        const at = order.indexOf(c.dataset.id);
        c.querySelector("small").textContent =
          at >= 0 ? `stroke ${at + 1} of your letter` : "";
      });
  }

  function placeStartDots(root) {
    root.querySelectorAll("g.num").forEach((g) => {
      if (g.childElementCount) return;
      const probe = svgEl("path", { d: g.dataset.d });
      const tmp = svgEl("svg", {
        width: 0,
        height: 0,
        style: "position:absolute",
      });
      tmp.appendChild(probe);
      document.body.appendChild(tmp);
      const p = probe.getPointAtLength(
        g.dataset.rev === "1" ? probe.getTotalLength() : 0,
      );
      document.body.removeChild(tmp);
      g.appendChild(
        svgEl("circle", { cx: p.x, cy: p.y, r: 34, fill: g.dataset.color }),
      );
      const t = svgEl("text", {
        x: p.x,
        y: p.y + 14,
        "text-anchor": "middle",
        "font-size": 40,
        "font-weight": 700,
        fill: "#fff",
      });
      t.textContent = g.dataset.n;
      g.appendChild(t);
    });
  }

  // ── Playing ─────────────────────────────────────────────────────────

  function frames(ms, token, onProgress) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      function frame(now) {
        if (token !== state.token) return resolve(false);
        const t = Math.min(1, (now - t0) / ms);
        onProgress(t);
        if (t < 1) requestAnimationFrame(frame);
        else resolve(true);
      }
      requestAnimationFrame(frame);
    });
  }

  async function playSvg(svg, token) {
    const paths = [...svg.querySelectorAll("path.ink")];
    const lens = paths.map((p) => p.getTotalLength());
    // a reversed stroke is revealed from its end: a negative dash offset shows the dash from the far end first
    const sign = paths.map((p) => (p.dataset.rev === "1" ? -1 : 1));
    paths.forEach((p, i) => {
      p.style.strokeDasharray = `${lens[i]} ${lens[i]}`;
      p.style.strokeDashoffset = String(sign[i] * lens[i]);
    });
    const dots = [...svg.querySelectorAll("g.num")];
    dots.forEach((d) => (d.style.opacity = "0"));
    const speed = Number($("speed").value);
    for (let i = 0; i < paths.length; i++) {
      dots[i].style.opacity = "1";
      const ms = Math.max(
        MIN_STROKE_MS,
        (lens[i] / (UNITS_PER_SECOND * speed)) * 1000,
      );
      const ok = await frames(
        ms,
        token,
        (t) =>
          (paths[i].style.strokeDashoffset = String(
            sign[i] * lens[i] * (1 - t),
          )),
      );
      if (!ok) return;
      await new Promise((r) => setTimeout(r, PEN_LIFT_MS));
      if (token !== state.token) return;
    }
  }

  function play() {
    state.token++;
    const token = state.token;
    document
      .querySelectorAll("#cards svg, #preview svg")
      .forEach((svg) => playSvg(svg, token));
  }

  // ── Export / import ─────────────────────────────────────────────────

  function download(name, data) {
    const blob = new Blob([JSON.stringify(data, null, 2) + "\n"], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    el("a", { href: url, download: name }).click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportChoices() {
    const out = {};
    Object.keys(state.choices)
      .sort()
      .forEach((c) => (out[c] = state.choices[c]));
    download("font-stroke-choices.ml.json", out);
  }

  async function importChoices(file) {
    try {
      const incoming = JSON.parse(await file.text());
      Object.entries(incoming).forEach(([c, ids]) => {
        if (Array.isArray(ids)) state.choices[c] = ids;
      });
    } catch {
      $("error").textContent = `${file.name} is not a valid choices file.`;
      $("error").hidden = false;
      return;
    }
    saveChoices();
    applyFilter();
  }

  // ── Wiring ──────────────────────────────────────────────────────────

  function step(delta) {
    if (state.shown.length)
      select((state.index + delta + state.shown.length) % state.shown.length);
  }

  $("filter").addEventListener("change", applyFilter);
  $("play").addEventListener("click", play);
  $("next").addEventListener("click", () => step(1));
  $("prev").addEventListener("click", () => step(-1));
  $("export").addEventListener("click", exportChoices);
  $("import").addEventListener("click", () => $("import-file").click());
  $("import-file").addEventListener(
    "change",
    (e) => e.target.files[0] && importChoices(e.target.files[0]),
  );
  $("picker-input").addEventListener("change", (e) =>
    loadPicked([...e.target.files]),
  );
  document.addEventListener("keydown", (e) => {
    if (["INPUT", "SELECT", "BUTTON"].includes(e.target.tagName)) return;
    const letter = state.shown[state.index];
    if (e.key === "ArrowRight") step(1);
    else if (e.key === "ArrowLeft") step(-1);
    else if (e.key === " ") {
      e.preventDefault();
      play();
    } else if (/^[1-9]$/.test(e.key) && letter) {
      const s = strokesOf(letter)[Number(e.key) - 1];
      if (s) toggle(letter, s.id);
    }
  });

  load();
})();
