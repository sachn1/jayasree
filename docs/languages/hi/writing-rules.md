# Hindi writing rules

> **Status: agent-researched, not human-verified.** Written 2026-11-23 by an agent, after the strokes were
> recorded, as an audit. A native writer must confirm it before anything is re-recorded.

How Devanagari is written by hand, ranked by source, with a confidence on each rule. Sources are tiered and the
highest tier wins: **T1** official standard, **T2** university course or published manual, **T3** learner site.

## What the sources say

**There is no fixed, universal stroke order.** A learner guide says order does not affect validity ([NepalGo,
T3](https://nepalgo.de/script/writing-the-devanagari-script)). The only official order is a teaching chart.

**The T1 source:** the Central Hindi Directorate's *Devanagari lipi evam Hindi vartani ka manakikaran* (2024 ed.,
[PDF](https://chd.education.gov.in/sites/default/files/devanagarilipiandhindivartanikamankikaran.pdf)), section 2.5
"Hindi varnamala lekhan vidhi", printed pages 15-18. For every vowel and consonant, plus ड़ ढ़ क्ष त्र ज्ञ श्र ळ,
it shows the letter building up step by step, and arrows on the finished letter. Pen lifts are not marked, and
the chart is an image (no text). Its scope is **letters only**: no vowel signs, no conjuncts, no half forms,
no words. (Section 2.6 is a technical-lettering standard, IS 9609, and says nothing on order.)

## Rules

| # | Rule | Confidence | Source |
|---|---|---|---|
| 1 | In a single letter, the **headline is the last step**, drawn left to right | **High** | T1 chart, every letter; T2 [IU](https://iu.pressbooks.pub/hindiscript/?p=279), [UNC](https://taj.oasis.unc.edu/Hindi.Less.25/wrtingsys.htm) |
| 2 | Vertical strokes run top to bottom; the headline runs left to right | **High** | T1 arrows |
| 3 | The **dot of ङ and the nukta of ड़ ढ़** are drawn after the letter's body | **High** | T1 chart p.16 |
| 4 | In a word the headline is one pass, drawn after all its letters | **Medium** | T2 IU; T3 [sublearn](https://sublearn.com/learn/hi/grammar/modern-hindi-manuscripts-6-words). The chart has no words |
| 5 | Some letters have a broken headline (थ ध भ श अ आ) | **High** | T2 UNC; matches our font measurements |
| 6 | For letters with a stem (खड़ी पाई), **the stem is drawn after the bowl or curve**: क ज ल त ... | **High per letter, Medium as a general rule** | T1 chart shows it letter by letter; not stated as a rule |
| 7 | Vowel signs, anusvara, chandrabindu: when drawn relative to their base and the headline | **Unknown** | the chart does not cover them; no T1/T2 source found |
| 8 | Nukta on क़ ख़ ग़ ज़ फ़ is drawn last like ड़ ढ़ | **Low** | an extension of rule 3; not shown |
| 9 | Half forms, conjuncts: order inside them | **Unknown** | no source |

## Audit of the recorded strokes (183 atoms)

Method: each atom drawn with its strokes numbered in recorded order, compared by eye with the T1 chart.
Limits: the chart does not mark pen lifts, so only the order of the *parts* can be compared, and only for
letters the chart shows. About 25 of the 60 letters were compared closely; the rest need a second look.

**Differs from the chart (our stem is recorded first; the chart draws it after the bowl):**
क, ज, ल, त (reading from the scan: clear). ऋ ॠ (hook first in the chart, ours starts with the stem; medium).
The half and conjunct atoms built on these (क् क्ष ज्ञ ...) have the same pattern but the chart cannot judge them.

**Consistent with the chart:** ग च ण म भ य व श ष स ब झ ञ ट ठ ड ङ, and the dots of ङ and the nukta letters
(drawn last).

**Look again:** ख, घ (the chart's step order is hard to read for them).

**Accepted as recorded:** छ has its small tick last, before the headline. The chart draws a tick first; the
recording keeps the tick last.

**Decision:** all of the above, including क ज ल त and ऋ ॠ, are accepted as recorded. Nothing is re-recorded.
The chart is a recommended teaching order, not a rule of the script.

Whether this matters: the order only changes how the animation looks, not what is drawn. A native reader may find
a stem-first क odd. Strokes are re-recorded by a native writer, never by an agent.

## Runtime behaviour (changed)

A nukta, matras and the other marks are written with their letter, and the headline comes last. The runtime
does that: marks keep their composed place after their letter, and the headline is drawn once, at the end of the
word. The recorded strokes are unchanged.

## Questions for the native writer

1. For क ज ल त, do you write the stem first or last? Is that the same across schools and regions?
2. Vowel signs (ि ी ु ू े ै ो ौ ृ) and anusvara/chandrabindu: written right after their letter, or after the whole word and the headline?
3. Is the nukta on क़ ख़ ग़ ज़ फ़ drawn last, like ड़ ढ़?
4. Do you draw the headline per letter or once per word?
5. Does the order inside half forms (क् ...) follow the full letter minus its stem?
