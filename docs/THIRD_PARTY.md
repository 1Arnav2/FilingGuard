# Third-party code and assets — FilingGuard dashboard (`web/`)

Every library, copied component and font the dashboard uses, with its source and licence.
Versions are pinned exactly in `web/package.json`. Recorded in Phase 6c (D-076).

## Copied components (source lives in this repo)

| Component | File | Source | Licence | Changes made here |
|---|---|---|---|---|
| shadcn/ui Button, Popover, Dropdown Menu, Sheet | `web/components/ui/{button,popover,dropdown-menu,sheet}.tsx` | `shadcn@4.22.1 add`, style `radix-nova` (https://ui.shadcn.com) | MIT | None |
| Magic UI Number Ticker | `web/components/ui/number-ticker.tsx` | https://magicui.design/docs/components/number-ticker | MIT (Copyright (c) Magic UI) | Shows the exact bound value at rest; counting digits are `aria-hidden` and screen readers get the final value; no animation under `prefers-reduced-motion`; counts once per value, with a timer that always writes the final text |
| Magic UI Border Beam | `web/components/ui/border-beam.tsx` | https://magicui.design/docs/components/border-beam | MIT | Renders nothing under `prefers-reduced-motion`; `aria-hidden` |
| Magic UI Animated Beam | `web/components/ui/animated-beam.tsx` | https://magicui.design/docs/components/animated-beam | MIT | Static path only under `prefers-reduced-motion`; `aria-hidden` |
| Magic UI Bento Grid | `web/components/ui/bento-grid.tsx` | https://magicui.design/docs/components/bento-grid | MIT | Grid container only; responsive columns; its BentoCard is not used (grey body text fails contrast) |

**Aceternity UI: not used.** The owner asked for its Spotlight or grid background on the Overview hero.
Its site calls the free components free to use but names no licence for them (the footer says "All
Rights Reserved"; the licence page covers the paid Pro items). No Aceternity code was copied. The
hero's grid is a two-line CSS background written for this project (`.hero-grid` in
`web/app/globals.css`).

## npm packages

| Package | Version | Licence | Used for |
|---|---|---|---|
| next | 15.5.28 | MIT | Framework, static export |
| react, react-dom | 19.2.9 | MIT | UI |
| radix-ui | 1.8.1 | MIT | Primitives under the shadcn components |
| class-variance-authority | 0.7.1 | Apache-2.0 | Button variants |
| cn | 0.5.0 | MIT | Class-name merging (published by shadcn; replaces clsx + tailwind-merge) |
| lucide-react | 1.61.0 | ISC | Icons |
| motion | 14.5.0 | MIT | Animation for the Magic UI components |
| next-themes | 0.4.6 | MIT | Light / dark / system theme |
| geist | 1.8.1 | SIL Open Font License 1.1 | Geist Sans and Geist Mono, served from the package (no font download at build) |
| tw-animate-css | 1.4.0 | MIT | Enter/exit animations used by shadcn components |
| tailwindcss, @tailwindcss/postcss | 4.3.3 | MIT | Styles (dev) |
| shadcn | 4.22.1 | MIT | CLI and its Tailwind preset CSS (dev) |
| typescript, eslint, eslint-config-next, @eslint/eslintrc, @types/* | see package.json | Apache-2.0 / MIT | Checks (dev) |

Removed in Phase 6c: `recharts` and `react-is` (the outcome bars are plain HTML with text alternatives).

Phase 6c polish and Should tier (D-077): no new packages. The definition tooltip (`web/components/site/Term.tsx`)
is built on the shadcn Popover already listed; the Disclosure, Jump to and glossary are project code.
