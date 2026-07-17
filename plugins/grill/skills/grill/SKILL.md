---
name: grill
description: Use when the user has an idea, feature, or plan they want thought through before building — asks to разобрать/продумать идею, составить план, спроектировать, «погрилль меня», "grill me", or invokes /grill:grill. Also use when a design conversation keeps producing decisions that live only in the chat and would be lost to the knowledge base.
---

# Grill

Interview the user about their idea until every decision is made — and leave behind a document that outlives the chat. Three rules carry the whole skill: facts are yours to find, decisions are the user's to make, and every resolved decision is written into the document the moment it lands — not at the end.

## Session shape

### 1. Frame — one turn

- Restate the idea in one paragraph; list what's known and what you're assuming.
- Look up facts before asking: read the codebase, search the web. Anything discoverable is your job; only genuine decisions go to the user.
- Sketch the decision map — the branches that must be resolved, in dependency order (blockers first). The map is not a design: presenting it costs the user nothing, a full design would pre-empt their answers.
- Create the document now (see The document), `status: draft`, with the map under "Open branches".
- End the turn with the first question.

### 2. Grill — the loop, one decision per turn

- One question per turn = the next open branch. Attach your recommendation and why. When the options are enumerable, the AskUserQuestion tool with the recommendation first works well; otherwise ask in chat.
- Confidence shortens your recommendation; it never skips the question. If you catch yourself writing "here's the design, confirm points 1–4" — that's four questions batched. Back to one.
- Grill means grill: probe contradictions, edge cases, failure modes, terms used loosely. Invent a concrete scenario that breaks the current answer and put it to the user.
- On each answer: write the decision into the document immediately (entry format below), tick it off "Open branches", then ask the next question.
- If the user cuts the interview short ("хватит, давай план"): stop asking. Resolve every remaining branch with your recommendation, record each under "Assumed (not grilled)", and go to Close.

### 3. Close — one turn, when no branches remain open

- Fill Goal, Plan (numbered steps, each with a check criterion), Risks & open questions, Out of scope. Delete "Open branches". Drop any section that has no content. Flip `status: final`.
- In chat: a three-bullet summary, the file path, and the next moves — commit it; in an atomic-wiki project also `/atomic-wiki:ingest <path>`. Mention them, don't run them.
- No implementation during the session. The session ends at the document; building it is the user's next request.

## The document

Exactly one file per session, written in the language the interview is conducted in — section titles included. Location — first match wins:

| Project looks like | Path |
|---|---|
| `raw/` + `atoms/` + `wiki/` at repo root (atomic-wiki project) | `raw/grill/<slug>.md` |
| `docs/` exists | `docs/<slug>.md` |
| anything else | `<slug>.md` in the project root |

Slug: lowercase, hyphens, 3–6 words from the topic. If a draft for the same topic already exists (`status: draft`), resume it — read it, keep its resolved decisions, continue from the first open branch.

```markdown
---
status: draft      # → final at Close
date: <today, YYYY-MM-DD>
---
# <the idea in one line>

## Goal
<for whom, why, what success looks like>

## Decisions
### <the decision in one line>
**Chosen:** <what> — <why>
**Rejected:** <alternative> — <why not>

## Plan
1. <step — how to check it's done>

## Risks & open questions
## Out of scope
## Assumed (not grilled)
## Open branches        <!-- draft only; delete at Close -->
- [ ] <branch>
```

Every Decisions entry must read standalone, out of chat context — one claim plus its rationale; each later becomes one wiki atom, and an entry that needs the conversation to make sense is lost knowledge. A small session collapses naturally: title + Goal + one decision is a complete final document (an ADR) — never pad with empty sections.

## Common mistakes

| Symptom | Fix |
|---|---|
| "I've explored the repo — here's the full design, confirm points 1–4" | The map is presented; branches are walked one per turn. |
| Decisions pile up in chat, document written at the end | Write each decision the moment it's resolved. |
| Asking what Read/Grep/web search would answer | Facts are yours; only decisions go to the user. |
| User said "enough" → grilling continues, or the session just stops | Record the rest as "Assumed (not grilled)", then Close. |
| Final doc has empty boilerplate sections | Sections without content are dropped. |

---

The interview core builds on Matt Pocock's `grilling` skill (MIT).
