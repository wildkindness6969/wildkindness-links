# Creator Site Design Runbook — Portable Edition

**What this is:** a self-contained, step-by-step workflow for designing a
link-in-bio / landing page for a creator using AI, with human approval at the
points where taste matters. Everything you need is in this one file — no
other repo or tooling required. Paste it into any AI coding assistant
(Claude Code, Claude.ai, Cursor, ChatGPT) as the operating instructions, or
follow it by hand.

Based on @vikingmute's "How to Do Design with AI"
(x.com/vikingmute/status/2073394398973595965), hardened into a gated
pipeline. First project: **Supreme**.

**Roles:**
- **Operator** (you, Hermes): runs the stages, drives the AI.
- **Creator** (Supreme): supplies info and references, approves at gates.

**The one rule:** the AI does the mechanical work; a human makes every
taste decision. Never let a stage auto-advance past a gate.

---

## Pipeline overview

| Stage | What happens | Gate |
|-------|--------------|------|
| 1 | Collect design references | — |
| 2 | Collect creator info → brief + structure | **A: creator approves brief** |
| 3 | Synthesize references + brief into 3 mockup directions | — |
| 4 | Choose the winning direction, write it down as a design system | **B: creator picks** |
| 5 | Turn the winner into a real page | — |
| 6 | Add motion / interactions | **C: creator signs off on final look** |
| — | QA + ship | **D: creator approves going live (never skipped)** |

---

## Stage 1 — Collect design references

Ask the creator for 3–6 screenshots of sites/pages/posters whose *look* they
love (from styles.refero.design, getdesign.md, other creators' pages,
anywhere). Also collect their existing brand assets: logo, photos, any
colors/fonts they already use, links to their current pages.

Save everything in one folder (`references/`). For each reference, note one
line: what about it they love (the type? the color? the mood?). That note is
worth more than the image.

## Stage 2 — Brief (structure before visuals)

Fill this in with the creator — it's the PRD. **Do not generate any imagery
until this is approved.**

```
# <Creator> — Brief

## Who
- Name / handle:
- What they do (one line):
- Where traffic comes from (which platform bios):

## Content to showcase — above the fold, in order:
1.
2.
3.

## Links
| Label | URL | Priority | Age-gated? |
|-------|-----|----------|------------|

- Contact methods (tel/sms/Signal) are primary and never gated.
- Adult-platform links (OnlyFans etc.) MUST sit behind an 18+ confirm
  overlay; consent persists for the session.

## Vibe
- 3–6 adjectives:
- References (the Stage-1 folder, with the one-line notes):
- Hard NOs (styles/colors/moods to avoid):

## Constraints
- Page type: link-in-bio (single screen, phone first)
- Must fit above the fold on a 390×844 viewport
- One self-contained HTML file, no build step
```

Have the AI draft **2–3 alternative structure outlines** (section order,
what's above the fold). **GATE A:** creator picks one and confirms the brief.

## Stage 3 — Synthesize into 3 visual directions

Feed the image model (ChatGPT images works well) this prompt, attaching the
reference screenshots:

```
You are designing a link-in-bio page for <creator>: <one-line identity>.
Vibe: <adjectives>. Hard NOs: <nos>.
Page structure, top to bottom: <approved structure>.
Attached are reference designs they love — for each: <the one-line notes>.

Generate 3 DIFFERENT visual directions for this exact structure as
phone-screen mockups (9:19.5 portrait). Make them genuinely distinct bets
(e.g. one dark/cinematic, one bold/graphic, one minimal/luxe — derive the
bets from the references, don't default to these). Give each a two-word
codename. Real UI, not abstract art: show the actual sections, buttons,
and text hierarchy.
```

Alternative if the operator's AI can code: have it build 3 throwaway
single-file HTML mockups instead (same brief, one aesthetic bet each) and
screenshot them on a 390×844 viewport. Same decision artifact.

## Stage 4 — Choose and codify

**GATE B:** show the creator all 3 side by side. They pick one, or ask for a
remix of two. Then — this is the step most people skip and regret — have the
AI write the winner down as a **design system markdown file** before any real
page is built:

```
# <Creator> — Design System ("<codename>")

## Essence — the mood in 3–5 sentences
## Color — table of tokens: hex, role, rules for when accents may appear
## Backdrop — the layers behind content (gradients/texture/animation), in order
## Materials — what cards/surfaces are made of: exact fills, blurs, radii, shadows
## Typography — display + body fonts, casing, tracking, clamp() sizes
## Layout — column width, spacing rhythm, card anatomy, safe-area rules
## Motion — entrance, idle, hover; must include a prefers-reduced-motion path
## Components — link row, primary CTA, 18+ gate modal (if needed)
## Voice — casing, label length, punctuation, emoji policy
## Engineering constraints — single HTML file; enumerate every allowed
   external request (fonts, CDN logo) — nothing else loads from outside
```

Concrete values only — hex codes, px, timing — not vibes. This file is the
durable source of truth; the mockup image is just its illustration.

## Stage 5 — Turn it into a page

Prompt for the coding AI:

```
Load the design system below and the winning mockup image. Build the page
as ONE self-contained HTML file: inline CSS/JS, vanilla JS only, no build
step, no frameworks. External requests: only what the design system's
Engineering constraints allow. Follow the design system section by section —
where the mockup and the design system disagree, the design system wins.
Acceptance: everything above the fold at 390×844; no horizontal scroll at
320px; safe-area insets respected.
```

Then the **screenshot loop** (this is where quality comes from): open the
file at 390×844 and 1440×900, compare against the design system and mockup,
list what's off, fix, re-screenshot. Repeat until a pass finds nothing.
If the AI can screenshot itself, make it run this loop; otherwise you
screenshot and paste back.

## Stage 6 — Motion pass

Separate pass after the layout is right. Small-scale, refined animation
only: an entrance choreography, hover states, maybe one idle loop
(transitions.dev is the taste bar; gsap or motion if warranted, vanilla CSS
springs are fine). Everything decorative, nothing required to use the page,
and a `prefers-reduced-motion` fallback that disables the choreography.

**GATE C:** creator sees final screenshots (+ a screen recording if motion
is central) and signs off.

## QA + Ship

QA checklist, never skipped:
- [ ] Every link opens correctly; external links `target="_blank" rel="noopener"`
- [ ] Adult-platform links open only after the 18+ overlay is confirmed
- [ ] No horizontal scroll at 320px wide; test on a real phone
- [ ] Only the allowed external requests appear in the network tab
- [ ] Page usable with JavaScript animations disabled

Host anywhere that serves a static file (GitHub Pages, Netlify, Cloudflare
Pages, existing domain). **GATE D:** the creator approves the exact version
that goes live. Keep the old page until the new one is confirmed working.

---

## Hand results back to the library

This workflow runs out of a shared reference archive that gets smarter with
every project (wildkindness-links repo, `references/INDEX.md`). When you're
done, send Jordan:
1. The reference screenshots + the one-line notes (they get archived and
   tagged for reuse),
2. Which direction won and which two lost (win/loss records steer future
   direction generation),
3. The final `design.md` and HTML file.

Second time anyone runs this, Stage 1 starts from the archive instead of
from zero — that's the whole point.
