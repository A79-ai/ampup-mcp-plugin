---
name: course-slides
description: Author high-design HTML slides for the AmpUp course player. Pairs the frontend-design craft with the player's hard render contract - a fixed 1280x720 canvas, shadow-isolated rich CSS, self-scaling to fit, and no interaction (the player screenshots and narrates each slide). Emits a single self-contained data-slide-isolated HTML block per slide that course-authoring embeds directly into the course plan. Ships a slide-designer subagent (Opus) that does the actual per-slide design work. Supporting craft skill; not invoked directly by users.
user-invocable: false
---

# Course slide design

This skill authors **course slides** - the visuals the AmpUp player shows while
the avatar narrates. It is a supporting craft skill: the `course-authoring`
skill delegates to it when a course needs designed slide HTML, and
`course-authoring` owns persisting that HTML into the course plan. This skill's
one job is to **produce the slide HTML string**.

It marries two things that pull in opposite directions:

1. **`frontend-design.md`** (read it in full, in this skill directory) - the
   design craft: distinctive typography, a committed aesthetic, atmosphere and
   depth, intentional composition. This is *how a slide should look*.
2. **The render contract below** - the hard constraints of the player the slide
   renders inside. Break these and the slide leaks CSS onto the app, clips, or
   renders blank. This is *what a slide must be*.

`frontend-design.md` is the source of taste; this file is the source of truth
where they conflict.

## Who does what

- The **aesthetic direction** (tone / flavor, light vs dark, the one memorable
  idea) is **chosen up front** and passed in - a course commits to one shared
  font stack, palette, and motif across every slide. You do not re-pick it; you
  execute it, consistently, across the whole course.
- The **design work** runs in the **`slide-designer` subagent** (Opus), one
  slide at a time, so each slide gets full creative attention. See
  `agents/slide-designer.md` in this skill directory. The subagent writes the
  slide HTML; that HTML string is what `course-authoring` embeds into the course
  plan's `slides[].html`.

## The render contract (non-negotiable)

### 1. Fixed 1280x720 canvas
Every slide is authored to fill exactly **1280 by 720** pixels. The player owns
fitting that into the viewport - never assume the on-screen size.

### 2. Rich CSS only inside an isolated slide
A slide is injected into the app's live DOM, so a bare `<style>` block (custom
fonts, `@keyframes`, `::before` layers, gradients) would **leak globally and
corrupt the rest of the app**. To use any real CSS you MUST isolate the slide:
mark the root element with **`data-slide-isolated`**. The player then mounts it
in a shadow root where its `<style>` is fully scoped - put all CSS in a
`<style>` block *inside* the slide root, and nothing escapes.

### 3. Self-scaling wrapper
The player gives the slide a fluid box, so the slide must scale its own fixed
1280x720 design down to fit. Use this exact wrapper; author your design inside
the inner box:

```html
<div data-slide-isolated style="position:absolute;inset:0;overflow:hidden;container-type:size;">
  <div style="position:absolute;top:0;left:0;width:1280px;height:720px;transform-origin:top left;transform:scale(min(100cqw / 1280, 100cqh / 720));">
    <style>
      /* @import MUST be first. Distinctive font, not Inter/Arial/system. */
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@400;700;900&display=swap');
      .sd-root { width:1280px; height:720px; font-family:'Fraunces',serif; /* ...committed palette + design... */ }
      @keyframes sd-rise { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:none; } }
    </style>
    <div class="sd-root"><!-- the 1280x720 design --></div>
  </div>
</div>
```

(`container-type:size` + `cqw`/`cqh` need a current Chromium - fine in the real
player and a modern browser; verify with real Chrome, not old bundled headless.)

**Exactly ONE `data-slide-isolated` root per slide.** The wrapper above is the
*whole slide* - use it once, as the outermost element, and author your design
inside `.sd-root`. Never place a second `data-slide-isolated` element anywhere
inside it: that nests a slide within a slide and renders as a shrunken clone of
itself. A two-column / "versus" comparison is **one** root whose `.sd-root`
contains two side-by-side child columns (plain `<div>`s) - not two slide-roots.
(The attribute may of course appear many times as the CSS *selector*
`[data-slide-isolated] {...}` inside your `<style>` - that's text, not a second
root, and is fine.) The publish gate rejects a slide with more than one root.

### 4. Static - all content visible at rest
The slide is **narrated, not interactive**. No hover-to-reveal, no scroll, no
click-to-advance - the player screenshots and scales it, and any JS is stripped.
Every word and visual must be present without any user action. CSS **entrance**
animations (`@keyframes` on load, staggered with `animation-delay`) are
encouraged for polish; just never gate content behind interaction, and never
rely on scripting for anything the viewer must see.

### 5. One idea per slide
Teach a single concept per slide. Dense decoration, sparse message. Make the
slide's main title a real `<h1>` (style it however you like) - the course
outline labels each step by that heading, so a styled `<div>` title leaves the
step unnamed.

### 6. No overlapping text or stray lines
Text elements must never overlap other text or readable content. Give every
heading, body block, and label enough margin/padding to stand clear of its
neighbors - if two elements could collide at 1280x720, add explicit spacing or
reposition. Decorative/background elements *behind* text (large watermark
numbers, faded shapes) are fine; two readable strings on top of each other are
not.

Keep slides visually clean: no decorative `<hr>`, hairlines, random border
strokes, or underlines that don't serve a structural purpose (e.g. separating a
footer). Every line on the slide should be intentional - if it doesn't frame or
divide meaningful content, remove it.

### 6a. Prefer source figures over recreating visuals
When the task prompt includes **source figure references** (embedded images
extracted from the author's uploaded deck - each with an `image_url`,
`source_page`, and dimensions), **always embed the original image** with
`<img>` rather than recreating the visual. The extracted figure is the author's
actual instrument screenshot / diagram / chart and renders correctly by
definition. Use `object-fit: contain` and appropriate sizing to fit the slide
layout. **Always apply at least 10px padding** around every embedded `<img>` so
edges are never clipped by the slide boundary or adjacent elements. When
multiple candidates are provided, embed the ones that match this slide's concept
and ignore the rest.

Only create visuals from scratch (per 6b below) when no source figure is
available for the concept.

### 6b. SVG for all non-text visuals (gauges, charts, diagrams, shapes)
Any visual element that is **not** plain text or a photograph **must** use
**inline `<svg>`** - never CSS shape tricks. This includes: meter gauges,
progress rings, arc indicators, pie/donut charts, bar charts, flowchart shapes,
icons, badges, circular progress, speedometers, and any custom geometric shape.

**Why**: CSS-based shapes (`border-radius` circles, `clip-path` polygons,
`transform: rotate` arcs, stacked `border` tricks) render unpredictably across
browsers and at different scale factors. SVG is coordinate-based and renders
pixel-perfect at any size.

**Banned patterns** (never use these for visual shapes):
- `border-radius: 50%` to create circles or semicircles for gauges/meters
- `clip-path` for non-rectangular shapes (OK for rectangular image crops)
- `transform: rotate` on `<div>` elements to create arcs or angled shapes
- `border-left` / `border-top` tricks to create triangles or wedges
- `conic-gradient` for pie charts or progress indicators
- Stacking multiple `<div>` elements with `position: absolute` to assemble a
  composite shape (e.g. a gauge needle on a dial)

**Required instead**: inline `<svg>` with explicit coordinates:
```html
<!-- Gauge: arc path + needle line, exact coordinates, no CSS tricks -->
<svg viewBox="0 0 200 120" width="200" height="120">
  <path d="M20,100 A80,80 0 0,1 180,100" fill="none" stroke="#e0e0e0" stroke-width="12" stroke-linecap="round"/>
  <path d="M20,100 A80,80 0 0,1 130,30" fill="none" stroke="#4CAF50" stroke-width="12" stroke-linecap="round"/>
  <circle cx="100" cy="100" r="6" fill="#333"/>
</svg>
```

SVG elements inherit the slide's shadow isolation, so inline `<svg>` inside
`.sd-root` works without any extra wiring.

### 6c. Flexbox/grid for content layout
Use **flexbox** or **CSS grid** for all content layout (text blocks, cards,
columns, image + text pairings). Reserve `position: absolute` for:
- the required `data-slide-isolated` outer wrapper (per section 3)
- decorative background elements (watermarks, faded shapes, ambient textures)

Never use `position: absolute` with hardcoded `top`/`left` pixel values to place
text blocks, headings, labels, or data visualizations - if the content changes
length, absolute placement causes overlap. Flexbox/grid adapts.

### 7. Spoken-narration-safe text
No em-dashes anywhere visible. Write numbers/abbreviations naturally.

### 8. Citations - only when the task asks for them
If the task prompt turns on source citations, every slide that states a
factual/quantitative claim (adoption numbers, pricing, capabilities, named
customers, dated milestones) carries a quiet **footer sources line**; otherwise
add nothing.

Treatment (keep it consistent across the deck):
- One muted, monospace line pinned to the bottom of the slide, left-aligned,
  e.g. `SOURCES  domain.com/path · domain.com/other`, sitting on the slide's
  footer rail. **No inline superscripts, no numbered markers on the claims
  themselves** - a single line per slide, nothing on the content. Each domain is
  a real `<a href="…" target="_blank" rel="noopener">` (clickable; opens a new
  tab).
- Show the short **domain/path label** as the link text (not the raw URL), one
  entry per distinct source the slide draws on (dedupe).
- Keep it dim (a footer treatment, not a focal point): small `JetBrains Mono`,
  low-contrast muted color, a hairline above it. It must never compete with the
  slide's content or overflow the 1280x720 box.

Sourcing rules (non-negotiable - a wrong citation is worse than none):
- Use **only** verified source URLs supplied to the task. **Never invent a URL,
  and never attach a source to a claim it does not actually support.**
- If a claim on the slide has no verifiable source, **do not cite it** - soften
  or drop the claim instead of citing something that doesn't back it. Never put
  words in a named person's mouth (no fabricated/paraphrased "quotes").

## Output

A slide is a single self-contained `data-slide-isolated` block (HTML plus its
inline `<style>`). That HTML string is the deliverable: `course-authoring`
embeds it directly into `course_plan.slides[].html`. Because the shadow root
isolates each slide's `<style>`, per-slide CSS is always safe; course-wide CSS
that every slide shares may instead be hoisted to the plan's top-level
`styles_css`.

The `slide-designer` subagent returns the slide HTML for its assigned slide -
it does not touch persistence, MCP tools, or the plan JSON. Handing the HTML
back to `course-authoring` (which persists it) is the entire integration
surface.

### Optional: local preview
`splice_slides.py` (in this skill directory) is an optional local helper for
previewing a course-plan JSON file - it assigns slide HTML into a plan's
`slides[].html` with correct JSON escaping so you can eyeball a plan locally
without re-emitting the HTML through the model. It is a convenience only; the
canonical persistence path is the AmpUp MCP tools driven by `course-authoring`,
not this script.
