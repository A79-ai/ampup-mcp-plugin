# AmpUp MCP Plugin

A [Claude Code](https://code.claude.com) plugin that bundles the **AmpUp MCP
connector** with a set of skills for authoring AmpUp **roleplays** (practice
scripts) and **courses** (narrated, slide-based training with quizzes and live
roleplay checkpoints).

Every skill drives AmpUp entirely through **MCP tools** - there is no direct API
access, no bundled scripts, and no API keys or keystore. Install the plugin,
authenticate the connector once via OAuth, and the authoring skills are ready in
any Claude Code session.

- **Marketplace:** `A79-ai/ampup-mcp-plugin`
- **MCP server:** `https://app.ampup.ai/mcp` (Auth0 OAuth, interactive)
- **License:** MIT

---

## Table of contents

- [What you get](#what-you-get)
- [Requirements](#requirements)
- [Install](#install)
- [The bundled MCP connector](#the-bundled-mcp-connector)
- [MCP tool prefix](#mcp-tool-prefix)
- [Skills](#skills)
  - [roleplay](#roleplay)
  - [course-authoring](#course-authoring)
  - [course-editing](#course-editing)
  - [instructor-brand](#instructor-brand)
  - [course-slides](#course-slides-supporting)
- [Data models](#data-models)
- [Design principles](#design-principles)
- [Verified end to end](#verified-end-to-end)
- [Pointing at another environment](#pointing-at-another-environment)
- [Using AmpUp on claude.ai or ChatGPT](#using-ampup-on-claudeai-or-chatgpt)
- [Repository layout](#repository-layout)
- [Development and maintenance](#development-and-maintenance)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## What you get

| Skill | Creates / edits | Auto-invoked when the user wants to... |
|---|---|---|
| [`roleplay`](#roleplay) | Practice-script roleplay scenarios (buyer persona, scenario, opener, evaluation metrics) | "create a cold-call roleplay", "build an interview practice scenario", "edit that practice script" |
| [`course-authoring`](#course-authoring) | A complete narrated course, created and published | "make a course on X", "turn this deck into a course", "build onboarding training" |
| [`course-editing`](#course-editing) | Edits to a drafted course's slides and talk-track | "rewrite slide 2's narration", "shorten this talk-track", "fix that quiz" |
| [`instructor-brand`](#instructor-brand) | A brand / design system for a course instructor | "brand this instructor from our deck", "use this styleguide for our courses" |
| [`course-slides`](#course-slides-supporting) *(supporting)* | High-design slide HTML for the player | delegated to automatically by `course-authoring` |

Plus the bundled **`ampup` MCP server**, which exposes AmpUp's CRM, roleplay, and
course tools to Claude.

---

## Requirements

- **Claude Code** v2.1+ (plugin + bundled-MCP support).
- An **AmpUp account** with access to at least one organization. Authoring
  courses additionally needs a talking-head avatar or a saved instructor in the
  org (both are created in the AmpUp app; `list_talking_head_avatars` /
  `list_course_instructors` surface them).
- A browser for the one-time OAuth sign-in.

---

## Install

```bash
# 1. Add this repo as a plugin marketplace
/plugin marketplace add A79-ai/ampup-mcp-plugin

# 2. Install the plugin
/plugin install ampup-mcp-plugin@ampup-mcp-plugin

# 3. Authenticate the AmpUp MCP connector (opens Auth0 in your browser)
/mcp
```

After `/mcp` completes the OAuth handshake, the AmpUp tools are live and the five
skills are available. Confirm with:

```bash
/plugin           # shows ampup-mcp-plugin with 5 skills
/mcp              # shows the ampup server as Connected
```

No token is written to any config file - the connector uses interactive OAuth,
and Claude Code manages the session.

---

## The bundled MCP connector

The plugin ships a single MCP server declaration in [`.mcp.json`](./.mcp.json):

```json
{
  "mcpServers": {
    "ampup": {
      "type": "http",
      "url": "https://app.ampup.ai/mcp"
    }
  }
}
```

It is a remote **streamable-HTTP** MCP server secured with **Auth0 OAuth**. On
first use Claude Code runs the browser sign-in; thereafter the tools connect
automatically. The connector exposes AmpUp's full tool surface (accounts, deals,
meetings, roleplays, courses, instructors, metrics, and more) - the skills use
the roleplay/course subset.

---

## MCP tool prefix

Claude Code namespaces a **plugin-bundled** MCP server's tools as:

```
mcp__plugin_<plugin-name>_<server-key>__<tool>
```

The plugin name keeps its hyphen. For this plugin (`ampup-mcp-plugin`, server key
`ampup`) that is:

```
mcp__plugin_ampup-mcp-plugin_ampup__<tool>
```

for example `mcp__plugin_ampup-mcp-plugin_ampup__create_course_from_plan`. This
was verified against the installed server, which registers as
`plugin:ampup-mcp-plugin:ampup`. Each skill states this prefix once at the top and
then refers to tools by their short names for readability.

---

## Skills

### `roleplay`

Create and edit AmpUp **practice scripts** - realistic roleplay scenarios for
sales, interviews, customer service, negotiation, or coaching. A script defines a
buyer/counterpart persona, the scenario, the opening line, voice/turn-taking
behavior, and the evaluation metrics used to score a rep's session.

**Key MCP tools:** `admin_create_practice_script` (persists a script),
`create_persona` / `list_personas` (reusable cast), `create_metric_group` +
`bulk_create_metrics` (evaluation rubric), `update_practice_script`,
`get_practice_script` / `list_practice_scripts`, `share_practice_script`.

**How it works:**
1. **Check the persona library first** (`list_personas`). If a saved persona fits
   the requested buyer, attach it via `persona_ids` and let its identity/voice/face
   inject at run time.
2. **Draft** the scenario, session script (the agent's system prompt), and - for an
   inline buyer - `agent_details` (name, role, company, `voice_id`, `first_message`,
   turn-taking).
3. **(Optional) metrics.** Create a metric group and its metrics, then reference the
   group in `analysis_options.metric_groups`.
4. **Persist** with `admin_create_practice_script`.

> **Persona note:** when you attach a persona via `persona_ids`, **omit
> `agent_details` entirely**. A partial `agent_details` (e.g. just
> `first_message`) fails, because `agent_details.name` is required whenever the
> object is present.

Example prompts: *"Create a cold-call roleplay against a skeptical VP of Sales."*
*"Make a mock backend-engineering interview with rubric metrics for communication,
problem solving, and system design."*

---

### `course-authoring`

Author a complete, narrated AmpUp course - outline, designed slides, spoken
talk-track, quizzes, and live roleplay checkpoints - and **create + publish** it
through MCP. Also turns an uploaded slide deck into a course.

**Key MCP tools:** `create_course_from_plan`, `set_course_plan`,
`set_course_styles`, `publish_course`, `create_course_from_deck`,
`list_talking_head_avatars`, `get_beat_clip_url`. Roleplay checkpoints reuse
`admin_create_practice_script` from the `roleplay` skill.

**The create -> persist -> publish sequence:**
1. **Pick a face/voice (required).** `create_course_from_plan` needs **either
   `talking_head_avatar_id` or `instructor_id`** - in *every* narration mode,
   including `audio_only`. Pass `voice_id` explicitly for narration.
2. **Create the draft:** `create_course_from_plan(name, course_plan, ...)`. `say`
   beats carry a `talking_head_clip_url` with a `__CID__` placeholder at this point.
3. **Swap `__CID__`:** replace the placeholder with the returned course id in every
   clip URL and call `set_course_plan(course_id, course_plan)`.
4. **(Optional) CSS:** `set_course_styles(course_id, css)`.
5. **Publish:** `publish_course(course_id)` (idempotent; `audio_only` publishes
   instantly).
6. **(Optional) warm audio:** `get_beat_clip_url(course_id, beat_id)` per `say` beat.

Slide design is delegated to the [`course-slides`](#course-slides-supporting)
skill and its `slide-designer` subagent; this skill owns the plan and persistence.

Example prompts: *"Build a 3-lesson onboarding course on handling security
objections, with a quiz and a live roleplay."* *"Turn this PPTX into an
audio-narrated course."*

---

### `course-editing`

Edit an already-created course's slides and talk-track, beat by beat. This is the
"Atlas" editor flow, MCP-only.

**Key MCP tools:** `get_course` (read the plan first), `update_slide_html`,
`update_beat_narration`, `update_quiz`, `update_roleplay`.

**How it works:** on the first turn, call `get_course(course_id)` to learn each
`slide_id`, `beat_id`, and which slides are editable (only agent-generated `html`
slides are - uploaded/rasterized deck pages are locked). Then make one edit per
tool call. The whole plan is re-validated after each edit; published/archived
courses reject edits with a 409 (edit the draft instead).

Example prompts: *"Make slide 2's narration a war story."* *"Shorten the
talk-track on the pricing slide."* *"Change the quiz answer options."*

---

### `instructor-brand`

Give a course instructor a brand: extract a design system (color, typography,
spacing, canvas tokens) from an uploaded template, settle the low-confidence
fields through a short interview, and persist it so every course that instructor
builds inherits the visual system.

**Key MCP tools:** `list_course_instructors` / `get_course_instructor` (resolve the
instructor), `extract_brand_tokens` (stateless token extraction with per-field
confidence), `update_course_instructor` (persist the settled `brand_template`).

**How it works:** resolve which existing instructor to brand, run
`extract_brand_tokens` against an uploaded template (pass the file's
`datasource_id` for a real deck; inline base64 only for a small styleguide),
inspect the confidence block, use `AskUserQuestion` on the low-confidence /
consequential fields only, then write the result with
`update_course_instructor(brand_template=...)`. Instructor creation (face/voice)
is owned by AmpUp's Identity Studio; this skill augments an existing instructor.

Example prompts: *"Brand this instructor from our company deck."* *"Use this
styleguide as the instructor's design system."*

---

### `course-slides` *(supporting)*

Authoring craft for high-design slide HTML that renders inside the AmpUp course
player. This is a **supporting** skill (`user-invocable: false`) that
`course-authoring` delegates to; it produces HTML strings that get embedded
directly into `course_plan.slides[].html`.

It ships:
- `frontend-design.md` - the design craft (typography, aesthetic direction, depth).
- `agents/slide-designer.md` - an Opus **slide-designer subagent** that does the
  per-slide design work.
- `splice_slides.py` - an optional local helper to preview a plan file.

It encodes the player's hard **render contract**: a fixed 1280x720 canvas,
shadow-isolated CSS, self-scaling to fit, one idea per slide, and no interaction
(the player screenshots and narrates each slide).

---

## Data models

### `course_plan` (schema_version `2.1`)

```jsonc
{
  "module_id": "short_slug",
  "title": "Course title",
  "narration_mode": "audio_only",         // "audio_only" | "talking_head" | "none"
  "schema_version": "2.1",
  "objectives": [ { "id": "obj_1", "label": "..." } ],
  "concepts":   [ { "id": "c_1", "label": "...", "objective_id": "obj_1",
                    "primary_slide_id": "s_intro" } ],
  "questions":  [ { "id": "q_1", "stem": "...?",
                    "options": [ {"id":"A","text":"...","correct":true},
                                 {"id":"B","text":"...","correct":false} ],
                    "rationale": "...", "multiSelect": false } ],
  "slides":     [ { "id": "s_intro", "kind": "html", "html": "<div ...>...</div>" } ],
  "lessons": [
    { "id": "l_1", "title": "...", "concept_ids": ["c_1"], "objective_ids": ["obj_1"],
      "beats": [
        { "id": "b_s_intro", "kind": "say", "slide_id": "s_intro", "say": "...",
          "talking_head_clip_url": "/sales-agents/api/v1/courses/__CID__/beat-audio/b_s_intro" },
        { "id": "bq1", "kind": "quiz", "question_ids": ["q_1"],
          "mandatory": false, "on_fail": "continue" },
        { "id": "brp1", "kind": "roleplay", "slide_id": "s_practice",
          "practice_script_id": "<id>", "scene": "...",
          "patient": { "name": "...", "tag": "...", "opener": "..." } }
      ] }
  ]
}
```

**Validation invariants** (the server rejects a plan that breaks any of these):

- `slides` and `lessons` are non-empty; every slide `id` is unique.
- Every `say` beat's `slide_id` resolves and its `say` is non-empty (except
  `narration_mode: "none"`).
- Every quiz `question_ids` entry exists in `questions[]`; `on_fail` is
  `"continue"` unless the beat also carries a `concept_id`.
- Every roleplay beat references a real `practice_script_id`, plus `slide_id`.
- Every `concept.primary_slide_id` and `concept.objective_id` resolve.
- **No orphan slides:** every slide is covered by at least one `say` or `roleplay`
  beat.
- After create, every `talking_head_clip_url` has `__CID__` swapped for the real
  course id before `set_course_plan`.

### Narration modes

| Mode | Presenter | Publish |
|---|---|---|
| `audio_only` | still avatar/instructor image + TTS voice | instant |
| `talking_head` | on-camera avatar reads the narration | renders video |
| `none` | silent, slides-only; learner advances manually | publishes with empty narration by design |

All modes require a `talking_head_avatar_id` or `instructor_id` at create time.

### Practice script (roleplay) fields

`admin_create_practice_script` takes `name`, `scenario`, `session_script`
(required) plus `agent_details` (persona identity + voice/turn-taking),
`analysis_options` (`metric_groups`, `auto_run_analysis`), `persona_ids`, `tags`,
`draft`, and `allow_hints`. Attach a saved persona via `persona_ids` **instead of**
`agent_details`.

---

## Design principles

- **MCP-only.** Every create, read, edit, and publish goes through an AmpUp MCP
  tool. No curl, no REST, no bundled API scripts, no keystore.
- **Standalone.** The skills are adapted from AmpUp's in-app authoring agents with
  all in-app runtime coupling removed - no web-app side panel, no server-side
  workspace, no "Save button" handoff. Persistence happens directly through the
  MCP tools, so the plugin works in any Claude Code session.
- **One prefix note per skill.** Each skill states the
  `mcp__plugin_ampup-mcp-plugin_ampup__` prefix once and uses short tool names
  throughout, so a fork/rename is a one-line change per skill.

---

## Verified end to end

The skills were flow-tested against a live AmpUp MCP connector, not just authored:

- **Roleplays:** created via `admin_create_practice_script` through three paths -
  reusing a saved persona, an inline persona, and a non-sales scenario with custom
  `create_metric_group` / `bulk_create_metrics` metrics wired into
  `analysis_options`.
- **Courses:** a full `create_course_from_plan` -> `set_course_plan` (`__CID__`
  swap) -> `publish_course` -> `get_beat_clip_url` sequence, including a course with
  a `say` beat, a quiz beat, and a roleplay beat referencing a created practice
  script. The course reached `status: published`.

Two API requirements surfaced during testing and are baked into the skills:

1. Attaching a persona to a practice script means **omitting `agent_details`
   entirely** (a partial object 422s on the required `name`).
2. `create_course_from_plan` **requires `talking_head_avatar_id` or `instructor_id`
   in every narration mode**, including `audio_only`.

---

## Pointing at another environment

The default connector targets production (`https://app.ampup.ai/mcp`). To use a
different environment, edit [`.mcp.json`](./.mcp.json) and change the `url`, for
example to `https://app.staging.a79dev.com/mcp`, then re-run `/mcp` to
authenticate against that environment.

---

## Using AmpUp on claude.ai or ChatGPT

- **claude.ai / Claude Desktop:** there is no single "plugin" artifact for the
  consumer apps. Add the AmpUp **MCP as a Connector** (same URL), and enable the
  skills separately as Agent Skills.
- **ChatGPT:** the bundled MCP can be added as an MCP connector (Apps SDK), but
  the skills do not port - ChatGPT has no skills concept, so their guidance would
  need to be folded into a custom GPT's instructions.

---

## Repository layout

```
ampup-mcp-plugin/
├── .claude-plugin/
│   ├── plugin.json          # plugin manifest (name, version, description)
│   └── marketplace.json     # single-plugin marketplace (source ".")
├── .mcp.json                # bundled AmpUp MCP server (streamable HTTP + OAuth)
├── skills/
│   ├── roleplay/SKILL.md
│   ├── course-authoring/SKILL.md
│   ├── course-editing/SKILL.md
│   ├── instructor-brand/SKILL.md
│   └── course-slides/
│       ├── SKILL.md
│       ├── frontend-design.md
│       ├── agents/slide-designer.md
│       └── splice_slides.py
├── README.md
└── LICENSE
```

---

## Development and maintenance

- **Validate** the plugin + marketplace manifests:
  ```bash
  claude plugin validate .
  ```
- **Test an install locally** from a path before pushing:
  ```bash
  claude plugin marketplace add /path/to/ampup-mcp-plugin
  claude plugin install ampup-mcp-plugin@ampup-mcp-plugin
  claude mcp list          # confirm plugin:ampup-mcp-plugin:ampup connects
  claude plugin uninstall ampup-mcp-plugin@ampup-mcp-plugin
  claude plugin marketplace remove ampup-mcp-plugin
  ```
- **Editing a skill:** skills are plain `SKILL.md` files with YAML frontmatter
  (`name`, `description`, `user-invocable`). Keep tool references on the
  `mcp__plugin_ampup-mcp-plugin_ampup__` prefix, and keep the "AmpUp MCP tools"
  note at the top of each skill in sync if the plugin or server name changes.
- **Cut a release tag:**
  ```bash
  claude plugin tag .      # creates ampup-mcp-plugin--v<version>, validating manifests
  ```
  Bump `version` in `.claude-plugin/plugin.json` first.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Tools show as `Needs authentication` in `/mcp` | Run `/mcp` and complete the browser OAuth flow. |
| `either instructor_id or talking_head_avatar_id is required` on course create | Pass a `talking_head_avatar_id` (from `list_talking_head_avatars`) or an `instructor_id`, in every narration mode. |
| `agent_details.name Field required` on roleplay create | You passed a partial `agent_details`. Either include `name`, or omit `agent_details` entirely when attaching a persona via `persona_ids`. |
| Course stuck / rejected on create | Re-check the [validation invariants](#course_plan-schema_version-21) - most often an orphan slide or an unresolved `slide_id`/`question_id`. |
| Narration never plays | Confirm every `say` beat's `talking_head_clip_url` had `__CID__` replaced with the real course id before `set_course_plan`. |
| Edit fails with 409 | The course is published/archived. Edits apply to drafts. |

---

## License

MIT - see [LICENSE](./LICENSE).
