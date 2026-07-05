---
name: design-site
description: Run the creator site design pipeline (WORKFLOW.md) for a creator — from references and brief through image synthesis, page build, motion pass, and gated ship. Usage: /design-site <creator-name> [stage]. Use when asked to design, redesign, or build a page for a creator.
---

# design-site

Execute the pipeline defined in `WORKFLOW.md` for the creator named in the
arguments. Read `WORKFLOW.md` first — it is the source of truth for stages
and gates; this skill is the runbook.

## Setup

1. Read `WORKFLOW.md`; parse `AUTONOMY_LEVEL` (1 = gates A–D, 2 = B+D, 3 = D).
   Gate D always applies.
2. Slugify the creator name (`wild-kindness`). Check what exists:
   - `briefs/<slug>.md` → Stage 2 done if Gate A checked
   - `design-systems/<slug>.design.md` → Stages 3–4 done
   - `references/<slug>/` → Stage 1 material
3. Resume at the first incomplete stage, or at the stage passed as an
   explicit second argument.

## Gate protocol

At each gate required by the autonomy level, stop and use AskUserQuestion
with concrete options (e.g. the 3 direction names at Gate B). Present visual
evidence before asking: send screenshots/mockups with SendUserFile. Record
gate outcomes in the brief's Status checklist. At skipped gates, note the
decision made autonomously and continue.

## Stage runbooks

### Stage 1 — References
Ask the user to drop screenshots if none exist (this is the one stage that
genuinely needs user input at any autonomy level for a brand-new creator).
Store in `references/<slug>/`. If the web is reachable, also pull relevant
style ideas from styles.refero.design / getdesign.md into
`design-systems/inspiration/`.

### Stage 2 — Brief
Fill `briefs/_TEMPLATE.md` from everything known. Draft 2–3 structure
outlines (section order, above-the-fold contents) as short labeled lists.
**Gate A** presents the outlines as options.

### Stage 3 — Directions
Produce 3 distinct visual directions of the approved structure:
- Preferred inside Claude Code: spawn 3 parallel agents, each builds a
  throwaway single-file HTML mockup with a named aesthetic bet (give each a
  codename). Screenshot each at 390×844 and 1440×900 using the bundled
  Chromium (`/opt/pw-browsers/chromium`) — serve the file with
  `python3 -m http.server` and capture via Playwright.
- If the user prefers the ChatGPT-images path, emit the prompt pack (brief
  summary + structure + reference list, phrased for an image model,
  requesting 3 styles) and wait for them to drop the outputs into
  `references/<slug>/directions/`.

### Stage 4 — Choose
**Gate B**: send the direction screenshots, ask which wins (offer remix as an
option). Then write `design-systems/<slug>.design.md` from the winner using
`design-systems/_TEMPLATE.design.md` — fill every section with concrete
values (hex, px, timing), not vibes. Commit the design system.

### Stage 5 — Build
Load brief + design system. Build `<codename>.html` (root for Wild Kindness,
`sites/<slug>/` for other creators) as one self-contained file. Then the
screenshot loop, minimum 2 iterations:
1. Serve + screenshot 390×844 and 1440×900.
2. Self-review against the design system section by section (color, type,
   materials, layout) and the winning mockup.
3. Fix, re-screenshot; stop when a pass finds nothing to fix.
Acceptance: everything above the fold at 390×844, no horizontal scroll at
320px, safe-area insets respected.

### Stage 6 — Motion
Separate pass, separate commit. Follow the design system's Motion section:
entrance choreography, hover states, idle loops, all with a
`prefers-reduced-motion` fallback. Re-run the screenshot loop after.
**Gate C**: send final screenshots for sign-off.

### Ship
Run the QA checklist from WORKFLOW.md (links, gating of adult platforms,
320px, page weight). Commit the page to the feature branch and push.
**Gate D (never skipped)**: ask before any commit that promotes the page to
`index.html` / production. Update the brief's Status checklist.

## Conventions

- Single-file HTML, no build step, vanilla JS. External requests only as
  enumerated in the creator's design system.
- Commit per stage with messages like `Stage 4: codify <codename> design system`.
- Never push to `main` directly; never overwrite `index.html` without Gate D.
