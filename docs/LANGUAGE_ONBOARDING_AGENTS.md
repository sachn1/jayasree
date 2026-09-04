# Language Onboarding - Multi-Agent Pipeline

A design for the agent pipeline that takes this project from "a language
name" to "a human has a minimal, correct set of atoms to trace." This is
**Phase 1 only**: research the script, pick a ghost font, and produce the
reduced labeling set. It stops there, at the same handoff point
`CONTRIBUTING.md`'s "Adding a new language" section already stops at -
*"recording needs a native speaker/writer of that script."* Actually driving
the recording session, triaging bug reports, and everything after is a
separate, later design (see "Out of scope" below).

Everything here is a **plan**, not yet implemented. No agent orchestration
code exists in the repo for this yet. Phase 0 (the prerequisite code
parametrization below) *is* implemented - see its section for what changed.

## Target languages

Malayalam is the only language onboarded so far - everything else here is
planned. The intended roster, onboarded **one language at a time** (never
several in flight at once - see "Design principles" below), in the order
given to this plan:

1. Hindi (Devanagari)
2. Tamil (Tamil script)
3. Telugu (Telugu script)
4. Kannada (Kannada script)
5. Bengali (Bengali script)
6. Sanskrit (Devanagari, historically also written in others)
7. more, beyond that, unscoped for now

Note Hindi and Sanskrit share a script (Devanagari) but are different
languages with different scope pressures - Sanskrit needs Vedic-era
characters/marks a modern Hindi profile has no reason to include. Whether
that means one shared `_chars_devanagari.py` with a language-specific
extension, or two independent profiles that happen to overlap heavily, is
an open question for whichever of the two is onboarded first (see "Open
questions").

**Read "Don't generalize from Malayalam" immediately below before running
Agent 1 for any of these** - none of them are Dravidian scripts, and
several of this doc's worked examples (chillu, subjoined-conjunct tails,
the specific split-vowel decomposition) are Malayalam/Dravidian-specific
findings, not general Indic-script facts.

## Don't generalize from Malayalam

Every concrete example in this document - chillu letters, the ്യ/്വ/്ല/്ര
subjoined-conjunct tails, the ൊ/ോ/ൌ split-vowel decomposition, the "~108
true ligatures" figure - is a **Malayalam finding**, cited because it's the
one worked example this project has. It is not a claim that Devanagari,
Tamil, Telugu, Kannada, or Bengali work the same way, and an agent (or a
person) running this pipeline for one of them should actively expect
differences, not surprise at them:

- **Devanagari (Hindi, Sanskrit) has no chillu-equivalent** bare-consonant
  form, but has its own well-known complexity Malayalam's pipeline has
  never had to handle: a large, productive set of consonant-conjunct
  ligatures (many formed via a visible half-form + the following
  consonant, some via a horizontal "reph" mark, some via genuinely fused
  ligature glyphs) - likely *more* true ligatures than Malayalam's ~108,
  not fewer.
- **Tamil** has a comparatively small consonant inventory and very few true
  ligatures (conjuncts are rare in native Tamil vocabulary) - Agent 2's
  font-verification step may find *most* consonant clusters decompose
  cleanly, the opposite emphasis from Malayalam's profile.
- **Telugu and Kannada** (a closely related script pair) have their own
  vowel-sign-fusion and conjunct ("vattu") conventions, structurally
  different from both Malayalam's and Devanagari's.
- **Bengali** has its own conjunct system (many genuinely fused, some
  Unicode-standard "ref"/"ya-phala" forms) distinct from all of the above.

Agent 1's job for each of these is to *discover* that script's actual
structure from scratch (sourced research, verified by Agent 2's real
HarfBuzz shaping) - not to fill in Malayalam's category names with a new
script's characters and assume the categories themselves transfer. Where
this document's "Job" descriptions below list Malayalam-shaped examples in
parentheses, read them as *"here is what this looked like for Malayalam"*,
never as *"here is what you should expect to find."*

## Why this isn't starting from zero

This project already solved the exact problem step 3 below is about -
"reduce thousands of combinations to the minimum a human must hand-label" -
for Malayalam, and documented both the solution and the mistakes made
building it:

- `tools/build_glyph_data.py`'s `marks` table gives every composable mark
  (virama, every matra, subjoined conjunct tails) a `{shift, prefix, suffix,
  trailingWidth}` recipe, derived by shaping the mark *alone* against
  HarfBuzz's real dotted-circle placeholder - not by guessing from a
  representative character.
- `tools/stroke-recorder.html` already filters its dropdown to the reduced
  atom set (~290 for Malayalam, out of ~2050 total clusters) using that
  table, with a "show all clusters" toggle for spot-checking.
- `tools/process_strokes.py --expand` (`stroke_compose.py`) and
  `js/src/index.js`'s runtime composer (`tryComposeStroke`) build everything
  else from those atoms, recursively, with the mark recipe.
- `docs/ARCHITECTURE.md`'s "Composition" section documents four real bugs
  this approach hit and fixed (placeholder-circle anchor correction,
  segmentation priority, tighten-trim on mark shifts, multi-glyph-base
  composition) - a checklist for what a *generic*, multi-script version of
  this machinery needs to keep handling correctly.

This machinery (`marks` table, `--expand`, `tryComposeStroke`) is already
described in the README/ARCHITECTURE as script-agnostic in its geometry and
composition logic; what's Malayalam-specific is only the *character
inventory* it's fed (`_chars.py`) and the *data it's fed to* (the two
committed JSON files). Agent 3 below is designed to feed that same generic
machinery a new script's inventory, not to reimplement it. (For the concrete
danger of reimplementing it instead, see the "duplicate scratch tooling"
note in `CLAUDE.md` - that's exactly what a shortcut version of Agent 3
would produce.)

## Design principles

1. **Reuse the existing pipeline; extend, don't fork.** Every output this
   pipeline produces should be shaped to slot into `build_glyph_data.py` /
   `process_strokes.py` / `stroke-recorder.html` as they already exist
   (post-parametrization - see Phase 0), not a parallel set of scripts.
2. **Human sign-off is mandatory at every stage, not just at the end.**
   `CONTRIBUTING.md` already draws this line for stroke data - *"strokes
   drawn by someone who doesn't write it daily are worse than no strokes."*
   The same bar applies to the linguistic profile (Agent 1) and the font
   choice (Agent 2): a wrong character inventory or a wrong font poisons
   everything built on top of it, and an agent has no way to *know* it's
   wrong the way a native speaker or a font's license terms can be wrong in
   ways only a human safely confirms. Each agent's output is a proposal for
   a human to approve, not a final artifact.
3. **Verification is structural, not just self-reported.** Every claim an
   agent makes that's checkable by running code (does this font actually
   have a glyph for this character; does this cluster actually render as one
   fused glyph or several) gets checked by actually shaping it through
   HarfBuzz, not asserted from a font's metadata or a research summary.
4. **No script's onboarding touches another script's files** - this is
   already a hard rule (`CONTRIBUTING.md`), and the pipeline's outputs are
   scoped per-language from the start (`_chars_<lang>.py`,
   `glyph-data.<lang>.json`, ...) to make violating it structurally awkward,
   not just discouraged.
5. **One language in flight at a time.** The target roster (see "Target
   languages" above) is deliberately worked sequentially, not in parallel -
   each run of this pipeline should reach its human sign-off gates (and
   ideally get through some real recording) before the next language
   starts, so lessons from one (a quirk Agent 1 missed, a font that turned
   out to have gaps) can inform the next rather than several languages
   independently repeating the same mistake.
6. **Coverage is bounded by the font, not by linguistic minimalism.**
   (Project owner, resolving Hindi's open questions - `docs/languages/hi/
   profile.md`.) The objective is to animate whatever the user actually
   types, so scope questions default to inclusion within "does the chosen
   font support this," not "is this common/standard enough to bother
   with." This governs judgment calls like which nukta letters or which
   loan vowels are in scope - it does *not* extend to pulling in a
   different *language's* characters just because they share a Unicode
   block or a font's coverage (Sanskrit's Vedic accents are still excluded
   from Hindi's own profile, per "one language at a time" above and "Don't
   generalize from Malayalam") - the font bounds *how much of this
   language* to include, not *which language*.

## Phase 0 - prerequisite code changes (done)

The pipeline below produces a language's *data*. Before that data had
anywhere correct to land, a handful of Malayalam-only assumptions needed to
become parameters. This was ordinary refactoring work, not agent work -
done once, generically, ahead of the first new-language run rather than
under pressure during it. What changed:

- **`python/src/jayasree/languages.py` (new)** - the single registry
  mapping a language name to its `LanguageSpec` (`code`, its
  `chars_module`, a `carrier_consonant` for shaping marks in isolation, and
  an optional bundled `default_font`). `data_paths(lang)` derives that
  language's `glyph-data`/`stroke-data(.raw)`/snapshot paths from its
  `code` - unsuffixed for `PRIMARY_LANGUAGE` (Malayalam, for backward
  compatibility with the published npm package and GitHub Pages site,
  which fetch `glyph-data.json`/`stroke-data.json` by that exact name),
  `.{code}`-suffixed for everything else. `char_tuple(module, name)` reads
  an inventory category off a language module and falls back to `()` if
  that module doesn't define it - see "Don't generalize from Malayalam"
  above for why nothing is assumed present.
- **`tools/build_glyph_data.py`** - takes `--lang` (default: `malayalam`),
  looks up the `LanguageSpec`, and builds its input-cluster list generically
  from whichever inventory categories that language's module actually
  defines. Malayalam's own hand-curated quirks (the ്യ/്വ/്ല/്ര
  subjoined-conjunct marks, the ൻറ/്ര extra ghosts, the ൊ/ോ/ൌ split-vowel
  exclusion) are gated behind `lang.code == "ml"`, not applied to every
  language - a new script's equivalent quirks (if any) get their own gated
  block once Agent 1/2 actually find them, per "Don't generalize from
  Malayalam." Verified to produce byte-identical output for Malayalam
  before/after this change.
- **`python/src/jayasree/cli.py`** - the `alphabet` sub-command takes
  `--lang` (default: `malayalam`) and builds its standalone-run/matra-
  syllable lists from the registry instead of a hardcoded Malayalam import.
- **`tools/process_strokes.py`** - takes `--lang` to select default
  `--input`/`--glyph-data`/`--output` paths (still overridable
  individually); `--preset=full` is a new script-agnostic alias for
  `--preset=malayalam` (kept working, since it's referenced elsewhere in
  the docs) - the four stages it names were always script-agnostic, only
  the preset's *name* wasn't.
- **`tools/validate_data.py`** - discovers every `glyph-data*.json` under
  `js/src/` and validates each language's triple, rather than hardcoding
  Malayalam's three filenames. Deliberately does **not** import
  `jayasree.languages` (or anything else from the `jayasree` package): the
  pre-commit hook `.pre-commit-config.yaml` defines for it runs via
  `language: system` on every commit touching a data file, using whatever
  bare `python3` is on the committer's PATH - there's no guarantee
  `uharfbuzz` (a transitive dependency of the full `jayasree` package) is
  importable there. It re-derives the same suffix convention locally from a
  single duplicated literal (`_PRIMARY_CODE = "ml"`), documented in its
  module docstring as the trade-off this constraint forces.
- **`python/tests/test_data_snapshot.py` - deliberately unchanged.**
  `CONTRIBUTING.md`'s existing convention is that a new language gets its
  *own* sibling test module (mirroring `test_chars_malayalam.py`), not an
  edit to the shared one - a new language's snapshot test should import
  `validate_data.build_snapshot` (already a pure, language-agnostic
  function) against its own `paths_for("<code>").snapshot`, following that
  same pattern, when it's actually onboarded.
- **`js/src/index.js` - audited, no changes needed.** `resolveSegments` and
  the rest of the composition engine look up whatever `clusters`/`marks`
  keys the loaded `glyph-data.json` happens to contain - there is no
  Malayalam Unicode-range regex or hardcoded cluster-length bound anywhere
  in the file (checked directly against the source, not assumed).
  `LEGACY_CHILLU` and `SPLIT_VOWEL_PARTS` are the only Malayalam-specific
  lookup tables, and both are inert (never matched) against text in any
  other script. `docs/ROADMAP.md`'s older note about auditing "segmentation
  regex bounds in index.js" turned out not to describe anything that
  actually exists there.
- **Makefile** - `build-glyph-data`, `process-strokes`, `update-snapshot`
  now accept `LANG=<name>`, defaulting to `malayalam` everywhere (`make
  build-glyph-data` behaves exactly as before if `LANG` is omitted).
  `validate-data` (plain, no `--update-snapshot`) always checks every
  language found on disk regardless of `LANG`.
- **Tests** - `python/tests/test_languages.py` (new) and additions to
  `test_validate_data.py`/`test_cli.py` cover the registry, the
  discovery/path logic, and the new `--lang` argument's error handling.
  `make ci` (both `ci-py` and `ci-js`) passes; Malayalam's
  `glyph-data.json`/`stroke-data.json` were regenerated and diffed
  byte-identical against the pre-refactor committed versions.

Adding a real second language from here means: registering its
`LanguageSpec` in `languages.py`, writing its `_chars_<code>.py` (Agent 1's
job below), and running `build_glyph_data.py --lang <name>` against its
chosen font (Agent 2/3's job) - no further plumbing changes anticipated,
though Agent 1/2 may still surface a script-specific quirk that needs its
own small, gated extension the way Malayalam's do.

**Already borne out**: Hindi's Agent 1 pass (`docs/languages/hi/`) needed
three category names Malayalam never had - `CANDRABINDU`, `NUKTA`,
`NATIVE_PUNCTUATION` - and `languages.py`/`build_glyph_data.py` were
extended to recognize them (still fully optional, still zero effect on
Malayalam's output - verified byte-identical after the change). This is
the pattern going forward: a language's profile can reveal a genuinely new
*infrastructure* category, not just new character data, and that gets
folded into the shared tooling before that language's own onboarding
continues - not deferred, and not generalized preemptively for languages
not yet being worked on.

## The three agents

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

### Agent 2 - Ghost Font Selection & Coverage Verification

**Input:** Agent 1's approved profile.

**Job:** find a font that is (a) license-compatible with this project's
stance (Malayalam uses Manjari, SIL OFL 1.1 - README's "License & credit"
section; a new font needs an equivalently open license, not just "free to
download"), (b) a real outline font HarfBuzz can shape (not a bitmap/color
font), and (c) **verified**, not claimed, to cover every character and
cluster in Agent 1's profile - including old/rare forms if those were scoped
in.

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
(`docs/languages/hi/profile.md`), beyond the three bullets above:**

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

**Review gate:** a human (a native writer of the script, per
`CONTRIBUTING.md`'s existing bar) spot-checks a sample of the reduced set's
ghost outlines before recording starts - catching a bad font choice or a
missed character category here is far cheaper than after hundreds of
strokes are recorded against it.

## Orchestration

Sequential with feedback edges, not a strict one-way pipeline:

```
Agent 1 (research) ⇄ Agent 1-reviewer (critique)
        │  human approval
        ▼
Agent 2 (font search + HarfBuzz verification) ──┐
        │  human approval               │ falsified ligature/coverage
        ▼                                │ claim → back to Agent 1
Agent 3 (drives build_glyph_data.py,     │
         derives reduced atom set)  ◄────┘
        │  human spot-check
        ▼
labeling-worklist.md  →  (Phase 2: recording workflow, out of scope here)
```

Each arrow with "human approval" is a hard stop, not a suggestion - this
mirrors `CONTRIBUTING.md`'s existing "Data integrity & governance" layering
(structural validation, content snapshot, generated-vs-source separation,
review + history, read-only runtime) applied one stage earlier, to the
research and font-selection stages that layer doesn't currently cover at
all because only one language has ever gone through it.

## Where artifacts live

```
docs/languages/<lang-code>/
├── profile.md              # Agent 1 - narrative + sources
├── chars.json               # Agent 1 - structured inventory
├── font-report.md            # Agent 2 - candidates, license, coverage
└── labeling-worklist.md       # Agent 3 - what a human traces, in order

python/src/jayasree/_chars_<lang-code>.py   # promoted from chars.json
js/src/glyph-data.<lang-code>.json           # Agent 3 output (generated),
                                              # via build_glyph_data.py --lang
```

Plus one `LanguageSpec` entry added to `python/src/jayasree/languages.py`'s
`LANGUAGES` registry (`code`, `name`, `chars_module`, `carrier_consonant`,
and a `default_font` once Agent 2 has picked one) - this is what makes
`--lang <name>` work across `build_glyph_data.py`/`cli.py`/
`process_strokes.py` for the new language.

`<lang-code>` should be a stable, short identifier (ISO 639 - `ta` for
Tamil, etc.), matching the `data(ml)`/`data(ta)` commit-scope convention
`CONTRIBUTING.md` already uses and the `LanguageSpec.code` field above.

## Open questions

- **Scope of "old/archaic characters."** Agent 1 will surface a judgment
  call (include Sanskrit-loanword-only rare vowels/consonants? historical
  orthography?) that has no purely mechanical answer - Malayalam's own
  `_chars.py` already makes this call (`RARE_VOWELS`/`RARE_CONSONANTS`/
  `RARE_MATRAS`, included; deprecated pre-reform-only forms, not) and that
  precedent is worth deferring to unless the human reviewer says otherwise.
- **Cost/budget for the research stage.** Web-research + multi-round
  critique loops are the most open-ended (least bounded-cost) part of this
  pipeline; worth capping rounds and being explicit that the human gate,
  not agent consensus, is what actually closes this stage.
- **Font licensing edge cases.** Not every script has a Manjari-equivalent
  (an actively-maintained, clearly-OFL-licensed, HarfBuzz-friendly font);
  Agent 2 may come back with "no good candidate" as a legitimate result,
  which should block the pipeline rather than settle for a worse license.
- **Shared-script languages** (Hindi and Sanskrit both use Devanagari):
  whether that means one `_chars_devanagari.py` covering both, with
  Sanskrit's Vedic-only additions layered on somehow, or two independent
  profiles that happen to overlap - genuinely open, and not worth deciding
  until one of the two is actually being onboarded and the other isn't yet
  (per "one language at a time" above).

## Out of scope (deferred - "Phase 2")

Everything after `labeling-worklist.md` exists: actually orchestrating the
native-speaker recording session, `docs/ROADMAP.md`'s "Bug-report → data
pipeline" (diagnosing wrong renders, a coverage gate, a frictionless
report→record loop), and any tooling to help a non-technical native speaker
work through the worklist without needing to understand this pipeline. Not
designed here on purpose - per the request that started this doc, Phase 1
stops at "the requirement/labeling-set is well understood," and Phase 2
should be scoped once Phase 1 has actually run once.
