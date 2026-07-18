# AmpUp MCP Plugin

A Claude Code plugin that bundles the **AmpUp MCP connector** with skills for
authoring AmpUp **roleplays** and **courses**. Every skill persists through MCP
tools — there is no direct API access, no scripts, and no keystore.

## Skills

| Skill | Creates / edits | Key MCP tools |
|---|---|---|
| `roleplay` | Practice-script roleplay scenarios (buyer persona, scenario, opener, evaluation metrics) | `admin_create_practice_script`, `create_persona`, `create_metric_group`, `update_practice_script` |
| `course-authoring` | A complete narrated course (outline → slides → talk-track → quizzes/roleplays), created and published | `create_course_from_plan`, `set_course_plan`, `set_course_styles`, `publish_course`, `create_course_from_deck` |
| `course-editing` | Edits to a drafted course's slides & talk-track, slide by slide | `get_course`, `update_slide_html`, `update_beat_narration`, `update_quiz`, `update_roleplay` |
| `instructor-brand` | A brand/design-system for a course instructor, from an uploaded template | `extract_brand_tokens`, `update_course_instructor`, `list_course_instructors` |
| `course-slides` | *(supporting)* High-design slide HTML for the course player; ships a `slide-designer` subagent | *(produces HTML for `course-authoring`)* |

Plus the bundled **`ampup` MCP server** (`.mcp.json`) — the AmpUp connector at
`https://app.ampup.ai/mcp`.

## Install

```bash
/plugin marketplace add A79-ai/ampup-mcp-plugin
/plugin install ampup-mcp-plugin@ampup-mcp-plugin
/mcp        # authenticate the AmpUp connector (Auth0 OAuth, opens in browser)
```

The MCP uses interactive OAuth on first use — no token is stored in the config.

### Pointing at staging

Edit `.mcp.json` and change the URL to `https://app.staging.a79dev.com/mcp`.

## MCP tool prefix

Claude Code namespaces a plugin-bundled MCP server's tools as
`mcp__plugin_<plugin>_<server>__<tool>` (the plugin name keeps its hyphen). For
this plugin that is **`mcp__plugin_ampup-mcp-plugin_ampup__*`** — verified against
the installed server, which registers as `plugin:ampup-mcp-plugin:ampup`. Each
skill states this prefix once and then refers to tools by their short names.

## Design principle: MCP-only

These skills are adapted from AmpUp's in-app authoring agents, with all
in-app runtime coupling removed (no web-app panel, no server-side workspace).
Everything a skill does — create, edit, publish — goes through an AmpUp MCP tool,
so the plugin works in any standalone Claude Code session once the connector is
authenticated.

## ChatGPT

The bundled MCP can be added to ChatGPT as an MCP connector (Apps SDK), but the
skills do not port — ChatGPT has no skills concept, so their guidance would need
to be folded into a custom GPT's instructions.

## License

MIT — see [LICENSE](./LICENSE).
