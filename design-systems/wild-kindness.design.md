# Wild Kindness — Design System
_"Neon After-Hours" — extracted from the live index.html_

Load this file before designing or editing anything for Wild Kindness.
It is the source of truth for the brand's look; the code follows it, not the
other way around.

## Essence

After-hours neon noir. A dark SF night — deep blue-black, film grain, drifting
stage-light rays in red and gold, everything floating on dark liquid glass.
Confident, cinematic, a little dangerous, never cluttered. One screen, phone
first: the whole page should land above the fold on a 390×844 viewport.

## Color

| Token     | Value                  | Role                                    |
|-----------|------------------------|-----------------------------------------|
| `--black` | `#05070F`              | Base canvas                             |
| `--ink`   | `#0B0F1D`              | Secondary surface                       |
| `--white` | `#FFFFFF`              | Primary text                            |
| `--gray`  | `#888899`              | Secondary text, idle icons              |
| `--red`   | `#E31C1C`              | Signature accent — hover, primary CTAs  |
| `--gold`  | `#F5C518`              | Reward accent — appears on interaction  |
| `--glass` | `rgba(8,10,20,0.55)`   | Card fill under heavy backdrop blur     |

Rules:
- Red is the brand; gold is the payoff. Idle state may hint red; gold only
  appears on hover/active (e.g. red button → gold on hover).
- Never introduce new hues. Tints of the existing palette only.
- Text on glass: white at 85% for labels, `--gray` for meta, full white on hover.

## Backdrop (the stage)

Layered, all `position:fixed`, in z-order:
1. Canvas: radial `#1a1830 → #0a0c1c → #04050c` ellipse high center, over a
   vertical `#05070F → #02030A` linear gradient. `background-attachment:fixed`.
2. Spotlight: blurred radial red→gold glow centered behind the logo,
   `pulse` 6s ease-in-out infinite.
3. Light rays: 4 blurred (40px) diagonal beams, red/gold at ≤0.12 alpha,
   `mix-blend-mode:screen`, drifting 18s ease-in-out, staggered delays.
4. Vignette: radial transparent → `rgba(0,0,0,0.65)` at edges.
5. Film grain: SVG `feTurbulence` tile at 8% opacity, `mix-blend-mode:overlay`,
   above everything, `pointer-events:none`.

## Materials — dark liquid glass

Cards are the only surfaces. Recipe:
- `backdrop-filter: blur(60px) saturate(1.8) brightness(0.95)` over `--glass` fill
- `border-radius: 24px`, no border; the edge is drawn by shadows:
  - `0 0 0 1px rgba(255,255,255,0.15)` clean outer ring
  - `inset 0 1.5px 0 0 rgba(255,255,255,0.3)` top specular highlight
  - `inset 0 -1px 0 0 rgba(0,0,0,0.3)` bottom shade
  - `0 30px 80px rgba(0,0,0,0.5)` drop + `0 8px 20px rgba(227,28,28,0.08)` red bloom
- Diagonal sheen overlay: 135° white gradient at ≤8% alpha, corners only.

## Typography

- Display: **Anton**, uppercase, tight leading, `letter-spacing: 0.04–0.12em`.
  Used for names, buttons, headings. Sized with `clamp()`.
- Body/UI: **Space Grotesk** 300–700. Meta text is small (9–12px), uppercase,
  wide tracking (`0.06–0.22em`), `--gray`.
- Headline treatment: white→lavender-gray vertical gradient via
  `background-clip:text`.

## Layout

- Single column, `max-width: 480px`, centered, 10px gap between cards.
- Header card: centered logo (clamped 100–140px, red/gold drop-shadow glow),
  name, tagline. Links card: full-bleed rows, not pill buttons.
- Link row: icon (28px box) + Anton label + `→` arrow, hairline
  `rgba(255,255,255,0.06)` dividers; first/last rows inherit the card radius.
- Respect `env(safe-area-inset-*)`; padding tightens at ≤480px.

## Motion

Physics over easing curves — motion should feel mechanical-organic, like
window blinds and heartbeats, not CSS demos.
- **Entrance:** "blinds" reveal — each card wrapped, revealed top-to-bottom by
  animating `clip-path: inset(0 0 X% 0)` with a real damped spring
  (k≈180–200, b≈26–28, m≈1–1.2) in rAF, inner content counter-translating;
  180ms stagger between cards. `will-change` set only while animating.
- **Idle:** logo heartbeat (lub-dub scale 1 → 1.025 → 1 → 1.018 → 1, 2.4s);
  rays drift; spotlight pulses.
- **Hover:** rows shift `padding-left` +8px, icon → red, arrow → red +
  `translateX(4px)`; primary rows go gold. 0.2–0.25s transitions.
- Provide a `prefers-reduced-motion` path: no entrance choreography, no
  idle loops; page fully usable static.

## Components

- **Link row** (default): gray icon, 14px Anton label at white 85%, dim arrow.
- **Link row, primary** (contact CTAs): red icon, white label, red-tinted
  hover fill `rgba(227,28,28,0.12)`, gold icon/arrow on hover.
- **NSFW gate** (required for adult-platform links): full-screen overlay
  `rgba(3,4,10,0.92)`, glass modal (blur 40px, 20px radius, red left edge
  accent bar), Anton "Adults Only" heading, red YES button (gold on hover),
  ghost NO button, tiny uppercase legal note. Links open only after consent;
  consent persists for the session. Direct contact (tel/sms) never gated.

## Voice

Uppercase, terse, confident. Labels are 1–3 words ("Call Me", "Text Me").
Meta text separated with `·`. No exclamation marks, no emoji in headings
(emoji allowed as link icons, rendered `grayscale(1) brightness(1.3)`).

## Engineering constraints

- One self-contained HTML file. No build step, no frameworks, no external JS.
- Only external requests: Google Fonts (Anton + Space Grotesk) and the logo
  from `wildkindness-cdn.b-cdn.net`.
- Vanilla JS in a single IIFE. Inline SVG icons, `currentColor` fill.
- Works at 320px wide with no horizontal scroll.
