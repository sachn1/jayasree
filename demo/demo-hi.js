/**
 * demo-hi.js - minimal progress-check demo for Hindi, trimmed from demo.js.
 *
 * Hindi's onboarding is still in progress (see docs/languages/hi/
 * labeling-worklist.md) - this intentionally only supports the handful of
 * controls that matter for checking real traced/composed output, not the
 * full feature set demo.js has for Malayalam (speech input, thickness
 * control, stroke-library drag-and-drop). Loads glyph-data.hi.json +
 * stroke-data.hi.json, same pattern as demo.js's Malayalam load.
 */

import { createStrokeWriter } from "../js/src/index.js";

const glyphDataResp = await fetch(`../js/src/glyph-data.hi.json?v=${Date.now()}`);
const glyphData = await glyphDataResp.json();

const stage = document.getElementById("stage");
// Slightly thicker than index.js's own DEFAULT_STROKE_WIDTH_FRACTION
// (0.022, unchanged there - Malayalam's published demo isn't touched by
// this) - a mitigation for small centering wobble being more visually
// obvious while Hindi's onboarding is still in progress (see
// docs/CENTERING_EXPERIMENTS.md's self-intersection finding), not a fix
// for it.
// speed: a quarter of index.js's own default (6000 - unchanged there,
// so the published npm package's pace is untouched) - some strokes were
// too fast to actually watch being drawn, especially single letters in
// the letter browser below. The speed *slider* still shows "1x" as its
// default position; this is what that "1x" now actually renders at.
const writer = createStrokeWriter(stage, { glyphData, strokeWidth: 0.03, speed: 1500 });
const form = document.getElementById("traceForm");
const input = document.getElementById("wordInput");
const status = document.getElementById("status");
const btn = document.getElementById("traceBtn");

await writer.loadStrokes(`../js/src/stroke-data.hi.json?v=${Date.now()}`);
writer.loadStrokes(`../js/src/stroke-data.hi.raw.json?v=${Date.now()}`);

const speedCtl = document.getElementById("speedCtl");
const speedVal = document.getElementById("speedVal");
const countCtl = document.getElementById("countCtl");

function playOptions() {
  return { speed: Number(speedCtl.value), count: Number(countCtl.value) };
}

speedCtl.addEventListener("input", () => {
  speedVal.textContent = `${Number(speedCtl.value)}×`;
});
speedCtl.addEventListener("change", () => traceWord(input.value));

async function traceWord(word) {
  word = word.trim();
  if (!word) return;
  status.textContent = "";
  btn.disabled = true;
  try {
    await writer.play(word, playOptions());
  } catch (err) {
    status.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  traceWord(input.value);
});

// Letter browser - every independent vowel + consonant, one click each, so
// a single letter's own trace can be checked in isolation (e.g. after a
// stroke-data regen) without typing/remembering a word that happens to
// contain it. Same idea as demo.js's own letter browser.
const HI_LETTERS = [
  "अ", "आ", "इ", "ई", "उ", "ऊ", "ऋ", "ए", "ऐ", "ओ", "औ",
  "क", "ख", "ग", "घ", "ङ", "च", "छ", "ज", "झ", "ञ", "ट", "ठ", "ड", "ढ",
  "ण", "त", "थ", "द", "ध", "न", "प", "फ", "ब", "भ", "म", "य", "र", "ल",
  "व", "श", "ष", "स", "ह",
]; // prettier-ignore

const letterChips = document.getElementById("letterChips");
for (const ch of HI_LETTERS) {
  const b = document.createElement("button");
  b.type = "button";
  b.dataset.word = ch;
  b.textContent = ch;
  letterChips.appendChild(b);
}

document.querySelectorAll(".chips button").forEach((b) =>
  b.addEventListener("click", () => {
    input.value = b.dataset.word;
    traceWord(input.value);
  })
);

document.getElementById("replay").addEventListener("click", () => writer.replay(playOptions()));

traceWord(input.value);
