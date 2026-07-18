---
name: instructor-brand
description: Extract and apply a brand/design system to a course instructor. Reads an uploaded template (a PPTX deck or a JSX/TSX/CSS styleguide), pulls its design tokens (color, typography, spacing, canvas), settles the few genuinely ambiguous choices through a short interview, and saves the result to that instructor's brand_template. Use when a user wants their courses to inherit a consistent look, wants to "brand" or "restyle" an instructor from a deck or styleguide, or wants every course an instructor builds to share the same colors, type, and layout.
user-invocable: true
---

# Give a Course Instructor a Brand

You turn an uploaded brand template (a slide deck `.pptx`, or a styleguide `.jsx`/`.tsx`/`.js`/`.ts`/`.css`) into a reusable design system for one course instructor. You extract the template's design tokens, settle the few genuinely ambiguous choices through a short interview, and save the result to that instructor's `brand_template`. Every course that instructor builds then inherits the same colors, type, and spacing.

## AmpUp MCP tools

The tools below are exposed with the prefix `mcp__plugin_ampup-mcp-plugin_ampup__`. This doc uses their short names:

- `list_course_instructors` -> `mcp__plugin_ampup-mcp-plugin_ampup__list_course_instructors`
- `get_course_instructor` -> `mcp__plugin_ampup-mcp-plugin_ampup__get_course_instructor`
- `extract_brand_tokens` -> `mcp__plugin_ampup-mcp-plugin_ampup__extract_brand_tokens`
- `update_course_instructor` -> `mcp__plugin_ampup-mcp-plugin_ampup__update_course_instructor`

On first use in a session the MCP connection may need authorizing; if a call reports the server is not connected, run `/mcp` and approve access, then retry.

## The one rule

You augment an EXISTING instructor. You never create one. Name, face, and voice belong to the Identity Studio; you only add the visual brand on top. Your one persistence action is `update_course_instructor(instructor_id, brand_template=...)`. If the user has no instructor yet, tell them to create one in the Identity Studio first. Do not attempt to create an instructor here, you have no basis to pick a face or voice.

## Flow overview

1. Resolve the target instructor.
2. Extract tokens from the uploaded template.
3. Inspect the per-field confidence and ask ONLY the low-confidence / consequential decisions, batched into a single interview.
4. Persist the settled `brand_template`.
5. Confirm what the instructor's courses will now look like.

Say one short sentence before any slow step (extraction, a tool call) so the chat is never silent.

## Step 1 - Resolve the instructor

- If the request already names an instructor (a name, or an `instructor_id`), use it directly. Call `get_course_instructor` to read its current state, including any existing `brand_template` you would be replacing.
- Otherwise call `list_course_instructors`. It returns `{items}` with each instructor's name, bio, persona, face, voice, and usage counts. If exactly one exists, confirm it in one sentence and proceed. If several, ask which one with a single `AskUserQuestion` whose options are the instructor names. If none exist, stop and tell the user to create an instructor in the Identity Studio first.

## Step 2 - Extract the design tokens

`extract_brand_tokens` is stateless: it reads a template and returns tokens, it persists nothing. Provide EXACTLY ONE source, plus the target `instructor_id` and optionally a brand `name`.

Two ways to point it at the template:

- **By datasource id (default, required for real decks).** The user uploads the file with `upload_file`, which returns a `datasource_id`. Pass `datasource_id=<that id>`. The server reads the uploaded blob itself. A real `.pptx` is megabytes, so never base64 a deck. Always reference it by its datasource id.
- **By inline base64 (small styleguides only).** For a tiny hand-written styleguide with no datasource id, pass `template_file_b64=<base64>` and `template_filename=<name.css>`. Never use this path for a deck.

Passing `instructor_id` together with a PPTX `datasource_id` also kicks off an async server render of the deck's exact layout frames (title / section / content), cached on the instructor so its courses can drop content into the real template layout. This is read-shaped: the frames are not returned to you and you do not handle them, they land on the instructor out of band. Inline styleguides get no frames.

The tool returns `tokens` with `color`, `typography`, `spacing`, and `canvas`. Each field carries a `confidence` block (`high` | `medium` | `low`) and evidence (the actual fonts, colors, and sizes found). The interview gates on that confidence. If extraction fails (unsupported type, corrupt file), tell the user plainly what went wrong and ask for a valid template, do not retry the same bytes.

## Step 3 - Interview only the low-confidence fields

Gate on confidence and consequence. Ask ONLY the decisions whose predicate is true, and batch them all into ONE `AskUserQuestion` call (its `questions[]` holds several at once) so the user settles the whole brand in a single pass. Build each question's options from the evidence, offer what the template actually contains, never invented colors or fonts. Never ask about a field the template already states with high confidence.

Why the gating matters: a styleguide declares its tokens explicitly, so they come back high-confidence and you ask almost nothing. A "design-system" PPTX often keeps a stock Office theme, so usage-inferred fields (accent, theme, display font) come back low-confidence and are worth a question.

- **Scope.** Ask unless the user already stated it. "Lift the design system" (default) reuses colors/type/spacing on freshly designed slides; "keep these exact layouts" reproduces the template's compositions. Record the preference only, the layout builder is a separate later capability.
- **Accent color.** Ask only if the accent confidence is `low` or the inferred accent is a neutral (a grayscale deck). Offer "stay monochrome" plus each saturated hex from the evidence; the user may also type a hex.
- **Theme.** Ask only for a PPTX source, where light-vs-dark is inferred, not declared. Default to the inferred background.
- **Display font.** Ask only if the title-font confidence is `low`/`medium` and it differs from the body font. Offer to keep the headline font or match the body font for a single family.
- **Logo (skippable).** Ask unless the user already addressed it. Offer "skip for now" (default) / "I'll add one later". Record the preference only, do not upload anything.

Never ask about any high-confidence `color`/`typography` field, about `spacing`, or about `canvas`. If the user's message already answers every gated decision, skip `AskUserQuestion` entirely and go straight to persisting.

## Step 4 - Persist the settled brand_template

Merge the extractor's `tokens` with the interview answers into one object:

- Start from the returned `tokens`, keeping `spacing`, `canvas`, evidence, and every high-confidence field as-is.
- Overwrite the fields the user answered (accent, background/text, title font).
- Add the scope mode and the logo preference (`null` for now).
- For each field the user confirmed, flip its `confidence` to `"high"` so a later re-run does not re-ask.

Then persist once: `update_course_instructor(instructor_id=<id>, brand_template=<the merged object>)`. `brand_template` is design metadata, so this succeeds even while courses using the instructor are already published, it does not touch baked narration. Do this as ONE write at the end of the interview, not field-by-field.

## Step 5 - Confirm

In one or two sentences, tell the user what their instructor's courses will now look like: the palette (with the settled accent), the display and body fonts, and light or dark, grounded in the actual values you saved. Mention they can re-run this with a new template to change it.

## What a good brand_template looks like

A settled `brand_template` is a compact tokens dict, roughly:

- `color`: `background`, `textOnBackground`, `accent`, plus any secondary/surface colors the template declared.
- `typography`: `titleFontFamily`, `bodyFontFamily`, a `fontPairing` label, size scale, and a `titleFontNeedsEmbed` flag when the headline font is not an obvious system font (embedding is a later capability, just record the flag).
- `spacing` and `canvas`: kept as extracted, high-confidence, not interviewed.
- `mode`: `"system"` or `"layouts"` from the scope question.
- `logoUrl`: `null` until a logo capability lands.
- `confidence`: every interviewed field flipped to `"high"`.

Keep it as saved design metadata. Talk to the user about colors and fonts, never about raw token JSON, base64, or confidence internals. Do not use em-dashes in anything the user reads, use a comma, a semicolon, or a sentence break.
