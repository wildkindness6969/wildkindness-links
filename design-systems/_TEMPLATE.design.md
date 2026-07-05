# <Creator Name> — Design System
_"<style codename>" — extracted from the approved Stage-3 direction_

Load this file before designing or editing anything for this creator.

## Essence
<3–5 sentences: the mood in plain words. What night/place/film does this feel
like? What should a visitor feel in the first second? Phone-first or not?>

## Color
| Token | Value | Role |
|-------|-------|------|
| `--bg`     | `#……` | Base canvas |
| `--text`   | `#……` | Primary text |
| `--muted`  | `#……` | Secondary text |
| `--accent` | `#……` | Signature accent |
| `--accent2`| `#……` | Payoff/hover accent |

Rules:
- <when each accent may appear; what is forbidden (e.g. "never new hues")>

## Backdrop
<the stage behind the content: gradients, textures, animated layers, vignette —
list layers in z-order with blend modes and opacities>

## Materials
<what surfaces are made of: glass/paper/metal — exact recipe: fills, blurs,
radii, shadow stack>

## Typography
- Display: <font, casing, tracking, clamp sizes>
- Body/UI: <font, weights, meta-text treatment>

## Layout
<column width, spacing rhythm, card anatomy, safe-area rules>

## Motion
- Entrance: <choreography + implementation approach>
- Idle: <ambient loops, if any>
- Hover/press: <micro-interactions>
- Reduced-motion path: <what remains>

## Components
<each reusable block: default link row, primary CTA, gates/modals, footer…
For adult-platform links, include the NSFW gate pattern and its rules.>

## Voice
<casing, label length, punctuation, emoji policy>

## Engineering constraints
- One self-contained HTML file, no build step.
- Allowed external requests: <fonts, CDN assets — enumerate exactly>
- Works at 320px wide with no horizontal scroll.
