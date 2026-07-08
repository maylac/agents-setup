# DESIGN.md — App Design Quality Standard

Load this before designing or implementing any user-facing UI (web app, mobile app, dashboard, landing page). This file governs process, tokens, and the quality bar. Specialized skills own their niches (§14). Written for agent consumption: rules are imperative, values are concrete, and the Never list is as binding as the Do list.

## 0. Prime Directive

**Intentionality over intensity.** Every interface commits to ONE nameable aesthetic point of view and executes it precisely. Refined minimalism and loud maximalism both win; timid, direction-less "modern and clean" always loses. The enemy is not ugliness — it is *distributional convergence*: the statistical-median UI (Inter, purple gradient, three feature cards, evenly-spaced boxes) that every generative model produces by default. If you cannot name the aesthetic in 3 words, it does not have one.

**Spend your boldness in one place.** One signature element executed flawlessly (a type moment, a background system, one orchestrated animation, a command palette) beats ten accumulated effects.

## 1. Mandatory Process

Never skip straight to code. In order:

1. **Product brief** (2–4 sentences, written down): what the product does, who uses it, the UI's single job, and the emotional tone as exactly 3 adjectives ("calm, precise, trustworthy" / "loud, playful, fast").
2. **Ground in the subject's world**: pull vocabulary, materials, and visual references from the domain itself (a finance tool borrows from ledgers and terminals; a kids' app from toys and stickers) — not from generic SaaS.
3. **Pick ONE aesthetic direction** from §2, or remix two ("Linear structure × editorial type"), or invent one. Never default silently. Never reuse the previous project's direction — rotate deliberately (anti-convergence).
4. **Lock tokens before components**: fonts, palette, spacing scale, radius personality, motion constants — as CSS variables / theme config first. Every token gets *intent + boundary*, not just a value (see §4).
5. **Build**, then **self-review** against §13 before declaring done.

**For any repo-based app**: materialize steps 1–4 as a project-local `DESIGN.md` (brief → direction → tokens with intent → don'ts) so later sessions inherit the decisions instead of re-deriving them.

## 2. Aesthetic Direction Catalog

Pick one and commit. Shape language / typography energy / color stance:

| Direction | Shape & space | Type | Color |
|---|---|---|---|
| **Refined minimal** | Generous whitespace, hairline rules, radius 0–4px | One quiet sans, tabular numerals, extreme weight contrast | Near-mono palette, 1 scarce accent |
| **Editorial / magazine** | Asymmetric grid, big margins, columns & rules | Display serif (opsz) + readable sans | Paper tones, ink text, 1 editorial red/blue |
| **Dark technical** (Linear school) | Dense, keyboard-first, 1px white/8% borders, glow | Sans + mono for ALL data/meta | `#08090A`–`#121216` layers, off-white text, 1 accent w/ glow |
| **Brutalist raw** | Exposed grid, hard edges, no shadows, radius 0 | Oversized grotesque, weight 900 vs 100 | Flat solids, 1px black borders, primaries |
| **Soft organic** | Large radii 16–24px, overlap, blobs | Rounded humanist sans | Warm tinted neutrals, desaturated pastels, tinted shadows |
| **Luxury / refined serif** | Symmetry, thin rules, letterspaced caps labels | High-contrast serif + tiny caps sans | Cream/charcoal + gold or deep green; never bright blue |
| **Playful / toy** | Chunky radii, thick borders, sticker shadows | Rounded display + geometric sans | Saturated triad on light ground |
| **Retro-futuristic** | Grain, scanlines, CRT glow | Extended/condensed display + mono | Dark ground, phosphor green/amber/magenta |
| **Industrial utilitarian** | Data-dense tables, visible structure, zero decoration | Condensed sans, small sizes, UD fonts | Grey scale + safety orange/yellow |

Caveats from the field (2026): bento grids and the full Linear glow-and-grid look are themselves becoming templates — use their *techniques* (§6) inside your own direction, don't clone the whole costume.

## 3. Typography

- **Exactly two families**: characterful display + workhorse body. Add mono only for code/data. Pair by contrast of structure, harmony of proportion (match x-height/width, contrast style). Superfamilies (IBM Plex Sans+Serif, DM Serif+DM Sans) are the zero-risk version.
- **Banned as the visible brand face**: Inter, Roboto, Arial, Helvetica, system-ui, Open Sans, Lato (fallback stacks fine). Also avoid the second-order convergence picks: Space Grotesk, Poppins, Montserrat, default Geist.
- **Rotation pools** (pick per project; don't repeat the last pick):
  - Display serif: **Fraunces** (SOFT/WONK axes), Newsreader, Instrument Serif, Libre Caslon Text, Spectral, Zilla Slab
  - Display sans: Bricolage Grotesque, Syne, Unbounded, Archivo (Expanded), Anybody, Familjen Grotesk
  - Body sans: Manrope, Hanken Grotesk, Schibsted Grotesk, Instrument Sans, Albert Sans, Figtree, Public Sans; accessibility-first: Atkinson Hyperlegible, Lexend
  - Mono: JetBrains Mono, IBM Plex Mono, Space Mono, Fragment Mono, Spline Sans Mono
- **Use variable fonts** (one WOFF2, free intermediate weights, animatable weight). Keep `font-optical-sizing: auto` — never pin `opsz` manually.
- **Hierarchy through weight and color before size** (Refactoring UI): 3 text colors (primary dark / secondary grey / tertiary lighter) + 2 weights cover most UIs. De-emphasize the competition instead of enlarging the star.
- **Extremes, not increments**: hierarchy through weight 100↔900 (not 400/600) and size jumps of 3×+ for hero vs body. Timid 1.5× jumps read as generated.
- **Labels are a last resort**: let data self-describe ("12 left in stock", not "In stock: 12"); when needed, label small and muted, value prominent.
- **Scale**: 12 / 14 / 16 / 18 / 20 / 24 / 30 / 36–40 px (in rem), ratio ~1.25 for app UI, 1.333 for marketing. Body ≥16px long-form, ≥14px functional UI. Line-height inverse to size: 1.5–1.6 body → 1.1 display. Letter-spacing: −0.01 to −0.025em at 24px+; +0.02–0.05em for caps labels (≥11px).
- **Fluid hero only**: `clamp()` with a rem-inclusive slope, max ≤ 2.5× min (WCAG resize). Dense app UI keeps a static scale.
- **Numbers**: `font-variant-numeric: tabular-nums` in tables/metrics; metrics and code always mono. Micro-labels: all-caps mono with letter-spacing is a strong current idiom.

### Japanese text

- Body line-height **1.7–1.9** (never Latin 1.5), letter-spacing 0.02–0.05em; UI labels may drop to 1.4–1.5.
- **No italics** (use weight/size/color). No faux bold — load real weights. `font-feature-settings: "palt"` headings only, never body. `text-wrap: balance` / `word-break: auto-phrase` on headings.
- Fonts: Noto Sans JP (safe default), **Zen Kaku Gothic New** (warm, the best "not Noto" pick), IBM Plex Sans JP (technical), LINE Seed JP (friendly product, self-host), BIZ UDGothic (accessibility); display mincho: Shippori Mincho, Zen Old Mincho.
- **Performance**: JP webfonts are multi-MB — load one JP webfont for headings, system stack for JP body (`"Hiragino Kaku Gothic ProN", "Yu Gothic UI", Meiryo`), `font-display: swap`.
- **Mixed JP/Latin**: Latin face FIRST in the stack (`"Manrope", "Zen Kaku Gothic New", sans-serif`) so Latin/numerals render from the Latin face; harmonize with `size-adjust`/`font-size-adjust` (Latin ~5–10% larger than JP at equal optical size). Measure: 35–42 full-width chars/line.

## 4. Color

- **Work in OKLCH** (`oklch(L C H)`), Tailwind v4 / shadcn native. Perceptually uniform L means palettes and dark mode become arithmetic, and contrast survives hue swaps.
- **Palette recipe**: ① one brand hue H → ② 11-step scale varying L on a fixed curve (≈0.97→0.20), C peaking ~0.15–0.20 mid-scale and tapering at both ends → ③ **neutrals = same hue at C 0.005–0.02** (tinted grey — never pure grey) → ④ status hues (success≈145, warning≈85, danger≈25, info≈240) sharing the same L/C curve for equal weight → ⑤ one sharp accent. **Accent power comes from scarcity** — realistic app distribution is ~90% neutral / 8% secondary / 2% accent (the 60-30-10 rule is a smell test, not a formula).
- **Semantic tokens, always** (shadcn vocabulary; surface + `-foreground` pairs so contrast is enforced once, at token definition):
  `background/foreground`, `card/card-foreground`, `popover/popover-foreground`, `primary/primary-foreground`, `secondary/…`, `muted/muted-foreground`, `accent/…`, `destructive/…` + add `success/warning/info` pairs, plus `border`, `input`, `ring`, `chart-1…5`, `radius`. Name by role, never by value. Components never touch primitives.
- **Every token gets intent + boundary** in the project design spec, e.g.: `primary — CTAs and active states only. Never a background, never decorative. One per screen.`
- **Dark mode construction**: bg **never pure black** — L≈0.14–0.18 (+brand hue at C≈0.01). **Elevation = lightness, not shadow**: base 0.15 → card 0.19–0.21 → popover 0.23–0.25 (steps of ~0.03–0.04). Cut accent chroma 20–30% and raise L vs light mode. Text L≈0.93–0.97 (not white) / secondary ≈0.72 / disabled ≈0.55. Borders replace shadows: 1px at ~+0.07 L or `white/8–12%`. Redefine `chart-*` for dark. `color-scheme: light dark` on `:root`; light on `:root`, dark on `.dark`; set theme class before first paint.
- **Define the full palette up front** (8–10 neutrals, 5–10 brand shades, semantic sets) — never generate shades ad hoc with lighten/darken. In OKLCH the fixed-ΔL trick mirrors Material's HCT tone arithmetic (tone Δ40 ⇒ ≥3:1, Δ50 ⇒ ≥4.5:1): encode contrast into the scale once.
- **Never grey text on colored backgrounds** — hand-pick a same-hue color with adjusted L/C; reduced-opacity white looks washed out.
- **Contrast**: design with APCA (Lc 90 body / 75 min body / 60 large / 45 headlines / 30 placeholder / 15 borders), **certify WCAG 2.x** (4.5:1 body, 3:1 large/UI) — where they disagree, satisfy both. The most common violation is `muted-foreground` — check it in both themes.
- **Banned**: purple→blue gradient hero on white; gradient text on multiple headings; timid all-grey palettes with no committed hue; shadcn-grey + Tailwind-blue defaults; teal-accent reflex; rainbow equal-weight palettes.

## 5. Space & Layout

- **4px base scale, super-linear**: 4, 8, 12, 16, 24, 32, 48, 64, 96, 128 — adjacent steps ≥25% apart so choices are decidable. Every margin/padding/gap from the scale. Section gaps go big (64–96px): few large deliberate gaps beat many medium ones.
- **Start with too much whitespace, then remove** — dense-by-default reads unstyled. **Don't fill the screen**: reading content 600–800px; sidebars fixed width, main content flexes.
- **Proximity encodes hierarchy**: gap within a group < gap between groups (8 inside, 24–32 between). Uniform 16px everywhere kills grouping — the most common generated-UI spacing failure.
- **Whitespace is a material**: per direction, generous negative space OR controlled density — never uniform medium. Vary section padding; identical section rhythm reads as template.
- **Cards borderless-first**: separate by whitespace → then 3–5% background-lightness shift → then soft elevation → 1px border as *last* resort. **Never the colored 3–4px left-border strip** (the single most reliable AI tell) except for true semantic status.
- **One deliberate grid-break per view**: an overlap, edge bleed, asymmetric offset, or rotation — one, executed cleanly.
- **Reading measure**: 65–75ch Latin, 35–42字 JP. Center-everything layouts are banned; commit to a grid with tension.
- **Radius personality — pick ONE**: sharp (0–2px), soft (8–12px), or round (16px+/pill), with a tiny vocabulary of 3–5 values (Linear ships exactly three: 6 buttons / 12 cards / pill). Derive from one `--radius` variable shadcn-style. Nested radii: inner = outer − padding (concentricity — now formalized in Apple's HIG).
- Container queries (`container-type: inline-size`) over viewport queries for reusable components.

## 6. Depth, Background, Texture

- **Backgrounds are layered systems, never flat default expanses.** The proven dark-technical stack (adapt per direction): ① radial gradient base (top-glow or vignette) → ② noise/grain at 1.5–4% opacity → ③ 1–2 large blurred color blobs anchored to the focal point → ④ optional grid/dot overlay at 10–20% opacity: `background-image: linear-gradient(rgba(0,0,0,.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,.05) 1px, transparent 1px); background-size: 24px 24px;`. Light-mode equivalents: paper tint, faint geometric pattern, soft radial warmth.
- **Shadow-as-border**: `box-shadow: 0 0 0 1px rgba(0,0,0,.08)` (light) / `0 0 0 1px rgba(255,255,255,.07)` (dark) — no box-model impact, smooth transitions. Stack layers with jobs: 1px ring + tight key shadow + wide ambient + `inset 0 1px 0 rgba(255,255,255,.05)` top highlight ("glow from within").
- **Shadows are tinted** with the background hue, **two parts** (large soft "direct light" + tight dark "ambient occlusion"; shrink the tight part as elevation rises), low opacity. Fix ~5 elevation levels up front — never ad-hoc shadows. Never one heavy black blur. Dark UIs: hairline borders + 4 stepped surface lightnesses do the elevation work, not shadows.
- **Glass (`backdrop-filter: blur(6–12px)`)**: navs and overlays only (15–30% FPS cost), always with a 1px light border + solid fallback. Liquid-Glass-style refraction (SVG `feDisplacementMap`) is a signature-moment budget item, not a default.
- Texture matches direction: grain for retro/organic, hard pattern for brutalist, nothing for refined minimal. Decorative gradient orbs floating behind heroes = banned (slop tell).

## 7. Motion

- **Budget: UI animation ≤300ms; interaction feedback ≤200ms.** Durations: press feedback 100–160 · hover/color 150–200 · tooltips 125–200 · dropdowns 150–250 · modals 200–300 · drawers/sheets 200–400 · page transitions 300–400. Enter longer, **exit faster** (~½ enter). Nothing UI-blocking >500ms.
- **Easing decision tree**: enter/exit screen → ease-out (`cubic-bezier(0.23, 1, 0.32, 1)`); move/morph on screen → ease-in-out (`cubic-bezier(0.77, 0, 0.175, 1)`); hover/color → `ease`; constant motion (spinner/marquee) → `linear`; iOS-feel sheets → `cubic-bezier(0.32, 0.72, 0, 1)`. **Never `ease-in` for UI** (exception: fast exits ≤200ms). Never default `ease` for everything.
- **Springs** for gesture-driven UI (drag, sheets — interruptible, velocity-preserving): Motion `{ type: "spring", duration: 0.5, bounce: 0.2 }`; bounce 0.1–0.3; visible overshoot only for reward moments.
- **Frequency rule — when NOT to animate**: actions used 100+×/day (command palette, context menus, keyboard-triggered) get **no** animation; occasional actions get standard; first-run/hero gets delight. Never animate keyboard-initiated actions or theme switches.
- **One orchestrated page-load** (stagger 30–80ms, ease-out, translateY 8–16px + fade, cap total) beats scattered micro-effects. Stagger first load only, never repeated interactions.
- **Compositor only**: animate `transform`/`opacity`; never width/height/top/left/padding. Pause looping animations off-screen.
- **Scroll-driven** (CSS `animation-timeline: view()` + `animation-range: entry`, `@supports` fallback) and **View Transitions** (`document.startViewTransition`, `view-transition-name` morphs, `@view-transition { navigation: auto }` for MPA) as progressive enhancement.
- **`prefers-reduced-motion`: reduce, don't remove** — swap movement for opacity/crossfade, keep feedback; gate `startViewTransition`; pause autoplay. It's a vestibular medical accommodation.

## 8. Component Quality Bar

Every interactive component ships **all states**: default / hover / active-press / focus-visible / disabled / loading / empty / error. Unstyled states are unfinished work.

- **Press**: `:active { transform: scale(0.96–0.98) }`, 100–160ms. Dialogs enter from scale 0.95–0.98 + fade — never from 0.
- **Hover**: gate with `@media (hover: hover) and (pointer: fine)`. Never change font-weight on hover/selected (layout shift). Tooltips animate the first show, appear instantly while "warm". Popovers get origin-aware `transform-origin` (trigger side).
- **Focus**: style `:focus-visible` (not bare `:focus`): `outline: 2px solid var(--ring); outline-offset: 2px` (or box-shadow following the radius). Never `outline: none` without replacement. Set `scroll-padding` for sticky headers (WCAG 2.4.11 focus-not-obscured).
- **Loading (NN/g)**: <1s → show *nothing* (a skeleton flash is worse); 1–10s → skeleton for full-page/known layout, spinner for a single small module; >10s → determinate progress with steps. Skeletons mimic final layout (no shift). Streams render progressively.
- **Optimistic UI**: acknowledge input <100ms (press state or local update), sync in background, roll back with visible error. Toggles apply instantly. Feedback appears near its trigger (inline "copied ✓", highlight the invalid field).
- **Empty states are designed**: what this space is for + one primary action (+ direction-consistent illustration). Never a blank region, never a dead end.
- **Errors**: what happened + what to do next; color reinforces, never carries alone.
- **Button action pyramid**: exactly ONE solid high-contrast primary per view; secondary = outline/muted; tertiary = link-style. Destructive is *not* automatically big and red — secondary treatment + red confirmation step is usually right.
- **Forms**: visible labels above (placeholders ≠ labels), validate on blur not keystroke, inputs ≥16px on mobile (prevents iOS zoom), Enter submits (wrap in `<form>`), errors summarized on attempt.
- **Data density**: tables offer comfortable (44–48px rows) vs compact (32–36px); numbers right-aligned, tabular, mono.
- **Keyboard**: composite widgets = one Tab stop + arrow keys inside; `⌘K` command palette for keyboard-centric apps (ARIA combobox + fuzzy match) — and render kbd hints as bordered pill chips.

## 9. AI-Product UI Patterns

(For chat/agent apps.) Message stream capped at **720–768px** measure; left rail ~240px collapsing <1200px; artifact/citation panel slides in on demand; mobile: bottom-docked composer, 44px targets.

- **Streaming is a trust mechanism**: first token <800ms; render the user's message optimistically; batch token paints in 30–60ms windows.
- **Six message states, each with distinct UI**: queued (pulse/shimmer) · thinking (collapsible, honest labels — "Searching web") · streaming (caret) · complete (reveal actions + timestamp) · error (cause + one recovery action, never a generic toast) · stopped (keep partial output, offer continue/regenerate).
- **Streaming markdown hygiene**: buffer half-open syntax (`**bold` must not break layout); code blocks render plain until the closing fence, then highlight; copy button only on completed blocks.
- Trust: numbered citations for factual claims; model name labeled per message; always a stop button; never fight the user's scroll-up with auto-scroll.
- `aria-live="polite"` on assistant messages; `⌘Enter` send / `Shift+Enter` newline.

## 10. Platform Baselines (native mobile)

- **iOS 26 / Liquid Glass**: two layers — content opaque and scrollable, controls/navigation float in glass; never glass on content, never glass-on-glass; use the Regular material variant (Clear only over media, with dimming); corners concentric with hardware. Body 17pt (floor 11pt), use Dynamic Type text styles end-to-end, system tracking. Targets 44×44pt; respect safe areas; content scrolls edge-to-edge under bars.
- **Android / M3 Expressive**: color via roles from a seed (HCT tonal palettes; never raw hex on components); type scale with "emphasized" variants for hero moments only; radius tokens 4/8/12/16/28/full; motion = springs, not curves — spatial springs may bounce, effects springs (color/opacity) never bounce a fade. Targets 48dp. Expressive scheme for consumer moments, Standard for dense/productivity surfaces.

## 11. Accessibility Floor (non-negotiable)

WCAG 2.2 AA: contrast per §4 · **targets ≥24×24px** (comfortable: 44 iOS / 48 Material) · focus visible and not obscured · every drag has a single-pointer alternative (2.5.7) · no re-entry of known info (3.3.7) · full keyboard reachability, logical order, no traps · no color-only meaning (pair icon/text/shape, 3:1 for UI states) · icon-only controls get `aria-label` · alt text on meaningful images · `prefers-reduced-motion` respected · semantic HTML before ARIA (`button`, `nav`, `main`, ordered headings).

## 12. Anti-Slop Banlist (Never)

Each item is an instant tell of generated UI:

1. Inter/Roboto body + purple→blue gradient hero on white.
2. Badge-above-H1 centered hero → exactly three feature cards (icon-title-blurb) → logo strip → pricing → FAQ. The canned skeleton.
3. Emoji or oversized centered Lucide icons as feature icons.
4. Untouched shadcn/Tailwind defaults (`rounded-2xl shadow-lg p-6`, grey-100 + blue-500) with no re-theming.
5. The colored 3–4px left-border strip on cards (non-semantic).
6. Gradient text on multiple headings; neon glowing borders everywhere.
7. Glassmorphism on every surface without layering rationale.
8. Floating purple gradient orbs / stock 3D blobs behind heroes.
9. Uniform 16px spacing between all elements; "cardocalypse" over-boxing; every section centered with equal padding.
10. Identical fade-in on every element instead of one orchestrated moment.
11. Permanent dark mode as reflex (choose per product, design both).
12. Reflexive bento grid; wholesale Linear-look cloning.
13. "Modern, clean design" with no nameable direction.
14. Same direction/fonts/palette as the previous project in this environment (anti-convergence).
15. `outline: none`, hover-only affordances on touch, color-only state.

## 13. Pre-Ship Self-Review

Run before declaring UI work complete; fix failures first:

- [ ] **Squint test** — one focal point per view; hierarchy survives blur.
- [ ] **Direction test** — the aesthetic named in 3 words; every screen answers to it; boldness spent in one place.
- [ ] **Memorability** — the one detail a user would describe to a friend exists. If not, add it.
- [ ] **Token audit** — zero colors/sizes/durations outside declared scales; no raw literals in components.
- [ ] **States audit** — hover/focus/disabled/loading/empty/error all present.
- [ ] **Contrast audit** — body + muted text, both themes (APCA-design, WCAG-certify).
- [ ] **Keyboard pass** — tab the whole flow; focus always visible; palette/shortcuts work.
- [ ] **Responsive pass** — 375 / 768 / 1280+; no horizontal scroll; ≥24px targets (44 on mobile).
- [ ] **Both themes** — light and dark each look *designed*, not inverted.
- [ ] **Reduced-motion pass** — nothing breaks; feedback survives.
- [ ] **Anti-slop pass** — screen §12 items one by one.
- [ ] **Delete pass** — remove one decorative element that doesn't serve the direction; if nothing is removable, the design is probably timid — recheck direction commitment.

## 14. Delegation Map

- Charts, dashboards, KPI tiles → `dataviz` skill (palette validator + mark specs).
- Mobile screen flows/navigation → `mobile-app-ui-design` skill.
- Presentations → `frontend-slides` / open-slide skills; one-off artifacts → `artifact-design`.
- Distinctive implementation push → `frontend-design` plugin skill (persona + boldness rules; consistent with this file).
- This file wins on: process (§1), direction (§2), tokens (§3–7), quality bar (§8–13).
