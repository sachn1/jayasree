# Hindi (Devanagari) — Script Profile

> **Status: agent-reviewed, not human-verified.** This is Agent 1's output
> from `docs/LANGUAGE_ONBOARDING_AGENTS.md` — a proposal, not a final
> artifact. Per that plan's design principles, it needs sign-off from
> someone who reads/writes Hindi before Agent 2 (ghost font selection)
> starts, and every "open question" below is a real decision, not a
> rhetorical one. Nothing here has been HarfBuzz-verified yet — that's
> Agent 2's job, and it can (per the plan) falsify some of the ligature/
> conjunct hypotheses below.

## Why Devanagari is a genuinely different shape than Malayalam

`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s "Don't generalize from Malayalam"
section predicted Devanagari would need *more* machinery for
consonant-conjunct formation, not less. That's confirmed, and more
elaborately than expected: Devanagari's own OpenType shaping model (see
Microsoft's [Developing OpenType Fonts for Devanagari
Script](https://learn.microsoft.com/en-us/typography/script-development/devanagari))
names and orders **eight** distinct conjunct-formation mechanisms (`akhn`,
`rphf`, `rkrf`, `blwf`, `half`, `pref`, `vatu`, `cjct`) applied in a fixed
sequence per syllable — Malayalam's pipeline only ever needed one generic
prefix/suffix mark recipe plus a short, hand-curated list of true
ligatures. Concretely, none of this is a Malayalam finding + Devanagari
characters; it's Devanagari's own structure, described below.

## Independent vowels

11 standard letters, taught in every school varnamala:
अ आ इ ई उ ऊ ऋ ए ऐ ओ औ (U+0905–U+090B, U+090F–U+0914).

**Loan vowels** (2, modern, for English/other-loanword sounds not native to
Hindi): ऍ *(candra e, /æ/, as in बैंक)*, ऑ *(candra o, /ɒ/, e.g.
कॉलेज "college")* — independent letters at U+090D, U+0911 (their matra
forms ॅ/ॉ, used attached to a consonant, are the separate codepoints
U+0945/U+0949 — see "Matras" below; don't conflate the two, they're
different characters for different roles).

**Sanskrit-loanword-only, rare** (parallel to Malayalam's `RARE_VOWELS`
tier): ऌ *(vocalic L, U+090C)*, and the independent letters ॠ *(vocalic RR,
U+0960)*, ॡ *(vocalic LL, U+0961)* — essentially never appear in native
Hindi vocabulary, only in direct Sanskrit borrowings/dictionary entries.

**Explicitly out of scope, not "rare" but wrong-language**: ऄ *(short A,
U+0904)*, ऎ/ऒ *(short e/short o, U+090E/U+0912)* — used for Dravidian-length
distinctions or Marwari/Kashmiri conventions, not Hindi at all. Including
these would be the exact "fill in Malayalam's categories with the wrong
script's characters" mistake the plan warns against, just inverted (here,
including characters this *is* the right Unicode block for, but the wrong
language for).

## Consonants

**33 basic**, organized by traditional articulation grouping (velar →
palatal → retroflex → dental → labial, then nasals/approximants/sibilants):
क ख ग घ ङ, च छ ज झ ञ, ट ठ ड ढ ण, त थ द ध न, प फ ब भ म, य र ल व, श ष स ह
(U+0915–U+0939, contiguous — but not *all* of that range: ऩ, ऱ, ळ, ऴ
*(Nnna, Rra, Lla, Llla)* sit inside the same contiguous block but are
Marathi/Dravidian-transliteration letters, not Hindi's — excluded, same
"same Unicode block, wrong language" reasoning as the vowel exclusions
below. ळ is the one most likely to actually turn up in real Hindi text,
in Marathi-origin loanwords/regional writing.).

**Nukta-modified consonants** (dot below, U+093C combining with a base
letter — or precomposed at U+0958–U+095F): used for sounds borrowed from
Persian/Arabic/English. Search corroboration across multiple sources
converges on: **ड़, ढ़** (retroflex flap sounds, native to modern
Hindi/Hindustani, not Sanskrit) are treated as standard Hindi consonants by
most authorities. **क़, ख़, ग़, ज़, फ़** (Perso-Arabic loan sounds: q, x/ḵ,
ġ, z, f) are used in careful/formal writing (Urdu-influenced vocabulary,
some English loans) but are **not universally taught as separate alphabet
letters** — casual Hindi writing frequently drops the nukta dot entirely
(ज for ज़, फ for फ़). This is a real scope decision, not a technicality —
see "Open questions" below.

**Encoding duality — direct parallel to Malayalam's chillu problem**:
nukta consonants exist as *both* a precomposed codepoint (U+0958–U+095F)
*and* a decomposed `consonant + ़ (U+093C)` sequence, and — per Unicode
normalization — the precomposed forms are in most cases the NFD
decomposition target of nothing (i.e. some of U+0958–095F are *not*
canonical-equivalent to their decomposed sequence; verify per-codepoint
before assuming interchangeability). Real-world Hindi text mixes both
spellings unpredictably, exactly like Malayalam's atomic-chillu vs.
`consonant+virama+ZWJ` split (`docs/ARCHITECTURE.md`'s "Chillu letters"
section) — this script will need its own `normalizeNukta()`-equivalent
before real text reliably matches recorded strokes.

## Matras (dependent vowel signs)

**9 core**: ा ि ी ु ू े ै ो ौ (U+093E–U+0942, U+0947–U+094C) — attach
before, after, above, or below the consonant depending on the specific
mark (े/ै attach *before* the consonant visually despite being typed
*after* it — a pre-base mark, the same category as Malayalam's െ/േ/ൈ).

**Loan-vowel matras** (2, modern, paired with ऍ/ऑ above): ॅ, ॉ
(U+0945, U+0949).

**Sanskrit-loanword-only, rare**: ृ *(vocalic R matra, U+0943)* is common
enough in real Hindi (कृष्ण, कृपा) to arguably not be "rare" at all — flagged
as an open question. ॄ, ॢ, ॣ *(vocalic RR/L/LL matras, U+0944, U+0962–3)*
are genuinely rare, Sanskrit-dictionary tier.

**No split/compound matra found for Hindi**, unlike Malayalam's
ൊ/ോ/ൌ → NFD-decomposable prefix+suffix pairs. Every Devanagari matra here
is its own single codepoint with no canonical decomposition. (The OpenType
spec's glossary defines a generic "split matra" concept used by *some*
Indic scripts, but nothing found in this research shows Devanagari itself
using it for Hindi's vowel signs — flagged for Agent 2 to confirm/refute
via real shaping, not assumed either way.)

## Virama, nasalization, aspiration

- **Virama/halant**: ् (U+094D) — suppresses the inherent vowel; also the
  trigger for every conjunct-formation mechanism below.
- **Anusvara**: ं (U+0902) — nasalization; modern Hindi's default way to
  write a nasal before a following consonant (अंत, हंस).
- **Candrabindu**: ँ (U+0901) — nasalization of a vowel with *no* following
  consonant (हँसी, हाँ). Modern style guides (CBSE and similar) draw this
  distinction fairly consistently; older/informal text sometimes uses
  anusvara for both. A real "old vs. modern" convention shift, structurally
  like Malayalam's chillu spelling reform.
- **Visarga**: ः (U+0903) — voiceless aspiration; rare in native Hindi
  vocabulary, appears mostly in direct Sanskrit borrowings (दुःख, प्रातः).

## Numerals

० १ २ ३ ४ ५ ६ ७ ८ ९ (U+0966–U+096F) — direct parallel to Malayalam's
`NUMERALS`. Modern printed/typed Hindi very commonly uses Latin/Arabic
digits (0-9) instead, especially outside formal government documents; both
are legitimate in scope but only the Devanagari set needs its own recorded
stroke — Latin digits are exactly `UNIVERSAL_CHARS`-shaped
(script-independent, no ghost, no stroke) if they end up supported at all.

## Native punctuation — an open design question

**Danda** । and **double danda** ॥ (U+0964, U+0965) are Devanagari's own
sentence/verse-end punctuation, not borrowed from Latin — this is different
from Malayalam, whose punctuation is entirely the shared Latin set
(`UNIVERSAL_CHARS` in `index.js`, deliberately script-independent). Modern
Hindi increasingly uses the Latin period instead of danda in casual
writing, but danda is still standard in formal/literary/religious text and,
unlike a period, *is* one of this script's own written marks — someone
learning Devanagari handwriting plausibly wants to see it traced. Flagged
as a real design question, not defaulted either way (see "Open questions").

## Other marks, rare tier

- **Avagraha**: ऽ (U+093D) — marks vowel elision (dictionary/poetic use,
  e.g. सोऽहम्). Rare in everyday writing but real, unlike the Vedic marks
  below.
- **Om**: ॐ (U+0950) — appears in ordinary Hindi text in religious/cultural
  contexts, not just Sanskrit liturgy. Worth including.

## Explicitly excluded — Sanskrit/Vedic, not Hindi

**Vedic accent marks** — udatta/anudatta (U+0951–0952), grave/acute accent
(U+0953–0954), plus the entire Devanagari Extended-A block
(U+A8E0–U+A8FF) — mark tonal accent for Vedic recitation. These are the
concrete example of `docs/LANGUAGE_ONBOARDING_AGENTS.md`'s open question
about Hindi/Sanskrit sharing Devanagari: **excluded from this Hindi
profile entirely**, reserved for a future Sanskrit profile, since they
never appear in ordinary modern Hindi.

**Other-Devanagari-language-only letters**, added in Unicode 7.0 (2014)
specifically for Marwari, Kashmiri, Konkani, Sindhi, and Dogri conventions
— not Hindi: ॐ's neighbors U+0972–U+097F (Candra A, Oe, Ooe, Aw, Ue, Uue,
Marwari Dda, Zha, Heavy Ya, Gga, Jja, Glottal stop, Ddda, Bba), and the
vowel sign Oe/Ooe pair (U+093A/093B). Excluded, same reasoning as the short
vowels above.

## Conjunct/ligature hypotheses (Agent 2 must verify)

This is the section most likely to change once real font shaping is
checked — everything here is a *reading* of Microsoft's shaping-engine
documentation, not a font-verified fact:

- **Reph**: when र is the *first* consonant of a cluster (e.g. र्क, र्म),
  it doesn't render as a normal र — it becomes a small hook above the
  *end* of the syllable (`rphf`/reordering). This is the same letter र in
  a special contextual form, not a separate atom the way Malayalam's
  subjoined ്യ/്വ/്ല/്ര are their own dedicated recordings.
- **Rakaar (vattu)**: when र is *not* the first consonant of a cluster
  (e.g. क्र, प्र, ग्र), it attaches below/after the preceding consonant as
  a small diagonal stroke (`rkrf`/`blwf`) — again the same letter, a
  different contextual form.
- **Half-forms**: most other consonants have a distinct "half form" glyph
  (vertical stem removed) used when they're non-final in a cluster —
  visually and structurally the closest Devanagari analogue to Malayalam's
  subjoined-conjunct tails, but applying to *most of the alphabet*, not a
  handful of marks.
- **Akhand ligatures**: a small set of consonant clusters that *must*
  fuse into one dedicated glyph regardless of context, highest shaping
  priority. क्ष *(kṣa)* and ज्ञ *(jña)* are the two nearly every source
  agrees on; त्त, श्र, and a few others appear in some but not all
  treatments/fonts. This is the direct analogue of Malayalam's ~108 true
  ligatures — likely a much shorter list for Hindi, but genuinely unknown
  until Agent 2 checks a real font.

**Open question this raises for Agent 3**: reph and rakaar are contextual
*forms of an existing atom* (र), not new atoms — whether they can compose
generically from र's own standalone stroke (the way Malayalam's marks
table composes generically) or need their own dedicated recording (the way
Malayalam's subjoined ്ര needed one, because 19/36 consonants fused it
into a font-specific ligature unrelated to the base's own shape) is
exactly the kind of thing that can only be settled by shaping real
clusters through a real font — not guessed here.

## Resolved (project owner, 2026-09-04)

All five open questions from the first draft are now decided. The
governing principle, stated explicitly: **coverage is bounded by the font,
not by linguistic minimalism** - the objective is to animate whatever the
user actually types, so scope should lean maximal within "does the chosen
font support this" rather than "is this common/standard enough to bother
with." This changes the *reasoning* behind a couple of these from the
first draft, not just the answers - noted per item.

1. **Nukta-letter scope: font-gated, and no human tracing needed at all.**
   Whichever nukta letters the chosen font actually renders (Agent 2's
   job to confirm) are in scope - not restricted to the 2 or 5 "most
   authorities agree on" from the first draft's framing. But nukta itself
   needs **no recorded stroke**: it's a small dot, not a shape requiring a
   native speaker's hand - synthesize it programmatically (a filled
   circle/dot primitive) rather than asking a human to trace it. This is a
   new composition primitive beyond what Malayalam's pipeline needed - see
   "New composition primitives for Agent 3" below and the corresponding
   note added to `docs/LANGUAGE_ONBOARDING_AGENTS.md`. The font is still
   needed for nukta's real glyph outline (the ghost/ligature-detection
   side of things), just not for a hand-traced ink stroke.
2. **Danda: recorded; double-danda: auto-composed, not separately traced.**
   Danda (।) gets one real human-traced stroke, like any other atom.
   Double danda (॥) is **not** its own labeling-set entry - it's generated
   as danda's own stroke placed twice, offset by danda's real advance
   width (the same glyph-offset composition machinery `stroke_compose.py`/
   `index.js` already use for other multi-glyph clusters). One recording
   covers both.
3. **ृ (vocalic R matra): promoted to the core matra set**, no longer
   filed under `rare_matras` - `chars.json` updated accordingly. Whether
   it needs its own dedicated recording or fuses into consonant-specific
   shapes (Malayalam's ു/ൂ/ৃ-style precedent) is exactly what Agent 2's
   HarfBuzz verification against the chosen font settles - the
   infrastructure already brute-forces every consonant+ृ combination for
   this reason (`build_glyph_data.py`'s `_consonant_matra_inputs`).
4. **Candrabindu vs. anusvara: both recorded, no normalization.** Confirms
   the first draft's lean - they're phonemically distinct, not two
   spellings of one sound, so unlike chillu's dual encoding this is never
   a lookup-table fix.
5. **Loan vowels/matras (ऍ ऑ / ॅ ॉ): in scope.** Confirms the first
   draft's lean.

## New composition primitives for Agent 3 (found here, generalizable)

Two ideas from resolving #1 and #2 above extend
`docs/LANGUAGE_ONBOARDING_AGENTS.md`'s Agent 3 design beyond what
Malayalam's onboarding needed, and apply to any future language, not just
Hindi:

- **Synthetic strokes** - a mark simple enough to generate procedurally
  (nukta's dot is the concrete case) doesn't need a human-traced recording
  at all, only a real font glyph outline (for the ghost/composition
  geometry). This reduces the labeling set further than "reduce to atoms"
  alone does - some atoms don't need tracing, just synthesis.
- **Self-composition** - a character that's structurally "the same mark,
  twice, offset" (double danda from single danda is the concrete case)
  composes from *its own* recorded stroke rather than needing a separate
  recording or a different mark's recipe. This is the same
  glyph-offset-composition mechanism the pipeline already has
  (`stroke_compose.py`/`tryComposeFromCharacters`), just applied to a
  single repeated atom instead of several different ones.

## Shirorekha (headline) — flagged for Agent 3, not yet verified

**New concern, raised by the project owner during Agent 2's font-report
review, not found by Agent 1's research pass.** Devanagari's shirorekha
(शिरोरेखा) — the horizontal bar running along the top of each letter,
continuing across a whole written word — has no Malayalam equivalent and
none of this profile's sections above account for it.

**The problem it raises for this pipeline specifically**: strokes are
recorded per-character (`tools/stroke-recorder.html` traces one atom's
ghost at a time), then composed left-to-right by advance width
(`resolveSegments`/`tryComposeStroke` in `js/src/index.js`). If each
recorded character's traced strokes include its own headline segment, a
composed word stitches N independently hand-traced segments together —
different tracing sessions, unlikely to agree on exact height/thickness/
slant — producing a visibly broken/uneven line where real Devanagari
handwriting has one continuous stroke.

**Agreed approach (project owner, 2026-09-04): treat the headline as a
synthetic, word-level stroke, not a traced, per-character one** — the same
"synthetic strokes" primitive `profile.md` already identified for nukta
(see "New composition primitives for Agent 3" above), but scoped to the
composed *word*, not a single atom. Concretely: tracers skip the top line
entirely when recording each character's ghost; at render/compose time, one
straight horizontal segment is drawn programmatically spanning the actual
rendered width of the composed word (reusing the same advance-width data
`resolveSegments` already computes for layout), at a height/thickness read
from the font.

**What Agent 3 needs to check before this is safe to build, not just
assumed**: whether Annapurna SIL's (or whichever font is approved) headline
sits at a *consistent* height/thickness across every character in the
reduced atom set — this is exactly the kind of thing `build_glyph_data.py`
already extracts real glyph outlines to check. A single project-wide
constant height only works if the font's own design keeps the bar level
across glyphs (expected — this is normally guaranteed by a well-built
Devanagari font's script design, "I would expect them to work together
cleanly" per the project owner — but unverified here, and exactly the kind
of claim this pipeline's design principle 3, "verification is structural,
not self-reported," exists to catch rather than assume). If heights vary
per-glyph, the synthetic line needs per-glyph height data instead of one
constant, which changes the composition recipe.

**Generalizes beyond Hindi**: this isn't Hindi-specific — it's a
Devanagari-script structural fact (so it also applies when Sanskrit is
onboarded), and Bengali has a related but less consistently unbroken
headline convention, worth checking when Bengali's turn comes. Once Agent 3
actually verifies this against a real font, the finding should be folded
into `docs/LANGUAGE_ONBOARDING_AGENTS.md`'s Agent 3 section as a fourth
named composition primitive (alongside synthetic strokes and
self-composition) — not generalized preemptively here, per this doc's own
"don't generalize before it's actually found" pattern.

## Sources

- [Unicode Devanagari block, compart.com](https://www.compart.com/en/unicode/block/U+0900) — full code point/name table
- [Developing OpenType Fonts for Devanagari Script, Microsoft Typography](https://learn.microsoft.com/en-us/typography/script-development/devanagari) — shaping model, reph/rakaar/half-form/akhand definitions and ordering
- [Hindi orthography notes, r12a.github.io](https://r12a.github.io/scripts/deva/hi.html) — Richard Ishida's (W3C i18n) practical Hindi-specific orthography reference
- [Devanagari, Wikipedia](https://en.wikipedia.org/wiki/Devanagari) and [Devanagari (Unicode block), Wikipedia](https://en.wikipedia.org/wiki/Devanagari_(Unicode_block))
- Nukta-letter usage corroborated across [LangLex](https://langlex.com/tech-talk/10-the-hindi-nukta-characters.html), [aashaan.in](https://www.aashaan.in/blog/20250927-16-learn-hindi-nukta/), and general web search — no single authoritative "official list," hence flagged as an open question rather than stated as settled fact
