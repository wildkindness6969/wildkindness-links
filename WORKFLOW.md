# Creator Site Design Workflow

A semi-automated pipeline for designing link-in-bio / landing sites for
creators, run by Claude Code with human approval at critical points.

Adapted from @vikingmute's "How to Do Design with AI" thread
(x.com/vikingmute/status/2073394398973595965). The pipeline:

1. **Collect** web design references
2. **Collect** information about the subject (the creator)
3. **Synthesize** the two into mockup images (ChatGPT images)
4. **Choose** the best synthesis
5. **Turn** the winner into a page
6. **Add** the interactive layer

Vikingmute's closing point — "it's all about that eye for beauty; that's
basically a talent" — is the human's job here: taste lives at the approval
gates. Everything mechanical is automated.

Run it with the `/design-site` skill, or follow the stages manually.

---

## The core idea

Instead of re-explaining a creator's vibe every session, each creator gets
three durable artifacts:

1. **A brief / PRD** (`briefs/<creator>.md`) — who they are, what links, what
   content to showcase, page structure, constraints.
2. **A design system** (`design-systems/<creator>.design.md`) — colors, type,
   materials, motion, and voice as plain markdown the AI loads before touching
   any code.
3. **A reference folder** (`references/<creator>/`) — screenshots of styles
   they like, plus the chosen mockup images from Stage 3.

Once those exist, "build me a new page" becomes a one-line prompt and the
output stays on-brand without supervising every pixel.

---

## Autonomy dial

Set the current level here. The `/design-site` skill reads this file and only
stops at the gates your level requires. Dial it down as trust builds.

```
AUTONOMY_LEVEL: 1
```

| Level | Name        | Gates that stop for approval          |
|-------|-------------|---------------------------------------|
| 1     | Hands-on    | A, B, C, D (all of them)              |
| 2     | Checkpoints | B (pick direction), D (ship)          |
| 3     | Final-only  | D (ship) only                         |

Regardless of level, **Gate D never auto-passes** for anything that overwrites
`index.html` on `main` — a human always approves what goes live.

---

## Pipeline

### Stage 1 — Collect design references
- Browse styles.refero.design and getdesign.md for looks that fit; save
  screenshots into `references/<creator>/` and grab matching `design.md`
  files into `design-systems/inspiration/`.
- The creator dropping screenshots of sites they love works just as well.
- Returning creator with an approved design system → skip to Stage 5.

### Stage 2 — Collect subject information
- Copy `briefs/_TEMPLATE.md` → `briefs/<creator>.md` and fill it in: identity,
  links, content to showcase, page structure, hard NOs, constraints.
  **Structure before visuals** — decide what's above the fold now, generate
  no imagery yet.
- Claude drafts 2–3 alternative structure outlines to choose between.
- **GATE A:** approve the brief + chosen structure.

### Stage 3 — Synthesize into images
- Claude assembles a **prompt pack**: brief summary + approved structure +
  reference screenshots + any `design.md` inspiration, phrased for an image
  model, asking for **3 distinct style directions** of the same structure.
- Default path (per the tweet): run the pack through ChatGPT images and drop
  the outputs into `references/<creator>/directions/`. Alternate path when
  staying inside Claude Code: 3 parallel agents build throwaway single-file
  HTML mockups, screenshotted at 390×844 and 1440×900 with the bundled
  Chromium — same decision artifact, no external tool.

### Stage 4 — Choose the best synthesis
- **GATE B:** the 3 directions are presented side by side; human picks one
  (or asks for a remix of two).
- The winner is codified into `design-systems/<creator>.design.md` using
  `design-systems/_TEMPLATE.design.md` — this file, not the image, becomes
  the durable source of truth.

### Stage 5 — Turn it into a page
- Load brief + design system + winning image, build the production page as a
  single self-contained HTML file (repo convention: no build step, Google
  Fonts + inline CSS/JS only).
- Run the **screenshot loop**: serve, screenshot mobile + desktop, compare
  against the design system and the winning mockup, fine-tune the subtle
  details, repeat until it self-reviews clean. Above-the-fold at 390×844 is
  the acceptance bar — these pages open from phone bios.

### Stage 6 — Add the interactive layer
- A dedicated motion pass after the layout is right: small-scale, refined
  animations that make the page pop — entrance choreography, hover states,
  micro-feedback. Keep the repo's vanilla-JS spring pattern (see
  `index.html`), or gsap/motion where a page warrants it; transitions.dev is
  the reference bar for subtlety.
- Respect `prefers-reduced-motion`; animations are decorative, never required.
- **GATE C:** final screenshots (plus a GIF if motion is central); human signs
  off on the finished feel.

### Ship (always gated)
- Automatic QA, never skipped:
  - Every link resolves, correct `target`/`rel`; adult-platform links go
    through the NSFW gate pattern (see design system → Components).
  - No horizontal scroll at 320px; safe-area insets respected.
  - Single-file page weight sanity check (external requests limited to fonts
    + CDN assets enumerated in the design system).
- Work lands on a feature branch as `<name>.html`; promotion to `index.html`
  is a separate, deliberate commit (see repo history for the pattern).
- **GATE D (always):** human approves the commit that goes live.

---

## File layout

```
briefs/
  _TEMPLATE.md              # intake form / PRD for a new creator
  wild-kindness.md          # the first creator (this site)
design-systems/
  _TEMPLATE.design.md       # structure for a new design system
  wild-kindness.design.md   # extracted from the live neon-after-hours page
  inspiration/              # design.md files grabbed from getdesign.md etc.
references/
  <creator>/                # style screenshots
  <creator>/directions/     # Stage-3 mockup images
.claude/skills/design-site/ # the /design-site skill that runs this pipeline
WORKFLOW.md                 # this file (autonomy dial lives here)
index.html                  # the live page
```

## Adding a new creator later

1. `/design-site <creator-name>` — the skill sees there's no brief and starts
   at Stage 1.
2. Approve at whatever gates your autonomy level requires.
3. Their site lives at `sites/<creator>/index.html` (the root `index.html`
   stays Wild Kindness).
