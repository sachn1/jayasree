---
name: onboard-language
description: >
  Orchestrates jayasree's multi-agent language-onboarding pipeline
  (docs/LANGUAGE_ONBOARDING_AGENTS.md) end to end for one Indic script:
  Agent 1 research -> human sign-off -> Agent 2 font selection -> human
  sign-off -> Agent 3 atom reduction. Detects which stage a language is
  already at and resumes from there instead of restarting. Use when the
  user says "/onboard-language <name>", "onboard <language>", "start
  onboarding <language>", or asks to run the language-onboarding pipeline
  for a new or in-progress language. Not for ad-hoc single-stage requests
  ("just re-run Agent 2") - those still go straight to the matching
  subagent (font-selector, etc.) without this skill.
---

This skill is a thin orchestrator. It does not restate the pipeline - read
`docs/LANGUAGE_ONBOARDING_AGENTS.md` in full before doing anything else,
same as every agent in `.claude/agents/` already does. If this file and
that doc ever disagree, the doc wins; fix this file to match, don't act
against it.

## What this skill actually does that isn't already automatic

Spawning the four pipeline agents (`language-researcher`, `language-reviewer`,
`font-selector`, `atom-reducer`) already works without this skill - it's
what's been happening in this conversation by hand. What a skill adds:

1. **A single entry point** (`/onboard-language <language>`) instead of the
   user needing to know the agent names or which stage comes next.
2. **A hard-enforced sign-off gate**, not an advisory one. Each agent's own
   description says "use only when explicitly asked, for a language whose
   profile/font already has human sign-off" - that's a note to whoever is
   orchestrating, not something the agent itself checks. This skill is the
   thing that actually enforces it: never invoke Agent 2 or Agent 3 without
   first getting an explicit, real sign-off message from the user in *this*
   conversation. A prior commit message, a doc header, or your own belief
   that something "seems fine" is not sign-off - if in doubt, ask.
3. **Resume detection**, so re-invoking this skill for a language already in
   progress doesn't redo finished work.

## Procedure

### 0. Identify the language and current stage

Determine the target language (from the skill's arguments, or ask if not
given). Check `docs/languages/<code>/` for what already exists:

- No `profile.md` -> start at Stage 1.
- `profile.md` exists, status header says "pending sign-off" or similar,
  and the user hasn't signed off in this conversation -> stop and ask for
  sign-off before doing anything else (don't re-run Agent 1 just because
  it's unsigned - re-running redoes real research work for nothing if the
  draft is actually fine).
- `profile.md` signed off, no `font-report.md` (or it's stale relative to
  a signed-off profile revision) -> Stage 2.
- `font-report.md` exists but its recommendation hasn't been signed off ->
  stop and ask, same as above.
- Font signed off, no (or stale) `labeling-worklist.md` /
  `glyph-data.<code>.json` -> Stage 3.
- Everything present and current -> nothing left for this skill to do;
  say so and point at the labeling worklist for the actual (human,
  unautomatable) stroke-tracing work.

Never assume "the files exist, so it's approved" - existence means a
*draft* exists. Only an explicit human sign-off in conversation clears a
gate.

### 1. Stage 1 - research (if needed)

Spawn `Agent(language-researcher, ...)` per `docs/LANGUAGE_ONBOARDING_AGENTS.md`'s
Agent 1 section, giving it the language name and pointing it at the "Don't
generalize from Malayalam" section so it profiles the script on its own
structural terms.

Then spawn `Agent(language-reviewer, ...)` against the draft - this is the
review gate the plan itself requires before a human ever sees the draft,
not optional polish.

Present the reviewed draft profile to the user and **stop**. Summarize the
open questions the reviewer raised. Do not proceed until the user
explicitly signs off (approves as-is, or approves with named corrections
you then apply).

### 2. Stage 2 - font selection (only after Stage 1 sign-off)

Spawn `Agent(font-selector, ...)` against the signed-off `profile.md`/
`chars.json`, per Agent 2's section of the plan.

Present the recommendation (and runner-up, if any) to the user and
**stop**. Do not wire the font into `python/src/jayasree/languages.py` or
invoke Agent 3 until the user explicitly signs off on a specific font.

### 3. Stage 3 - atom reduction (only after Stage 2 sign-off)

Spawn `Agent(atom-reducer, ...)` against the signed-off font choice, per
Agent 3's section. This is the stage that actually wires the registry
entry, regenerates `glyph-data.<code>.json`, and produces the labeling
worklist - it's allowed to write code/data, unlike Stages 1-2's review
gates.

Report back what was generated and where the labeling worklist lives.
**Recording strokes by hand is never this skill's job** - that's
`tools/stroke-recorder.html`, a human task, per `CLAUDE.md`'s hard rules.

## Hard boundaries (same ones every pipeline agent already has)

- Never touch Malayalam's files (`python/src/jayasree/_chars.py`,
  `js/src/stroke-data.raw.json`, `python/tests/test_chars_malayalam.py`).
- Never hand-edit a generated data file; only the dedicated tools/agents
  regenerate them.
- One language at a time, per the plan's own target-roster ordering -
  don't fan this skill out across multiple languages in parallel.
