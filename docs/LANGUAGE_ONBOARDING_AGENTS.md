# Language Onboarding - Multi-Agent Pipeline

How a language goes from a name to shipped handwriting, in eight stages (the table below). Only recording
(stage 4), the sign-offs and the look in a browser need a human: recording needs a native writer of the
script (`CONTRIBUTING.md`). Run it with `/onboard-language <name>`, which detects the stage and enforces the
gates. It has run once end to end, on Hindi.

This file is the portable spec of each role; `.claude/agents/*.md` are thin adapters over it. If you change
what a role does, change it here first.

## The sequence at a glance

Run in this order, one language at a time. `/onboard-language <name>` does
the stage detection and the gates for you; each agent can also be invoked
directly, e.g. `Agent(language-researcher, "Tamil")`.

| # | Stage | Who does it | Trigger | Output | Who signs off | Status |
|---|---|---|---|---|---|---|
| 1a | Research the script | `language-researcher` (Agent 1) | the owner asks `/onboard-language <name>` | `docs/languages/<code>/profile.md`, `chars.json`, `writing-rules.md` | - (goes to 1b) | built |
| 1b | Critique the draft | `language-reviewer` (read-only) | automatic, after 1a | critique, shown in chat | **the owner** approves the profile | built |
| 2 | Ghost-font selection + HarfBuzz check | `font-selector` (Agent 2) | the profile is approved | `font-report.md` | **the owner** approves one font (a falsified claim goes back to 1a) | built |
| 3 | Reduced atom set | `atom-reducer` (Agent 3) | the font is approved | `_chars_<code>.py`, its tests, the `LanguageSpec` entry, `glyph-data.<code>.json`, `labeling-worklist.md` (opens with the writing-rules brief), `reduced-atom-list*.txt`, a simulated coverage report | **the owner** spot-checks the worklist | built |
| 4 | Record strokes | **the owner**, in `tools/stroke-recorder.html` | the worklist exists | `js/src/stroke-data.<code>.raw.json` | the owner says the recording is done | human |
| 5 | Process + verify | a command, run by the skill (not an agent) - see "Post-recording gate" | the owner says the recording is done | `js/src/stroke-data.<code>.json` | gate: `validate-data` OK and coverage 0 fallbacks | command planned (an `onboard-gate` target) |
| 7 | Wire up and document | `language-publisher` | the stage-5 gate passes | demo tab, wordmark, README and home-page mentions, `docs/languages/<code>/README.md` | `test_language_wiring.py` passes | built |
| 6 | Inspect in a browser | **the owner** | stage 7 is done (it needs the demo tab) | follow-up fixes, each on its own branch | the owner says the letters are clean | human |
| 8 | Freeze | a generator command, run by the skill | **only** the owner's "this ships" | a golden file + JS and Python freeze tests | the owner | built by hand per language (Malayalam, Hindi); see "Stage 8" |

Stage 7 runs before 6 because the browser check needs the demo tab. Every stage
that changes the repo goes in as a branch and a PR; **the owner merging that PR
is the sign-off**, so "the font report is on the language's branch" means the font
was approved. Agents never merge. Before each PR, the `code-reviewer` agent runs
on the branch.

`code-reviewer` is **not** a stage of this pipeline - it reviews code diffs
and is invoked separately.

## Don't generalize from Malayalam

Every worked example in the repo (chillu letters, subjoined conjunct tails, the ൊ/ോ/ൌ split vowels, "~108
true ligatures") is a **Malayalam finding**, not a fact about Indic scripts. Expect each script to differ:
Devanagari has no chillu but many half-form, reph and fused conjuncts; Tamil has few conjuncts; Telugu and
Kannada have their own vattu and vowel-fusion rules; Bengali has its own conjunct system. Agent 1 *discovers*
the script's structure from sources, verified by Agent 2's real HarfBuzz shaping; read a Malayalam example in
this spec as "what it looked like for Malayalam", never as what to expect.

## Design principles

1. **Extend the existing pipeline, never fork it.** Outputs slot into `build_glyph_data.py`,
   `process_strokes.py` and `stroke-recorder.html` (Phase 0 below).
2. **A human signs off at every stage.** An agent's output is a proposal; a native writer or the font's licence
   terms can be wrong in ways an agent cannot know. Strokes from someone who doesn't write the script daily are
   worse than none.
3. **Verify by running code**, not from metadata or a summary: shape it through HarfBuzz.
4. **One language in flight at a time, and none touches another's files** (`CONTRIBUTING.md`).
5. **Coverage is bounded by the font, not by minimalism.** Scope questions default to "include it if the chosen
   font supports it", but never another language's characters (Sanskrit's Vedic marks stay out of Hindi). Rare
   or archaic forms are a flagged judgment call; Malayalam's `RARE_*` sets are the precedent. "No good font"
   is a valid Agent 2 result and blocks the pipeline.

## Phase 0 - the language registry

`python/src/jayasree/languages.py`'s `LANGUAGES` maps a language name to its `LanguageSpec` (code, character
module, carrier consonant, default font) and derives its data paths: unsuffixed for Malayalam, `.{code}` for the
rest. `build_glyph_data.py`, `process_strokes.py`, `cli.py` and `validate_data.py` all take `--lang`.

## The research, font and atom agents

### Agent 1 - Linguistic Research & Script Profiling

**Input:** a language name from the user (e.g. "Tamil").

**Job:** produce a complete, sourced character inventory for the script,
shaped like `_chars.py`'s categories so it can become `_chars_<lang>.py`
directly:

- independent vowels, consonants (regular / script-specific /
  rare-or-archaic - mirroring `REGULAR_CONSONANTS`/`SPECIAL_CONSONANTS`/
  `RARE_CONSONANTS`'s split), numerals, matras (dependent vowel signs),
  virama-equivalent, anusvara/visarga-equivalents, and any
  chillu-equivalent (bare word-final consonant forms) if the script has one
  - Malayalam's chillu, with its two-Unicode-encodings-one-glyph quirk
    (`docs/ARCHITECTURE.md`'s "Chillu letters" section), is a concrete
    example of exactly the kind of encoding subtlety this stage exists to
    catch before it becomes a runtime bug.
- **old vs. modern character variants**: deprecated/reformed letterforms,
  any orthography reform history, characters still in traditional/religious
  texts but dropped from modern typesetting (own judgment call to scope
  in/out, flagged explicitly rather than silently included or excluded).
- **conjunct/ligature inventory**: which consonant clusters form true fused
  ligatures (script- and often font-dependent - Malayalam's ~108 true
  ligature conjuncts are documented in `docs/ARCHITECTURE.md`) vs. which
  compose visually from parts. This is a *hypothesis* at this stage - Agent
  2 verifies it against real font shaping, since ligation is actually a font
  behavior, not a purely linguistic fact.
- **compound/split vowel signs** with a canonical decomposition (Malayalam's
  ൊ/ോ/ൌ → NFD-equivalent prefix+suffix parts is the model - see
  "Compound vowel signs" in `docs/ARCHITECTURE.md`) vs. any with no clean
  decomposition (Malayalam's ൈ is the model for that exception).
- Unicode block, code points, and citations for every non-obvious claim.
- **writing rules**, in their own file (`writing-rules.md`): how the script is
  actually written by hand - stroke order and direction per letter group, where the
  headline/baseline stroke falls in a letter and in a word, and when each mark (vowel
  sign, nukta-equivalent, anusvara, virama) is written relative to its base and to the
  headline. Sources are ranked and the **highest tier wins**: (1) an official or
  community-accepted standard (a government or language-board writing guide, the national
  curriculum's primers, Unicode/W3C notes); (2) university courses and published
  handwriting manuals; (3) learner sites and apps. Every rule carries a **confidence**
  (high / medium / low / unknown), its source tier, and a link; where the sources conflict
  or no standard exists, say so instead of choosing. Many scripts have no fixed stroke
  order - record that as a finding, not a gap. Rules that need a native writer's
  confirmation go in a "Questions for the native writer" list.

**Tools:** web search/fetch for linguistic references, Unicode's own
script/block charts and proposals, academic/orthographic sources; no code
execution needed for this stage.

**Review gate (the "fluent, literate reviewer" requirement):** run as two
roles, not one pass - a *researcher* agent produces the draft profile, then
a separate *reviewer* agent (prompted for fluency, literary/orthographic
depth, and explicitly instructed to interrogate the researcher's claims
rather than restate them) critiques it: flags anything that looks
incomplete, anachronistic, dialectally narrow, or unsourced, and sends it
back for revision. Iterate a bounded number of rounds, then hand the
result - explicitly marked "agent-reviewed, not human-verified" - to the
user (ideally someone who reads/writes the script) for actual sign-off
before Agent 2 starts. Don't skip the human gate because the agent review
passed; the agent review's job is to make the human review fast and
well-organized, not to replace it.

**Output artifacts** (proposed location: `docs/languages/<lang-code>/`):

- `profile.md` - the narrative version: what's in scope and why, open
  questions, sources, anything the reviewer flagged.
- `chars.json` (or directly a draft `_chars_<lang>.py`) - the structured
  inventory, machine-readable for Agent 2/3.
- `writing-rules.md` - the writing rules above, with confidence and sources.
  The reviewer interrogates it like the rest, hunting especially for "always" claims.

### Agent 2 - Ghost Font Selection & Coverage Verification

**Input:** Agent 1's approved profile.

**Job:** find a font that is (a) license-compatible with this project's
stance (Malayalam uses Manjari, SIL OFL 1.1 - README's "License & credit"
section; a new font needs an equivalently open license, not just "free to
download"), (b) a real outline font HarfBuzz can shape (not a bitmap/color
font), (c) **verified**, not claimed, to cover every character and
cluster in Agent 1's profile - including old/rare forms if those were scoped
in, and (d) reasonably low-contrast/monoline in its stroke-width modulation.
Point (d) is a real, not cosmetic, criterion: `docs/CENTERING_EXPERIMENTS.md`
documents that the adopted centering/straightening approach (gradient ascent
up a distance-transform field) is already known to get unreliable near
corners/junctions - a font with pronounced calligraphic ductus (stroke width
varying by direction, e.g. a broad-nib look) multiplies exactly those
ambiguous junctions wherever strokes join (headline-to-stem, conjunct joins),
so prefer the candidate with flatter stroke-width variation when coverage and
license are otherwise tied, and note the tradeoff explicitly in
`font-report.md` if the best-covered candidate is also the most calligraphic
one.

Verification is mechanical, reusing this project's own shaping code
(`python/src/jayasree/strokes.py`'s HarfBuzz path, the same one
`build_glyph_data.py` calls): shape every atom and a representative sample
of the profile's hypothesized ligatures/conjuncts through the candidate
font, and check for `.notdef` glyphs and for whether each hypothesized
ligature actually renders as one fused glyph or several. **This step can
falsify Agent 1's ligature classification** - a font might not ligate
something Agent 1 expected to be fused, or might fuse something Agent 1
expected to decompose. That's a real finding, not noise: route it back to
Agent 1 (or directly to the human reviewer, if Agent 1's round is already
closed) to correct the profile, since the labeling set in Agent 3 depends on
getting this right - conflating "true ligature" with "composable" is exactly
the class of bug `docs/ARCHITECTURE.md`'s Composition section catalogs.

**Output artifacts** (same `docs/languages/<lang-code>/` directory):

- `font-report.md` - candidates considered, why each was rejected or
  chosen, license text/link, and the coverage-verification results
  (character/cluster → glyph, flagged mismatches against Agent 1's
  ligature hypotheses).
- the chosen font file (or a pinned download reference, matching how
  Manjari is currently vendored - check `python/tests/fixtures/` for the
  existing convention before adding a new one).

**Review gate:** human approval on the font choice specifically (licensing
is a real legal/attribution obligation, not just a technical one - see
`LICENSE`/`LICENSE-DATA`'s existing split between code and data licenses)
before Agent 3 runs against it.

### Agent 3 - Atom-Set Reduction & Labeling Worklist

**Input:** Agent 1's approved profile + Agent 2's approved, verified font.

**Job:** this is closer to a **script that calls the existing pipeline**
than a research agent - its job is to *drive* `build_glyph_data.py --lang
<name>` (already parametrized - see Phase 0) against the new
`_chars_<lang>.py` and chosen font, producing `glyph-data.<lang>.json` with
its own `marks` table, then derive
the reduced atom set from that table exactly the way
`stroke-recorder.html` already does for Malayalam - not a new heuristic.
Concretely, the reduced set is:

- every standalone character (from Agent 1's inventory),
- every consonant+vowel-sign combination the `marks` table records as *not*
  generically composable (Malayalam's ു/ூ/ൃ-style fused forms are the
  precedent - Agent 2's shaping pass is what actually reveals which ones
  these are for the new script/font),
- every true single-glyph ligature/conjunct Agent 2 confirmed actually
  fuses.

Everything else is left to compose automatically at runtime/build time, the
same as Malayalam's ~1760 non-atom clusters do today.

**Two more ways to shrink the labeling set, found during Hindi's profiling
(`docs/languages/hi/README.md`), beyond the three bullets above:**

- **Synthetic strokes.** A mark simple enough to generate procedurally
  (Hindi's nukta - just a small dot) needs no human-traced recording at
  all, only a real font glyph outline (for the ghost/composition
  geometry). Not every atom in the reduced set needs *tracing* - some just
  need *synthesizing*.
- **Self-composition.** A character that's structurally "the same mark,
  twice, offset" (Hindi's double danda from single danda) composes from
  its *own* recorded stroke via the existing glyph-offset machinery
  (`stroke_compose.py`/`tryComposeFromCharacters`), rather than needing a
  separate recording.

Both reduce the *labeling-worklist* further than atom-set reduction alone
- worth checking for on every future language, not just Hindi.

**Coverage audit - before AND after recording, same tool
(`tools/coverage_report.js`):** don't just *assert* the reduced atom set
is sufficient - verify it, mechanically, using the exact composition code
`js/src/index.js`'s runtime uses (not a reimplementation):

- **Pre-recording (simulated).** Once `glyph-data.<lang-code>.json` exists
  (it needs the real `marks` table to know what's composable at all - this
  audit is not a substitute for generating it, it runs right after), feed
  `coverage_report.js --simulate-atoms <planned-atom-list>` the reduced
  set Agent 3 just derived. It stubs a trivial stroke for every listed
  atom and reports, for *every* cluster the font defines, whether it would
  resolve to a direct or composed stroke. 100% here means the atom-set
  *logic* is structurally sound - worth confirming before a human spends
  real time tracing hundreds of strokes on the strength of it. Anything
  short of 100% is a bug in the reduction logic (a category Agent 3 missed
  entirely), not something for a human to work around.
- **Post-recording (real).** Once real strokes exist -
  `coverage_report.js --stroke-data <real stroke-data(.raw).json>` - run
  the identical check against real data. This is the standing coverage
  gate; `--min-coverage N` makes it usable as a CI gate once a
  language's recording work has stabilized enough that regressions, not
  in-progress gaps, are the thing worth failing a build over.
- `--verbose` lists every fallback cluster with a specific reason (missing
  base stroke, a mark recipe that exists but didn't apply, a
  character-count/glyph-count mismatch, ...), for the whole cluster set of any language.

**The worklist opens with a writing-rules brief.** Before the first atom, copy
in `writing-rules.md`'s rules as a short table (rule, confidence, source tier), so the
person recording sees what the research found - and how sure it is - before drawing
anything. Low or unknown confidence rules are listed as questions, not instructions.

**Output artifacts:**

- `glyph-data.<lang-code>.json` (generated, committed - same convention as
  the existing `js/src/glyph-data.json`).
- `labeling-worklist.md` - the human-facing deliverable: the reduced atom
  list, grouped and counted the way `README.md`'s "Status" section already
  reports Malayalam's (~290 atoms, split standalone/fused-mark/ligature),
  plus priority ordering (standalone characters first, since everything
  else depends on them existing before composition can be spot-checked)
  and a pointer to load `stroke-recorder.html` against the new
  `glyph-data.<lang-code>.json` to start tracing.
- The pre-recording coverage report (saved alongside the worklist) -
  evidence the reduced set was verified sufficient, not just asserted to
  be.

**Review gate:** a human (a native writer of the script, per
`CONTRIBUTING.md`'s existing bar) spot-checks a sample of the reduced set's
ghost outlines before recording starts - catching a bad font choice or a
missed character category here is far cheaper than after hundreds of
strokes are recorded against it. The pre-recording coverage report is what
makes this spot-check trustworthy: a human is verifying *quality*
(does this ghost look right), the tool already verified *completeness*
(does the atom set cover everything) - the two are complementary, neither
substitutes for the other.

## Orchestration

Sequential, with human approval as a hard stop after each agent, and feedback edges: a falsified ligature or
coverage claim from Agent 2 goes back to Agent 1; a font change re-runs Agent 3.

```
Agent 1 (research) <-> reviewer -> human -> Agent 2 (font) -> human -> Agent 3 (atoms) -> human -> worklist
```

The five agents are explicit-use only (each `description` says "use only when explicitly asked"), so they never
auto-trigger on unrelated prompts.

## Where artifacts live

```
docs/languages/<lang-code>/
├── profile.md              # Agent 1 - narrative + sources
├── chars.json               # Agent 1 - structured inventory
├── writing-rules.md          # Agent 1 - how it is written by hand, with confidence + sources
├── font-report.md            # Agent 2 - candidates, license, coverage
├── labeling-worklist.md       # Agent 3 - what a human traces, in order
├── reduced-atom-list.txt       # Agent 3 - the atom set, grouped/commented
├── reduced-atom-list.flat.txt   # Agent 3 - same set, one per line (the
│                                 #   --simulate-atoms input for coverage_report.js)
└── coverage-report-pre-recording.txt   # Agent 3 - simulated coverage, verbatim
                                         # (+ any script-specific research reports)

python/src/jayasree/_chars_<lang-code>.py   # written by Agent 3 from chars.json
python/tests/test_chars_<lang-code>.py       # its own test module
js/src/glyph-data.<lang-code>.json           # Agent 3 output (generated),
                                              # via build_glyph_data.py --lang
js/src/stroke-data.<lang-code>.raw.json      # stage 4 - the human's recording
js/src/stroke-data.<lang-code>.json          # stage 5 - generated from the above
```

**Working files vs. the record.** The files above are working artifacts: they
exist so the next stage (and the human sign-off) has something to read. Once a
language's stage 5 is done, don't keep them all - fold them into one short
`docs/languages/<code>/README.md` and delete the rest (they stay in git
history; name the commit in the README). Keep `reduced-atom-list.flat.txt`,
which tooling reads. `docs/languages/hi/README.md` is the worked example; its
sections are the template: **Status** (stage-by-stage outcome and sign-off
dates), **Scope decisions** (owner resolutions, exclusions), **Font decision**
(candidates, measured criteria, licence, what the switch cost), **the atom set**
(groups and counts), **the script's headline finding** (what didn't fit the
existing composition model), **Corrections the mechanical pass found**,
**Still open**, **Reproducing**, **Sources**. Malayalam's
`docs/languages/ml/` predates this and is kept as is.

Plus one `LanguageSpec` entry added to `python/src/jayasree/languages.py`'s
`LANGUAGES` registry (`code`, `name`, `chars_module`, `carrier_consonant`,
and a `default_font` once Agent 2 has picked one) - this is what makes
`--lang <name>` work across `build_glyph_data.py`/`cli.py`/
`process_strokes.py` for the new language.

`<lang-code>` should be a stable, short identifier (ISO 639 - `ta` for
Tamil, etc.), matching the `data(ml)`/`data(ta)` commit-scope convention
`CONTRIBUTING.md` already uses and the `LanguageSpec.code` field above.

## After recording

### Post-recording gate (stage 5)

Not an agent: a fixed command sequence, run from the repo root, all of which
must pass before a language's data is committed.

```bash
cd python && poetry run python ../tools/process_strokes.py --preset=full --lang hindi && cd ..
python3 tools/validate_data.py
node tools/coverage_report.js --glyph-data js/src/glyph-data.hi.json \
                              --stroke-data js/src/stroke-data.hi.json   # want: 0 fallback
```

If clusters fall back, `--verbose` explains each one: a missing atom means
record it (stage 4); "recipe exists but composition itself failed" means a
composition bug to fix in shared code - with Malayalam's tests unmodified.
For Hindi that same command also runs the font-geometry cleanup (`docs/ARCHITECTURE.md`,
"Cleanup (Hindi)"), so the committed strokes are the cleaned ones. A new language gets it by being added
to the language check in `process_strokes.py`, only after its own review.
Commit the raw and processed strokes together as a one-line `data(<code>)`
commit. A language's *first* data needs no `make update-snapshot`; a later
change to an already-recorded cluster does.

### Stage 7 - wire up and document

A language is not finished when its strokes are processed: a visitor sees it
only once the demo, the site and the docs know about it. This used to be done
by hand (Hindi's lessons are the checklist), so a step could be forgotten.
`language-publisher` does it, and `python/tests/test_language_wiring.py` fails
until the demo tab, wordmark and README pieces are in (it does not check the
language README, scope line or roadmap - review those). Do these in order; the owner reviews the result in a
browser before anything goes to `master`.

1. **Demo tab.** One entry in `demo/demo.js`'s `LANGUAGES` table (code, tab
   label, tagline, default word, "Try:" words, letter browser, speech tag, the
   three data paths, stroke width, `logo`).
2. **Wordmark.** `tools/export_wordmark.py --lang <name> --output
   demo/jayasree.<code>.svg --color <hex>`, in a colour no other language
   uses. `DEFAULT_COLOR` in that tool is Hindi's red and is tied to it by a
   test, so a new language passes `--color` and leaves the default alone.
   `demo/demo.css` has one `#logo-live` colour rule (Hindi's): a second live
   wordmark needs its own per-language rule there and in `demo.js`.
3. **README and home page.** Show the wordmark beside the others in
   `README.md` and `index.html` (the `<img>` and the home page's replay-script
   entry), add the language to the status table, name it
   in the one-line description.
4. **Fold the working files** (see "Where artifacts live") into
   `docs/languages/<code>/README.md`, using `docs/languages/hi/README.md` as the
   template.
5. **Scope line.** Update "Current scope" in `CLAUDE.md` and the roster in
   `docs/ROADMAP.md`.
6. **Gate.** `make ci` green, every already-frozen language's freeze tests
   unmodified, `test_language_wiring.py` passing, and the `code-reviewer` agent
   run on the branch before its PR.

The font-geometry cleanup is not part of this stage: a language gets it by being
added to the language check in `process_strokes.py` (stage 5's command), after its
own review.

### Stage 8 - freeze

The last step, and the owner's: once the owner has looked at the language in a
browser, says the letters are clean and it ships, **freeze it** - snapshot
exactly what its visitors see (words, clusters, data) into a golden file, with a
JS and a Python test that fail if any of it moves. From then on the language is
*shipped*, and the rule for every later change, human or agent, is: **no
previously shipped language's letters, data or behaviour may change**; shared
code may change only if every frozen language's tests pass unmodified. A frozen
language changes only by a deliberate, reviewed regeneration of its golden file
(for example a later cleanup of Malayalam's strokes).

Today Malayalam and Hindi are frozen: each has `tests/<language>-freeze.test.js`,
`python/tests/test_<language>_freeze.py`, a golden file in `tests/freeze/` and a
raw-data snapshot (`CONTRIBUTING.md`, "Language freezes" and "The Hindi
freeze"). Hindi was frozen when it shipped. For the next
language, copy Hindi's files (`tests/freeze/hindi-snapshot.mjs`,
`generate-hindi-golden.mjs`, `tests/hindi-freeze.test.js`,
`python/tests/test_hindi_freeze.py`), then change the language, the words, the
file list and the label. A shared, language-parametrized freeze is a worthwhile
cleanup once a third language needs it; it would touch Malayalam's frozen
tests, so it needs the owner's approval.

## What Hindi's first run taught us

- **A font change after Agent 3 invalidates its output.** Hindi moved from Annapurna SIL to Noto Sans Devanagari
  and the atom set went from 174 to 183. Re-sweep true ligatures per font; never hand-curate them.
- **Devanagari needed a composition primitive Malayalam did not**: half-forms and reph (`contextualForms`,
  `tryComposeContextualForm`). Malayalam has no such table, so that path is a no-op for it.
- **The worklist is the contract.** A first recording pass is rarely complete; `coverage_report.js --verbose`
  names the missing atoms. Skipping one on purpose is fine if the recorder's remarks field says so.
- **`--lang` / `PROJECT_LANG=` take the registry name** (`hindi`), not the code (`hi`). The Python tools need the
  Poetry environment (`uharfbuzz`).
