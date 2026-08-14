"""
MotionX harness spike — the agent loop.

This is the whole thing. Read state, think, call a tool, repeat. No framework,
no graph, no orchestration. The ordering that used to live in the pipeline is
decided here, at runtime, by the model reading skill files.

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-...
    python agent.py "give me a shot list for scene 1"

Every run writes a full transcript to runs/. That transcript is the output of
the spike — more informative than the shot list itself.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic

from spike_tools import PROJECT_ID, PathError, execute, tool_schemas, _project_ref

MODEL = "claude-opus-5"  # swap to claude-sonnet-5 for cheaper iteration
MAX_TURNS = 40

client = Anthropic()

SYSTEM = """You are a filmmaking agent working inside a MotionX film project.

The project is a tree you navigate with `list` and `read`:

  /                       project: genre, style, aspect_ratio, moodboard_style
  /skills                 craft knowledge — read these, they are how you work
  /bible/characters       cast, each with visual_traits
  /bible/locations        locations, some with generated views
  /bible/props            props and products
  /{episode}/{scene}      scenes: scene_number, slugline, time, synopsis,
                          characters[], products[], dialogues[]
  /{episode}/{scene}/{shot}   shots, when a scene has been covered

Address scenes by number (`/Not Yet/sc1`) and shots 1-based (`/Not Yet/sc1/sh3`).
Sluglines repeat across a script, so they are not addresses.

HOW TO WORK

Start by listing `/skills` and reading whatever is relevant to the task. They
carry craft knowledge you are expected to apply, not background reading.

Never invent what you can read. If a scene names a character, read that
character. If you need the project's look, read the project node. Missing
information is a `read` away, and guessing at it is the main way this goes
wrong.

`list` gives summaries; `read` gives one node in full. Prefer listing first so
you know what exists before pulling detail. A project can hold dozens of scenes
and hundreds of nodes — read selectively.

When something doesn't resolve or contradicts itself, say so plainly rather than
working around it silently. Data problems are worth surfacing.

Ask before doing anything expensive or destructive. Generation costs money.

THIS SESSION

`write` and `generate_image` are in DRY RUN — they report what they would do and
change nothing. Proceed as though they are real; the printed patch is the
deliverable.
"""


def _print_tool_call(name: str, args: dict) -> None:
    if name in ("list", "read"):
        detail = args.get("path", "")
        if args.get("fields"):
            detail += f"  fields={args['fields']}"
    elif name == "write":
        detail = f"{args.get('path','')}  keys={list(args.get('patch', {}))}"
    else:
        detail = json.dumps(args)[:160]
    print(f"  → {name}({detail})")


def run(request: str) -> dict:
    messages = [{"role": "user", "content": request}]
    tools = tool_schemas()
    transcript = []
    total_in = total_out = 0
    started = time.time()

    print(f"\nproject {PROJECT_ID}")
    print(f"request: {request}\n" + "─" * 70)

    for turn in range(1, MAX_TURNS + 1):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            system=SYSTEM,
            tools=tools,
            messages=messages,
        )

        total_in += resp.usage.input_tokens
        total_out += resp.usage.output_tokens
        print(f"\n[turn {turn}]  in {resp.usage.input_tokens:,}  out {resp.usage.output_tokens:,}")

        for block in resp.content:
            if block.type == "text" and block.text.strip():
                print(f"\n{block.text}\n")

        messages.append({"role": "assistant", "content": resp.content})
        transcript.append({"turn": turn, "assistant": [b.model_dump() for b in resp.content]})

        calls = [b for b in resp.content if b.type == "tool_use"]
        if not calls:
            break

        results = []
        for call in calls:
            _print_tool_call(call.name, call.input)
            try:
                out = execute(call.name, call.input)
                results.append({"type": "tool_result", "tool_use_id": call.id,
                                "content": json.dumps(out, default=str)})
            except PathError as e:
                # Readable failure — the agent is expected to correct and retry.
                print(f"    ✗ {e}")
                results.append({"type": "tool_result", "tool_use_id": call.id,
                                "content": f"PathError: {e}", "is_error": True})
            except Exception as e:
                print(f"    ✗ {type(e).__name__}: {e}")
                results.append({"type": "tool_result", "tool_use_id": call.id,
                                "content": f"{type(e).__name__}: {e}", "is_error": True})

        messages.append({"role": "user", "content": results})
        transcript.append({"turn": turn, "tool_results": results})
    else:
        print(f"\n⚠ hit MAX_TURNS ({MAX_TURNS}) — agent did not finish")

    elapsed = time.time() - started
    print("\n" + "─" * 70)
    print(f"{turn} turns · {elapsed:.0f}s · in {total_in:,} · out {total_out:,}")

    Path("runs").mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = Path("runs") / f"{stamp}.json"
    out_path.write_text(json.dumps({
        "request": request,
        "model": MODEL,
        "project_id": PROJECT_ID,
        "turns": turn,
        "seconds": round(elapsed),
        "tokens": {"in": total_in, "out": total_out},
        "transcript": transcript,
    }, indent=2, default=str))
    print(f"transcript → {out_path}")

    return {"turns": turn, "tokens_in": total_in, "tokens_out": total_out}


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("set ANTHROPIC_API_KEY")
    prompt = " ".join(sys.argv[1:]) or "List the scenes in this project."
    run(prompt)