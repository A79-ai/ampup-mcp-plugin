#!/usr/bin/env python3
"""Splice designed slide HTML from sidecar files into a course plan JSON.

The ``slide-designer`` subagent writes each slide's raw HTML to a sidecar file
(``<plan_dir>/slides/<slide_id>.html``) rather than editing the plan JSON
directly: injecting raw HTML (real newlines and quotes) into a JSON string
field corrupts the file, and the agent-side Edit/escape hook only escapes when
the edit already straddles escaped bytes. This script reads each sidecar and
assigns it to the matching ``slides[].html`` via ``json.dump``, which escapes
the string correctly every time.

stdlib-only on purpose: it runs inside the Daytona sandbox, where common_py and
third-party packages are not installed.

Usage::

    splice_slides.py <plan.course.json> [slide_id ...]

With no slide_id, every slide that has a sidecar is spliced. With one or more
slide_ids, only those are spliced (used per-slide for progressive rendering).
Exit code 0 = all requested slides spliced; 1 = at least one slide_id had no
sidecar or no matching slide entry; 2 = bad invocation.
"""

import json
import os
import sys
import tempfile
from dataclasses import dataclass, field


@dataclass
class SpliceResult:
    """Outcome of a splice run.

    ``spliced`` = slide ids whose sidecar HTML was written into the plan;
    ``missing`` = requested ids with no sidecar file or no matching slide entry.
    """

    spliced: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def splice(plan_path: str, slide_ids: list[str] | None = None) -> SpliceResult:
    """Fill ``slides[].html`` from sidecar files."""
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)

    slides_dir = os.path.join(os.path.dirname(os.path.abspath(plan_path)), "slides")
    by_id = {
        s["id"]: s for s in plan.get("slides", []) if isinstance(s, dict) and "id" in s
    }
    targets = slide_ids if slide_ids else list(by_id)

    result = SpliceResult()
    for sid in targets:
        slide = by_id.get(sid)
        sidecar = os.path.join(slides_dir, f"{sid}.html")
        if slide is None or not os.path.exists(sidecar):
            result.missing.append(sid)
            continue
        with open(sidecar, encoding="utf-8") as f:
            # Postgres rejects NUL bytes in text/jsonb; strip them at the
            # sandbox boundary so the plan stays persistable on Save.
            slide["html"] = f.read().replace("\x00", "")
        result.spliced.append(sid)

    # Write atomically: the panel polls this file on a short interval while the
    # build streams, so a truncate-in-place (``open(path, "w")``) lets a reader
    # catch a half-written file and flash a parse / load error. Write a sibling
    # temp file and ``os.replace`` it in — readers only ever see the old or the
    # new complete file, never a partial one.
    plan_dir = os.path.dirname(os.path.abspath(plan_path))
    fd, tmp_path = tempfile.mkstemp(dir=plan_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, plan_path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return result


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: splice_slides.py <plan.course.json> [slide_id ...]", file=sys.stderr
        )
        return 2
    result = splice(argv[1], argv[2:] or None)
    print(f"spliced: {','.join(result.spliced) if result.spliced else '(none)'}")
    if result.missing:
        print(f"no sidecar/slide for: {','.join(result.missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
