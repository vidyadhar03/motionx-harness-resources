"""
MotionX harness spike — the agent loop (Gemini).

This is the whole thing. Read state, think, call a tool, repeat. No framework,
no graph, no orchestration. The ordering that used to live in the pipeline is
decided here, at runtime, by the model reading skill files.

Deliberately the same model family the legacy pipeline used, so the diff
isolates architecture rather than model quality.

Usage:
    pip install google-genai
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccountKey.json
    export GOOGLE_CLOUD_PROJECT=motionx-studio          # Vertex path
    # ...or, for the simpler AI Studio path:
    export GEMINI_API_KEY=...

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

from google import genai
from google.genai import types

from spike_tools import PROJECT_ID, PathError, execute, tool_schemas

MODEL = "gemini-3.1-pro-preview"
MAX_TURNS = 40

# Vertex when a GCP project is set (reuses the Firestore service account),
# otherwise AI Studio with an API key.
if os.environ.get("GOOGLE_CLOUD_PROJECT"):
    client = genai.Client(
        vertexai=True,
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
else:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


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


# ─────────────────────────────────────────────────────────────────────────────
# Schema translation — Anthropic-style JSON Schema → Gemini FunctionDeclaration
# ─────────────────────────────────────────────────────────────────────────────

def _clean_schema(node: dict, defs: dict) -> dict:
    """
    Gemini's schema dialect is narrower than Pydantic's output: no $ref, no
    $defs, no anyOf/const, no format hints. Inline and strip.
    """
    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        key = node["$ref"].split("/")[-1]
        return _clean_schema(defs.get(key, {}), defs)

    # Optional[X] arrives as anyOf[X, null]; take the non-null branch.
    if "anyOf" in node:
        for option in node["anyOf"]:
            if option.get("type") != "null":
                return _clean_schema(option, defs)
        return {"type": "string"}

    out: dict = {}
    for k, v in node.items():
        if k in ("$defs", "title", "default", "additionalProperties",
                 "format", "const", "minLength", "maxLength",
                 "minItems", "maxItems", "exclusiveMinimum", "exclusiveMaximum"):
            continue
        if k == "properties":
            out["properties"] = {pk: _clean_schema(pv, defs) for pk, pv in v.items()}
        elif k == "items":
            out["items"] = _clean_schema(v, defs)
        elif k == "enum":
            out["enum"] = [str(e) for e in v]
        else:
            out[k] = v

    # Gemini requires object types to declare properties.
    if out.get("type") == "object" and "properties" not in out:
        out["properties"] = {}
    return out


def gemini_tools() -> types.Tool:
    declarations = []
    for spec in tool_schemas():
        schema = spec["input_schema"]
        cleaned = _clean_schema(schema, schema.get("$defs", {}))
        declarations.append(
            types.FunctionDeclaration(
                name=spec["name"],
                description=spec["description"],
                parameters=cleaned,
            )
        )
    return types.Tool(function_declarations=declarations)


# ─────────────────────────────────────────────────────────────────────────────
# Loop
# ─────────────────────────────────────────────────────────────────────────────

def _print_tool_call(name: str, args: dict) -> None:
    if name in ("list", "read"):
        detail = args.get("path", "")
        if args.get("fields"):
            detail += f"  fields={args['fields']}"
    elif name == "write":
        detail = f"{args.get('path','')}  keys={list(args.get('patch', {}))}"
    else:
        detail = json.dumps(args, default=str)[:160]
    print(f"  → {name}({detail})")


def run(request: str) -> dict:
    tools = gemini_tools()
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM,
        tools=[tools],
        temperature=1.0,
        max_output_tokens=8000,
        # The model decides when to stop calling tools, not us.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    contents = [types.Content(role="user", parts=[types.Part(text=request)])]
    transcript = []
    total_in = total_out = 0
    started = time.time()
    turn = 0

    print(f"\nmodel {MODEL}")
    print(f"project {PROJECT_ID}")
    print(f"request: {request}\n" + "─" * 70)

    while turn < MAX_TURNS:
        turn += 1
        resp = client.models.generate_content(
            model=MODEL, contents=contents, config=config
        )

        usage = resp.usage_metadata
        if usage:
            total_in += usage.prompt_token_count or 0
            total_out += usage.candidates_token_count or 0
            print(f"\n[turn {turn}]  in {usage.prompt_token_count:,}  "
                  f"out {usage.candidates_token_count:,}")

        candidate = resp.candidates[0]
        parts = candidate.content.parts or []

        for part in parts:
            if getattr(part, "text", None) and part.text.strip():
                print(f"\n{part.text}\n")

        contents.append(candidate.content)
        transcript.append({
            "turn": turn,
            "model": [
                {"text": p.text} if getattr(p, "text", None)
                else {"call": p.function_call.name, "args": dict(p.function_call.args or {})}
                for p in parts
            ],
        })

        calls = [p.function_call for p in parts if getattr(p, "function_call", None)]
        if not calls:
            break

        response_parts = []
        results_log = []
        for call in calls:
            args = dict(call.args or {})
            _print_tool_call(call.name, args)
            try:
                out = execute(call.name, args)
                payload = {"result": json.loads(json.dumps(out, default=str))}
            except PathError as e:
                # Readable failure — the agent is expected to correct and retry.
                print(f"    ✗ {e}")
                payload = {"error": f"PathError: {e}"}
            except Exception as e:
                print(f"    ✗ {type(e).__name__}: {e}")
                payload = {"error": f"{type(e).__name__}: {e}"}

            results_log.append({"call": call.name, "args": args, "payload": payload})
            response_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=call.name, response=payload
                    )
                )
            )

        contents.append(types.Content(role="user", parts=response_parts))
        transcript.append({"turn": turn, "tool_results": results_log})
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
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_CLOUD_PROJECT")):
        sys.exit("set GEMINI_API_KEY, or GOOGLE_CLOUD_PROJECT to use Vertex")
    prompt = " ".join(sys.argv[1:]) or "List the scenes in this project."
    run(prompt)