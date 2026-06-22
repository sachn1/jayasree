/**
 * malayalam-stroker (JS)
 *
 * Self-contained. No server. No font file at runtime.
 *
 * Two data files, both committed to your repo:
 *
 *   glyph-data.json   — font-specific: SVG outlines + advance widths for every
 *                        cluster.  Re-generate when you change fonts:
 *                          python tools/build_glyph_data.py [/path/to/Font.ttf]
 *                        Defaults to the bundled Manjari-Regular.ttf.
 *
 *   stroke-data.json  — font-agnostic: hand-authored centerline strokes per
 *                        cluster, produced by tools/stroke-recorder.html.
 *                        Commit once; works across font choices.
 *                        Falls back to outer-contour outline when missing.
 *
 * Basic usage:
 *   import { createStrokeWriter } from "malayalam-stroker";
 *   const writer = createStrokeWriter(document.getElementById("stage"));
 *   await writer.load();                  // glyph-data.json (font outlines)
 *   await writer.loadStrokes();           // stroke-data.json (authored paths) — optional
 *   await writer.play("നന്ദി");
 *
 * START_OVERRIDES / DIRECTION_OVERRIDES: keyed by Unicode cluster ("ന", "ക്ഷ")
 */

const SVGNS        = "http://www.w3.org/2000/svg";
const SAMPLE_STEPS = 200;
const PEN_LIFT_MS  = 120;
const GLYPH_DATA_URL   = new URL("./glyph-data.json",   import.meta.url);
const STROKE_DATA_URL  = new URL("./stroke-data.json",  import.meta.url);

export const START_OVERRIDES     = {};
export const DIRECTION_OVERRIDES = {};
// Populated by loadStrokes() or by importing/merging your own stroke-data.json.
// Keys are Unicode clusters ("ന", "ക്ഷ"). Values: { strokes: [{ d: "M ..." }] }
export const STROKE_LIBRARY      = {};

/* ── helpers ──────────────────────────────────────────────────────── */

function svgEl(tag, attrs) {
  const el = document.createElementNS(SVGNS, tag);
  for (const k in attrs) el.setAttribute(k, attrs[k]);
  return el;
}

function splitSubpaths(d) { return d.match(/M[^M]*/g) ?? [d]; }

function resolveStart(cluster, i) {
  const e = START_OVERRIDES[cluster];
  if (e === undefined) return "leftmost";
  return Array.isArray(e) ? (e[i] ?? "leftmost") : e;
}

function resolveDirection(cluster, i) {
  const e = DIRECTION_OVERRIDES[cluster];
  if (e === undefined) return "forward";
  return Array.isArray(e) ? (e[i] ?? "forward") : e;
}

const HOLE_RATIO = 0.45;
function classifySubpaths(subDs, scratch) {
  const lens = subDs.map(d => { scratch.setAttribute("d", d); return scratch.getTotalLength(); });
  const max  = Math.max(...lens);
  return lens.map(l => l >= max * HOLE_RATIO);
}

function buildTracePath(pathEl, startOverride, direction) {
  const len = pathEl.getTotalLength();
  if (len <= 0) return "";
  let pts = Array.from({ length: SAMPLE_STEPS }, (_, i) =>
    pathEl.getPointAtLength((i / SAMPLE_STEPS) * len)
  );
  let si = 0;
  if (typeof startOverride === "number") {
    si = Math.round(startOverride * SAMPLE_STEPS) % SAMPLE_STEPS;
  } else {
    const axis   = { leftmost:"x", rightmost:"x", topmost:"y", bottommost:"y" }[startOverride] ?? "x";
    const prefer = (startOverride === "rightmost" || startOverride === "bottommost")
                   ? (a, b) => a > b : (a, b) => a < b;
    let best = pts[0][axis];
    for (let i = 1; i < pts.length; i++) {
      if (prefer(pts[i][axis], best)) { best = pts[i][axis]; si = i; }
    }
  }
  pts = [...pts.slice(si), ...pts.slice(0, si)];
  if (direction === "reverse") pts = [pts[0], ...pts.slice(1).reverse()];
  return "M " + pts.map(p => `${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" L ") + " Z";
}

/* ── Malayalam segmentation ─────────────────────────────────────────
 * Longest-match: tries 3-char cluster (conjunct) → 2-char (consonant+matra) → 1-char.
 */
function segmentText(text, clusters) {
  const segs = [];
  let i = 0;
  while (i < text.length) {
    if (i + 2 < text.length && clusters[text.slice(i, i + 3)]) {
      segs.push(text.slice(i, i + 3)); i += 3;
    } else if (i + 1 < text.length && clusters[text.slice(i, i + 2)]) {
      segs.push(text.slice(i, i + 2)); i += 2;
    } else if (clusters[text[i]]) {
      segs.push(text[i]); i++;
    } else {
      i++;
    }
  }
  return segs;
}

/* ── main export ──────────────────────────────────────────────────── */

export function createStrokeWriter(container, options = {}) {
  const SPEED = options.speed ?? 6000;
  const state = { playToken: 0 };
  let glyphData = options.glyphData ?? null;
  let lastText  = null;

  async function load(url = GLYPH_DATA_URL) {
    if (glyphData) return;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`Failed to load glyph data: ${resp.status}`);
    glyphData = await resp.json();
  }

  // Load hand-authored stroke paths from stroke-data.json (or any URL).
  // Merges into the shared STROKE_LIBRARY so all writer instances benefit.
  // Safe to call multiple times — existing keys are not overwritten.
  async function loadStrokes(url = STROKE_DATA_URL) {
    let resp;
    try { resp = await fetch(url); } catch { return; }   // missing file = no-op
    if (!resp.ok) return;                                // 404 = no-op
    const data = await resp.json();
    for (const [cluster, entry] of Object.entries(data)) {
      if (!STROKE_LIBRARY[cluster]) STROKE_LIBRARY[cluster] = entry;
    }
  }

  function buildTrace(text) {
    if (!glyphData) throw new Error("Call writer.load() before writer.play()");
    const { meta, clusters } = glyphData;
    const segs = segmentText(text, clusters);
    if (!segs.length) return null;
    let penX = 0;
    // Each segment becomes one group: authored strokes fire once per group.
    // Components are the individual HarfBuzz glyphs that make up the cluster
    // (e.g. "ജാ" = ജ-base glyph + ാ-matra glyph). They are used for the ghost
    // and for the outline fallback, but NOT for authored stroke lookup.
    const segGroups = [];
    for (const seg of segs) {
      const entry = clusters[seg];
      if (!entry) continue;
      const components = entry.glyphs.map(g => ({ d: g.d, x: penX + g.x, y: g.y }));
      segGroups.push({ cluster: seg, components, groupX: penX });
      penX += entry.advance;
    }
    return { unitsPerEm: meta.unitsPerEm, ascent: meta.ascent, descent: meta.descent, totalAdvance: penX, segGroups };
  }

  function buildStage(trace) {
    container.innerHTML = "";
    const { unitsPerEm, ascent, descent, totalAdvance, segGroups } = trace;
    const pad = unitsPerEm * 0.1;
    const vb  = `${-pad} ${-ascent-pad} ${totalAdvance+pad*2} ${ascent-descent+pad*2}`;
    const svg = svgEl("svg", { viewBox: vb });

    // Ghost: all component paths for all clusters
    const ghostG = svgEl("g", { class:"ms-ghost" });
    segGroups.forEach(grp =>
      grp.components.forEach(c =>
        ghostG.appendChild(svgEl("path", { d:c.d, transform:`translate(${c.x},${c.y})` }))
      )
    );
    svg.appendChild(ghostG);
    container.appendChild(svg);

    const defs = svgEl("defs", {});
    svg.appendChild(defs);
    const scratch = svgEl("path", { fill:"none", stroke:"none" });
    defs.appendChild(scratch);

    const sw = unitsPerEm * 0.022;
    const stylus = svgEl("circle", { class:"ms-stylus", r: unitsPerEm * 0.016 });
    stylus.style.opacity = "0";
    svg.appendChild(stylus);

    const glyphUnits = segGroups.map(grp => {
      // Authored strokes — drawn ONCE per cluster group, regardless of component count.
      // Strokes are authored relative to the cluster's pen origin (groupX).
      const authored = STROKE_LIBRARY[grp.cluster];
      if (authored?.strokes?.length) {
        const gEl = svgEl("g", { transform:`translate(${grp.groupX},0)` });
        svg.appendChild(gEl);
        const tr = { x: grp.groupX, y: 0 };
        const subUnits = authored.strokes.map(s => {
          const el = svgEl("path", { d:s.d, class:"ms-stroke", "stroke-width":sw, "stroke-linecap":"round", "stroke-linejoin":"round" });
          gEl.appendChild(el);
          const len = el.getTotalLength();
          if (len > 0) { el.setAttribute("stroke-dasharray", `${len} ${len}`); el.setAttribute("stroke-dashoffset", String(len)); }
          return { strokeEl: el, len, tr };
        });
        return { gEl, subUnits };
      }

      // Fallback: outer-contour outline per component.
      // Each component is positioned with its own absolute translate.
      let oi = 0;
      const subUnits = grp.components.flatMap(c => {
        const subDs   = splitSubpaths(c.d);
        const isOuter = classifySubpaths(subDs, scratch);
        return subDs.flatMap((subD, i) => {
          if (!isOuter[i]) return [];
          scratch.setAttribute("d", subD);
          const td = buildTracePath(scratch, resolveStart(grp.cluster, oi), resolveDirection(grp.cluster, oi));
          oi++;
          if (!td) return [];
          const cEl = svgEl("g", { transform:`translate(${c.x},${c.y})` });
          svg.appendChild(cEl);
          const el = svgEl("path", { d:td, class:"ms-stroke", "stroke-width":sw, "stroke-linecap":"round", "stroke-linejoin":"round" });
          cEl.appendChild(el);
          const len = el.getTotalLength();
          if (len > 0) { el.setAttribute("stroke-dasharray", `${len} ${len}`); el.setAttribute("stroke-dashoffset", String(len)); }
          return [{ strokeEl: el, len, tr: { x: c.x, y: c.y } }];
        });
      });
      return { gEl: null, subUnits };
    });

    return { glyphUnits, stylus };
  }

  function traceSub(unit, stylus, token) {
    return new Promise(resolve => {
      const { strokeEl, len, tr } = unit;
      if (len <= 0) return resolve();
      const dMs = unit.dMs;
      const p0 = strokeEl.getPointAtLength(0);
      stylus.setAttribute("cx", String(p0.x + tr.x));
      stylus.setAttribute("cy", String(p0.y + tr.y));
      stylus.style.opacity = "1";
      const t0 = performance.now();
      function frame(now) {
        if (token !== state.playToken) return resolve();
        const t = Math.max(0, Math.min(1, (now - t0) / dMs));
        strokeEl.setAttribute("stroke-dashoffset", String(len * (1 - t)));
        const pt = strokeEl.getPointAtLength(t * len);
        stylus.setAttribute("cx", String(pt.x + tr.x));
        stylus.setAttribute("cy", String(pt.y + tr.y));
        if (t < 1) requestAnimationFrame(frame); else resolve();
      }
      requestAnimationFrame(frame);
    });
  }

  async function traceGlyph(unit, stylus, dMs, token) {
    const tl = unit.subUnits.reduce((s, u) => s + u.len, 0) || 1;
    // Attach dMs to each subUnit so traceSub can use it
    unit.subUnits.forEach(u => { u.dMs = Math.max(80, dMs * (u.len / tl)); });
    for (const sub of unit.subUnits) {
      if (token !== state.playToken) return;
      await traceSub(sub, stylus, token);
      if (sub !== unit.subUnits[unit.subUnits.length - 1]) {
        stylus.style.opacity = "0";
        await new Promise(r => setTimeout(r, PEN_LIFT_MS));
      }
    }
    stylus.style.opacity = "0";
  }

  async function play(text, playOptions = {}) {
    if (!glyphData) await load();
    lastText = text;
    const trace = buildTrace(text);
    if (!trace) return;
    const sm    = playOptions.speed ?? 1;
    const token = ++state.playToken;
    const { glyphUnits, stylus } = buildStage(trace);
    for (const unit of glyphUnits) {
      if (token !== state.playToken) return;
      const tl = unit.subUnits.reduce((s, u) => s + u.len, 0) || 1;
      await traceGlyph(unit, stylus, Math.max(200, (tl / (SPEED * sm)) * 1000), token);
    }
    if (token === state.playToken) stylus.style.opacity = "0";
  }

  function replay(o = {})  { return lastText ? play(lastText, o) : Promise.resolve(); }
  function cancel()         { state.playToken++; }
  function destroy()        { cancel(); container.innerHTML = ""; lastText = null; }

  return { load, loadStrokes, play, replay, cancel, destroy };
}
