---
name: course-authoring
description: Create and publish a narrated AmpUp course end to end - outline, designed slides, spoken talk-track, quizzes, and live roleplay checkpoints - persisted and published through the AmpUp MCP tools. Also turns an uploaded slide deck into a course. Use when someone wants to build a training course, "make a course about X", narrate a deck, or ship a playable, published course to learners.
user-invocable: true
---

# Course Authoring

Build a complete, narrated AmpUp course and persist + publish it through MCP: an outline (objectives, concepts, lessons), designed slides, the spoken talk-track the on-screen instructor reads, and checkpoints (quizzes, roleplays). Everything lives in a `course_plan` object that you send to the AmpUp course tools; there is no web app, no side panel, and no Save button in this flow. You author the plan, you persist it, you publish it.

## AmpUp MCP tools

The AmpUp tools are exposed with the prefix `mcp__plugin_ampup-mcp-plugin_ampup__` (for example, `mcp__plugin_ampup-mcp-plugin_ampup__create_course_from_plan`). This document uses the short names - `create_course_from_plan`, `set_course_plan`, `publish_course`, etc. - and each maps to that prefix. On first use you may be prompted to authorize the server with `/mcp`; approve it once and the tools are live for the session.

## When to use this

Use this skill to author a course from a topic/brief, or to turn a deck the user hands you into a course. Two entry paths:

- **Author from scratch** - you are given a topic, audience, and desired takeaway (or just a company/product). You write the outline, design the slides, write narration, add checkpoints, then create → persist → publish. This is the main path below.
- **From a deck** - the user hands over a slide deck (PPTX/PDF). Call `create_course_from_deck`, which imports the pages as slides; then build lessons + talk-track over those slides with `set_course_plan` and publish. See "Starting from a deck."

## The `course_plan` shape (schema_version "2.1")

One JSON object. You may keep it as a local file for your own bookkeeping while you build, but it becomes real only when you pass it to `create_course_from_plan` / `set_course_plan`.

```jsonc
{
  "module_id": "short_slug",
  "title": "Course title",
  "narration_mode": "audio_only",     // "audio_only" | "talking_head" | "none"
  "schema_version": "2.1",
  "objectives": [ { "id": "obj_1", "label": "What the learner will be able to do" } ],
  "concepts":   [ { "id": "c_1", "label": "Concept name", "objective_id": "obj_1", "primary_slide_id": "s_intro" } ],
  "questions":  [ { "id": "q_1", "stem": "...?",
                    "options": [ {"id":"A","text":"...","correct":true},
                                 {"id":"B","text":"...","correct":false} ],
                    "rationale": "why A is right", "multiSelect": false } ],
  "slides":     [ { "id": "s_intro", "kind": "html", "html": "<div ...>...</div>" } ],
  "lessons": [
    {
      "id": "l_1",
      "title": "Lesson title",
      "concept_ids": ["c_1"],
      "objective_ids": ["obj_1"],
      "beats": [
        { "id": "b_s_intro", "kind": "say", "slide_id": "s_intro",
          "say": "Narration the instructor speaks over this slide.",
          "talking_head_clip_url": "/sales-agents/api/v1/courses/__CID__/beat-audio/b_s_intro" },
        { "id": "bq1", "kind": "quiz", "question_ids": ["q_1"], "mandatory": false, "on_fail": "continue" }
      ]
    }
  ]
}
```

**Beat kinds:**
- `say` - a slide with narration. Needs `slide_id` and non-empty `say` (except in `narration_mode: "none"`). Carries `talking_head_clip_url` with the `__CID__` placeholder (see the persistence sequence).
- `quiz` - a checkpoint. Needs `question_ids` (each must exist in `questions[]`). Set `on_fail: "continue"` unless you also set a `concept_id` on the beat - any other `on_fail` without a concept lands a 422.
- `roleplay` - a live practice scene. Needs `slide_id`, a real `practice_script_id`, `scene`, and `patient: { name, tag, opener }`. Create the script first (see "Roleplay checkpoints").

**ID conventions.** `obj_N` objectives, `c_N` concepts, `q_N` questions, `l_N` lessons. Slides use descriptive slugs: `s_<two_to_four_words>` (for example `s_intro_to_pricing`, `s_objection_handling`) - never bare `s_1`. Beats: `b_<slide_id>` for `say`, `bq<n>` for quiz, `brp<n>` for roleplay.

**Slide HTML is embedded directly** in `slides[].html`. Slides render inside the player's `.course-slide` container. Delegate the actual slide design to the bundled `course-slides` skill and its `slide-designer` subagent (see the "Slides" step under "Phased build"); this skill owns the plan and persistence, not the pixels.

## Phased build

Build in this order. This keeps each phase reviewable and keeps broken references out of the plan.

1. **Outline.** Write `objectives`, `concepts`, `lessons`, and one title-card slide per lesson. Add a `say` beat over each slide with `say` left as a placeholder for now (you fill narration in phase 3). Decide `narration_mode` up front (see "Narration modes").
2. **Slides.** Design each teaching slide via the `course-slides` skill's `slide-designer` subagent - one idea per slide - and place the returned HTML into that slide's `slides[].html`. Commit one aesthetic direction (look, light/dark, accent) before the first slide and reuse it for every slide so the course feels like one deck. Reference `course-slides` for the render contract; do not duplicate it here.
3. **Narration (talk-track).** Fill every `say` beat's `say` with the spoken script - 30 to 80 words per beat, written for the voice (see "House style"). Skip this only for `narration_mode: "none"`.
4. **Checkpoints.** Add `quiz` beats where a concept needs reinforcing (vary which option is correct across questions; do not always make A correct), and `roleplay` beats where live practice fits.

Run the validation checklist below before you persist.

## The create → persist → publish sequence

Once the plan is complete and validated:

1. **(Optional) Pick a face and voice.** For `talking_head`, call `list_talking_head_avatars` and choose an avatar; pass its id as `talking_head_avatar_id`. Always also pass `voice_id` (an ElevenLabs voice) explicitly, so narration works even if the avatar carries no voice of its own. For `audio_only`, pass `instructor_image_url` (a still image) plus `voice_id` - there is no on-camera avatar.

2. **Create the draft.** Call `create_course_from_plan(name, course_plan, ...)`. Beyond `name` and `course_plan`, the optional instructor/voice fields are `talking_head_avatar_id`, `voice_id`, `instructor_id`, `instructor_name`, `instructor_image_url`, `instructor_persona`, and `instructor_description` (pass an existing `instructor_id` to reuse a saved instructor, or the individual `instructor_*` fields to define one inline). At this point every `say` beat's `talking_head_clip_url` still contains the literal `__CID__` placeholder - that is correct. The call returns `{ id, status }` with `status: "draft"`.

```
create_course_from_plan(
  name = "Selling Widgets 101",
  course_plan = <plan with __CID__ placeholders>,
  voice_id = "pNInz6obpgDQGcFmaJgB",
  instructor_name = "Ada",
  instructor_image_url = "https://.../ada.png",     // for audio_only
)
-> { "id": "crs_abc123", "status": "draft" }
```

3. **Swap `__CID__` and re-persist.** Take the returned id (`crs_abc123`), replace every `__CID__` in the plan with it, and call `set_course_plan(course_id, course_plan)` with the substituted plan. This is a required step - without it the beat-audio URLs point at a placeholder and narration never resolves.

```
plan2 = <plan with every "__CID__" replaced by "crs_abc123">
set_course_plan(course_id = "crs_abc123", course_plan = plan2)
```

4. **(Optional) Per-course CSS.** If your slides rely on shared classes rather than inline styles, call `set_course_styles(course_id, css)` - the CSS is scoped to `.course-slide` and capped at 256KB. Omit this entirely when slides are inline-styled.

5. **Publish.** Call `publish_course(course_id)`. This moves `draft` → `published` and re-renders; it is idempotent, so republishing after an edit is safe. An `audio_only` course publishes effectively instantly. Publishing requires real narration on every teaching beat - except `narration_mode: "none"`.

6. **(Optional) Warm the audio.** After publish, call `get_beat_clip_url(course_id, beat_id)` for each `say` beat to pre-generate its narration audio so the first learner does not wait on TTS.

## Narration modes

- **`audio_only`** - a still instructor image plus TTS narration. Set `instructor_image_url` + `voice_id`. Publishes instantly.
- **`talking_head`** - an on-camera avatar reads the narration. Set `talking_head_avatar_id` (from `list_talking_head_avatars`) + `voice_id`.
- **`none`** - a silent, slides-only course. Author slides, quizzes, and roleplays as usual, but leave every `say` beat's `say` as `""`. The learner reads each slide and advances manually. This is the one mode that publishes with empty narration by design; every other mode requires real narration on every teaching beat before publish.

## Roleplay checkpoints

A `roleplay` beat needs a real `practice_script_id`. Create the script first with `admin_create_practice_script(name, scenario, session_script, agent_details{...})` (see the roleplay/practice-script skill for the full field set - `agent_details` carries the agent's `name`, `voice_id`, `first_message`, and description). Use the returned script id as the beat's `practice_script_id`. The beat also needs `slide_id`, `scene`, and `patient: { name, tag, opener }`. Do not invent a script id - a roleplay beat pointing at a non-existent script fails.

## Starting from a deck

When the user hands over a slide deck, base64-encode the file and call:

```
create_course_from_deck(
  name = "Onboarding Deck",
  slides_file_b64 = <base64 of the .pptx/.pdf>,
  slides_filename = "onboarding.pptx",
  keep_slides = true,
  narration_mode = "talking_head",   // or "audio_only" | "none"
  render_mode = "image",             // "image" keeps each page as a fixed image; "live" for reflowed rendering
  voice_id = "pNInz6obpgDQGcFmaJgB",
)
```

- `keep_slides = true` keeps each deck page as a fixed image slide (do not redesign these - they are the deck).
- `keep_slides = false` seeds the deck's text as source material for freshly designed slides instead of keeping the page images.

The returned course has slides but no lessons and no talk-track. Build those next: write `objectives`, `concepts`, and `lessons` whose `say` beats reference the imported slide ids (one `say` beat per slide unless the user says otherwise), then run the same `set_course_plan` (with the `__CID__` swap) → optional styles → `publish_course` sequence. For `keep_slides = true`, write narration over the existing slides; for `keep_slides = false`, design new slides via `course-slides` as in the from-scratch path.

## Validation checklist

The server rejects a malformed plan (and a bad `slide_id` reference lands the course in needs_review / 422). Verify all of these before you persist:

- `slides` is non-empty and `lessons` is non-empty.
- Every slide `id` is unique.
- Every `say` beat's `slide_id` names a real slide, and its `say` is non-empty (except `narration_mode: "none"`).
- Every `quiz` beat's `question_ids` each exist in `questions[]`, and `on_fail` is `"continue"` unless the beat carries a `concept_id`.
- Every `roleplay` beat has a `slide_id` and a `practice_script_id` for a script that actually exists (with a real name / instructions / first_message on it).
- Every `concept.primary_slide_id` and `concept.objective_id` resolve.
- **No orphan slides:** every slide is covered by at least one `say` or `roleplay` beat.
- After create, every `talking_head_clip_url` has had `__CID__` replaced with the real course id (checked before `set_course_plan`).

## House style

Narration is read aloud, so write it for the voice:

- Use `...` for pauses and keep sentences short (15 to 25 words). No em-dashes anywhere.
- Voice tags sparingly - about one every 2 to 3 slides - and only `[sighs]`, `[whispers]`, or `[laughs]`. For example: `[sighs] This is where most teams get it wrong.` No other bracket tags; they get spoken aloud.
- Write numbers and money in spoken form: "one point two million dollars", not "$1.2M".
- No SSML, no XML, no markdown in `say` text.

## Worked example

A tiny two-slide `audio_only` course with one quiz, from plan to published.

**1. The plan (with `__CID__` placeholders):**

```jsonc
{
  "module_id": "widgets_101",
  "title": "Selling Widgets 101",
  "narration_mode": "audio_only",
  "schema_version": "2.1",
  "objectives": [ { "id": "obj_1", "label": "Explain the core widget value prop" } ],
  "concepts":   [ { "id": "c_1", "label": "Value prop", "objective_id": "obj_1", "primary_slide_id": "s_value_prop" } ],
  "questions":  [ { "id": "q_1", "stem": "What do widgets save the buyer most?",
                    "options": [ {"id":"A","text":"Time","correct":false},
                                 {"id":"B","text":"Rework","correct":true} ],
                    "rationale": "Widgets remove the rework loop entirely.", "multiSelect": false } ],
  "slides": [
    { "id": "s_intro",      "kind": "html", "html": "<div class=\"course-slide\">...intro...</div>" },
    { "id": "s_value_prop", "kind": "html", "html": "<div class=\"course-slide\">...value prop...</div>" }
  ],
  "lessons": [
    {
      "id": "l_1",
      "title": "Why widgets",
      "concept_ids": ["c_1"],
      "objective_ids": ["obj_1"],
      "beats": [
        { "id": "b_s_intro", "kind": "say", "slide_id": "s_intro",
          "say": "Welcome. In the next two minutes... you will learn exactly why buyers pick widgets.",
          "talking_head_clip_url": "/sales-agents/api/v1/courses/__CID__/beat-audio/b_s_intro" },
        { "id": "b_s_value_prop", "kind": "say", "slide_id": "s_value_prop",
          "say": "Here is the part that closes deals. Widgets remove the rework loop... completely.",
          "talking_head_clip_url": "/sales-agents/api/v1/courses/__CID__/beat-audio/b_s_value_prop" },
        { "id": "bq1", "kind": "quiz", "question_ids": ["q_1"], "mandatory": false, "on_fail": "continue" }
      ]
    }
  ]
}
```

**2. The tool-call sequence:**

```
# create the draft (placeholders still in place)
create_course_from_plan(
  name = "Selling Widgets 101",
  course_plan = <plan above>,
  voice_id = "pNInz6obpgDQGcFmaJgB",
  instructor_name = "Ada",
  instructor_image_url = "https://.../ada.png",
)  ->  { "id": "crs_abc123", "status": "draft" }

# swap every "__CID__" -> "crs_abc123", then re-persist the whole plan
set_course_plan(course_id = "crs_abc123", course_plan = <plan with crs_abc123 in every clip url>)

# publish (audio_only -> effectively instant)
publish_course(course_id = "crs_abc123")  ->  { "status": "published" }

# optional: warm each say beat's audio
get_beat_clip_url(course_id = "crs_abc123", beat_id = "b_s_intro")
get_beat_clip_url(course_id = "crs_abc123", beat_id = "b_s_value_prop")
```

The course is now published and playable. To change anything later, edit the plan, call `set_course_plan` again, and re-run `publish_course` (it re-renders idempotently).
