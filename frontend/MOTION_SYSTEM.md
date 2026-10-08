# Motion system

A small, dependency-free motion layer for DocMind AI. Everything is CSS-first:
React only passes an `index`, the browser runs the entrance on the compositor,
and nothing re-renders to animate.

**No animation libraries were added.** `package.json` is unchanged.

## Files

| File | What it holds |
| --- | --- |
| `app/globals.css` | Easing tokens, keyframes, `.motion-*` utilities, mobile tuning, reduced-motion rules |
| `components/motion/reveal.tsx` | `Reveal`, `MaskReveal`, `DrawRule`, `StaggerScope`, `motionVars` (hook-free, usable in server components) |
| `components/motion/decode-text.tsx` | `DecodeText` / `useDecodeText` / `useMediaQuery` / `useReducedMotion` (client only) |
| `components/motion/page-transition.tsx` | `PageTransition` — keyed route entrance |
| `components/motion/processing-strip.tsx` | `ProcessingStrip` — determinate or sweeping progress hairline |

## Vocabulary

**SETTLE** — `motion-settle`. Content starts ~10px lower at `opacity: 0` and
rises into place on `cubic-bezier(.22,.61,.36,1)`. Used for cards, panels,
nav rows, CTA groups and dashboard widgets.

**MASK** — `motion-mask` inside an `overflow-hidden` parent. Text starts below
the clip and rises out on `cubic-bezier(.16,1,.3,1)`. Reserved for page
headings, major section headings and important result titles — never body copy.

**DRAW** — `motion-draw-x` / `motion-draw-y`. A rule or accent edge scales out
from one edge. Used for the short accent rule under page titles, the sidebar's
active-item indicator, and the top edge of extraction panels.

**STAGGER** — components pass `index={n}`; the delay is composed in CSS as
`index × --motion-stagger + --motion-delay`. The whole initial entrance
resolves inside ~1.1s. `--motion-stagger` is 70ms on desktop and 40ms below
640px, so mobile tightens automatically without touching React.

**DECODE** — `DecodeText`. Character scramble, left-to-right resolve, width
reserved up front so nothing reflows. Used **only** on short uppercase labels
(sidebar section labels, page-header eyebrows). Disabled entirely under
reduced motion and below 640px.

**PAGE TRANSITION** — `motion-page-in`, a 420ms fade + 8px rise, keyed on the
pathname. No exit animation and no loading gate, so the new route is
interactive immediately.

**HOVER** — 200–300ms on `background-color`, `border-color`, `color`,
`box-shadow` and small `translate` moves. No bouncing, spinning or large
scaling.

## Rules the system enforces

- Only `opacity` and `transform` are animated. Never `width`/`height`/`top`/`left`.
  (`Progress` was converted from animated `width` to `scale3d`.)
- Every keyframe ends at `transform: none`, so no element is left with a
  transform that would create a containing block and break `position: fixed`
  descendants (modals, toasts).
- **Never put a `motion-*` class on an element that also relies on a transform
  or opacity utility.** A CSS animation overrides those declarations, so
  `hover:-translate-y-0.5`, `scale-[1.005]` or `opacity-50` would silently stop
  working. Wrap the element in `<Reveal>` instead — this is why the dropzone,
  stat cards and `interactive` cards use wrappers.
- Table rows use the opacity-only `motion-fade`, so rows never move and tables
  cannot jump.
- The only continuously-running loops are the processing sweep and status dot,
  and they exist only while a document is actually processing.

## Reduced motion

`@media (prefers-reduced-motion: reduce)` zeroes `animation-duration`,
`animation-delay`, `transition-duration` and `transition-delay` for everything
(zeroing the delays matters — a 0.001ms animation with a 400ms backwards-fill
delay would still hide content for 400ms).

`.motion-essential` opts functional feedback back in at 1.6s: loading spinners,
the processing sweep, the pipeline progress bar. A frozen spinner reads as a
hung app, so these keep moving — slowly.

`DecodeText` also checks the media query in JS and renders plain text, and
skips the scramble below 640px.

## Mobile

Below 640px: `--motion-distance` drops 10px → 6px, `--motion-stagger`
70ms → 40ms, the in-card stagger 38ms → 24ms, and DECODE is switched off.
