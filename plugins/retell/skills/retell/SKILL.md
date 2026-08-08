---
name: retell
description: >
  Use when the user wants to check whether they understood a source rather than
  get a summary of it — they hand over a video, article, paper or file and want
  to retell it from memory, be quizzed on it, have their understanding verified
  ("did I get this right?", "проверь, правильно ли я понял", "check what I
  remember"), or invoke /retell:retell. Also use when studying a source for
  retention and the takeaways should end up in a wiki in the user's own words.
---

# Retell

Extract the source into atoms, verify the source holds up, then interview the user on what they
remember — and rewrite those atoms in their voice from their answers.

Two rules carry the skill:

- **The atoms stay hidden until the interview is over.** They exist in the repo from step 2 on; the
  user must not see them, or recall collapses into recognition and the session is worthless.
- **The interview changes voice, never claims.** A misunderstanding is reported to the user; it is
  never written into the wiki.

Conduct the session in the user's language.

## Preconditions

Needs an atomic-wiki repo — `raw/`, `atoms/`, `wiki/` at the git root. Missing? Say so and point at
`/atomic-wiki:init`. Do not improvise a layout.

## Session shape

### 1. Capture — one turn, no content

| Source | Action |
|---|---|
| YouTube URL | Use the `youread` skill; its worker writes `raw/<channel>/<video>/` |
| Other URL | Fetch it, save to `raw/read/<slug>.md` |
| File already in the repo | Use it in place |

If the capture worker's report hands you a summary, it stays out of chat. Announce only: source
title, length, saved path.

### 2. Extract and verify — no content

Run `/atomic-wiki:ingest` over the captured note. Ingest extracts atoms and runs its own factcheck
pass over them; let it. Nothing here reaches the user except the gate verdict below.

### 3. Gate — is the source worth studying?

No point interviewing someone on a video that is wrong. Read the factcheck verdicts and decide:

- **❌ on the atoms the source's thesis rests on** → the source fails. Stop.
- **❌ outnumbering ✅ overall** → the source fails. Stop.
- **❓ could-not-verify** is not failure. Fresh research, niche topics and opinion atoms are
  routinely unverifiable; only refuted claims count against the source.

The gate report is **counts only** — `18 атомов: ✅15 ⚠️2 ❌1` plus a one-line call. Quoting a single
failed claim leaks the content and ends the exercise. The one exception: when the gate **fails**,
give the full factcheck report — there is no interview left to protect, and the user needs to see
why the source was thrown out.

Gate passed → invite the retelling. Gate failed → the user decides whether to bin the atoms or keep
them flagged; either way the session ends here.

### 4. Free recall — the user's turns

- Wait. No hints, no leading questions, no corrections mid-stream.
- They may add across several turns. Move on only when they signal they are done.
- If they ask a content question while retelling, answering breaks the test for that point — answer,
  then mark it revealed. A revealed point never counts as recalled.

### 5. Fill the gaps — one question per turn

Match the retelling against the atom set. Every atom is covered, contradicted, or untouched. Ask
about the untouched ones, one per turn.

**A question names the atom's topic, never its claim.** "What did it say about batching latency?"
opens recall. "Did it say batching raises latency?" hands over the answer and destroys the atom's
value as a test.

If more than ~8 atoms are untouched, ask about themes rather than grinding through one turn each.
If the user calls it ("хватит", "давай итог"), stop asking — the rest are simply not recalled.

### 6. Rewrite the atoms — one turn

Each atom already exists; the interview decides what happens to it:

| The user | The atom |
|---|---|
| recalled it correctly | rewritten in their words, from their answer — claim unchanged |
| recalled it imprecisely | rewritten in their words, claim corrected to the source |
| got it wrong | untouched — the source's claim stands; the error goes in the report |
| never recalled it | untouched, plus `tags: ["recall-gap"]` |

These atoms were created this session and never committed, so they stay `version: 1` no matter how
much the text changes — the pre-commit hook compares against HEAD.

The retelling itself is not saved anywhere: its content is now in the atoms, and a second copy would
be a duplicate of the same knowledge in the same voice.

Close with the report — what was ⚠️ imprecise and ❌ wrong, each with the source segment that
decides it, plus the tally and the list of `recall-gap` atoms.

### Gates that stay the user's

`youread` and `atomic-wiki:ingest` each refuse to run the other unasked; invoking `/retell` is that
ask, so you drive the chain. Two decisions remain theirs: a new atom branch needs approval, and
nothing is committed without it.

## Common mistakes

| Symptom | Fix |
|---|---|
| Gate report quotes what failed | Counts only — details only when the gate fails |
| Ingest's per-atom factcheck report shown before the interview | It is the answer key; it ships in step 6 |
| "Did the video say X?" | Name the topic, never the claim |
| Interview starts after the first paragraph | The user says when they are done, not you |
| The user's wrong answer rewritten into the atom | Voice bends to the user, claims never do |
| `version:` bumped while rewriting | Never committed → stays 1 |
| Unrecalled atoms deleted | They stay, tagged `recall-gap` |
