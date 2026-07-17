/**
 * demo.js - interactive demo for jayasree.
 *
 * Loads glyph-data.json + stroke-data.json at startup, then wires up the
 * trace form, suggestion chips, replay button, and the stroke-library
 * drag-and-drop loader.
 */

import { createStrokeWriter, STROKE_LIBRARY } from "../js/src/index.js";

// Fetch + parse glyph-data.json once and hand the same parsed object to every
// writer instance (main stage + logo) via the `glyphData` option - each
// writer's own load() would otherwise independently re-fetch and, worse,
// re-parse this file, and at its current (prototype-stage) size that
// double parse is a real, noticeable chunk of page-load time.
const glyphDataResp = await fetch("../js/src/glyph-data.json");
const glyphData = await glyphDataResp.json();

// The ജയശ്രീ wordmark is a plain <img src="jayasree.svg"> in the HTML - the
// same pre-exported, self-animating (SMIL, no JS) asset the homepage uses.
// It used to be rebuilt here at runtime via createStrokeWriter, gated on
// this page's own ~5.5MB glyph-data.json fetch below for no reason (it's a
// fixed word, not user input) - now it just loads and animates on its own,
// independent of anything below.

const stage = document.getElementById("stage");
let writer = createStrokeWriter(stage, { glyphData });
const form = document.getElementById("traceForm");
const input = document.getElementById("wordInput");
const status = document.getElementById("status");
const btn = document.getElementById("traceBtn");

// Load stroke-data.json (processed: centered + smoothed + ghost-straightened +
// expanded - see tools/process_strokes.py) and await it - it alone already
// covers every word in the "Try:" chips and the default word below, so the
// first trace can start as soon as it's ready. stroke-data.raw.json (hand-
// recorded strokes not yet through the processing pipeline) is fetched but
// deliberately NOT awaited: loadStrokes() never overwrites a cluster
// already in STROKE_LIBRARY, so it only ever fills in coverage the
// processed file doesn't have yet, and nothing shown on page load depends
// on it - no reason to block the default trace on another ~6.8MB fetch.
await writer.loadStrokes(`../js/src/stroke-data.json?v=${Date.now()}`);
writer.loadStrokes(`../js/src/stroke-data.raw.json?v=${Date.now()}`);

// ---------------------------------------------------------------------------
// Controls - speed / thickness / repeat
// ---------------------------------------------------------------------------

const speedCtl = document.getElementById("speedCtl");
const speedVal = document.getElementById("speedVal");
const thicknessCtl = document.getElementById("thicknessCtl");
const thicknessVal = document.getElementById("thicknessVal");
const countCtl = document.getElementById("countCtl");

/** Current per-play options from the speed slider + repeat select. */
function playOptions() {
  return { speed: Number(speedCtl.value), count: Number(countCtl.value) };
}

speedCtl.addEventListener("input", () => {
  speedVal.textContent = `${Number(speedCtl.value)}×`;
});
// `change` (not `input`) so it fires once per adjustment, not per pixel of
// slider drag - same reasoning as thicknessCtl's `change` listener below.
speedCtl.addEventListener("change", () => {
  traceWord(input.value);
});

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

// strokeWidth is fixed at writer creation (it sizes every stroke element the
// stage builds), so changing it means a fresh writer on the same stage -
// cheap, since the parsed glyphData object is shared and STROKE_LIBRARY is
// module-global. `change` (not `input`) so it fires once per adjustment, not
// per pixel of slider drag.
thicknessCtl.addEventListener("input", () => {
  thicknessVal.textContent = thicknessLabel(Number(thicknessCtl.value));
});
thicknessCtl.addEventListener("change", () => {
  writer.cancel();
  writer = createStrokeWriter(stage, {
    glyphData,
    strokeWidth: Number(thicknessCtl.value),
  });
  traceWord(input.value);
});

// ---------------------------------------------------------------------------
// Trace
// ---------------------------------------------------------------------------

/**
 * Trace the given word and handle errors.
 *
 * @param {string} word
 */
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

document.querySelectorAll(".chips button").forEach((b) =>
  b.addEventListener("click", () => {
    input.value = b.dataset.word;
    traceWord(input.value);
  })
);

document.getElementById("replay").addEventListener("click", () => writer.replay(playOptions()));

// ---------------------------------------------------------------------------
// Speech input - say a word instead of typing it
// ---------------------------------------------------------------------------

// Chrome/Edge/Safari only expose this as the prefixed webkitSpeechRecognition;
// Firefox doesn't implement it at all. The button stays `hidden` (see
// index.html) on any browser where neither exists, rather than showing a
// control that would just fail on click.
const SpeechRecognitionAPI = window.SpeechRecognition ?? window.webkitSpeechRecognition;
const speakBtn = document.getElementById("speakBtn");

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
    recognition.lang = "ml-IN";
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

const libDrop = document.getElementById("lib-drop");
const libFile = document.getElementById("lib-file");
const libStatus = document.getElementById("lib-status");

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
      writer.replay();
    } catch {
      libStatus.textContent = "Could not parse JSON - is this a stroke-data export?";
    }
  };
  reader.readAsText(file);
}

libDrop.addEventListener("click", () => libFile.click());
libFile.addEventListener("change", () => libFile.files[0] && loadLibrary(libFile.files[0]));
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

// Trace the default word on load.
traceWord(input.value);
