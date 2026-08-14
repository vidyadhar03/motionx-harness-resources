"""
MotionX harness spike — four tools over the existing Firestore project tree.

Throwaway. No API, no auth, no deploy. Run from a terminal, point at one project,
watch what the agent does.

Safety posture for the spike:
  - write()          is DRY RUN by default (prints the patch, touches nothing)
  - generate_image() is DRY RUN by default (returns the assembled prompt, spends nothing)

Verified structure:
  projects/{pid}
    characters/{NAME}       visual_traits{age,ethnicity,hair,clothing,vibe}, prompt, image_url
    locations/{ID}
    products/{ID}
    moodboard_options/{id}
    scripts/{id}
    drafts/{id}
    episodes/{eid}
      scenes/{scene_N_hash}   scene_number, slugline, location, location_id, time,
                              synopsis, characters[], products[], dialogues[], status
        shots/{shot_NN}       order, shot_type, prompt, visual_action, video_prompt,
                              characters[], products[], image_url, video_url, status

Two gotchas this file handles:
  - The bible stores display names ("BLACK PANTHER"); scenes reference IDs
    ("BLACK_PANTHER"). Both sides are normalized before matching.
  - Sluglines repeat across scenes. Scenes address by number only.
"""

from __future__ import annotations

import json
import warnings
from typing import Any, Dict, List, Literal, Optional, Tuple

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from pydantic import BaseModel, Field

from pathlib import Path
 
SKILLS_DIR = Path(__file__).parent / "skills"
 
 
def _skills_parts(path: str):
    """Return path parts if this is a /skills path, else None."""
    parts = [p for p in path.strip("/").split("/") if p]
    return parts if parts and parts[0] == "skills" else None
 

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ID = "6372a137-59e8-4abf-aff8-6e804a943f01"

# Logical tree path → Firestore subcollection under projects/{id}/
COLLECTIONS = {
    "script": "scripts",
    "moodboard": "moodboard_options",
    "bible/characters": "characters",
    "bible/locations": "locations",
    "bible/props": "products",
    "episodes": "episodes",
}

SCENES_SUBCOLLECTION = "scenes"
SHOTS_SUBCOLLECTION = "shots"

# Never returned to the agent: stale counters, generation logs, frozen duplicates.
NOISE_FIELDS = (
    "metrics",              # stale counters
    "ai_logs",              # generation logs
    "last_generated_prompt",  # byte-identical duplicate of `prompt`
    "video_history",        # hundreds of tokens of near-duplicate prompts
    "video_settings",       # provider plumbing
    "seedance_task_id",
    "model_used",
    "error_code",
    "error_message",
)

DRY_RUN_WRITES = True
DRY_RUN_GENERATION = True

db = firestore.Client()
_project_ref = db.collection("projects").document(PROJECT_ID)


# ─────────────────────────────────────────────────────────────────────────────
# Path resolution — logical tree → Firestore ref
#
#   /                        project doc
#   /bible/characters        collection
#   /bible/characters/ANNA   doc (case- and separator-insensitive)
#   /ep1                     episode (by title or episode_number)
#   /ep1/sc3                 scene (by scene_number)
#   /ep1/sc3/sh1             shot (1-based in paths; maps to order 0)
# ─────────────────────────────────────────────────────────────────────────────


class PathError(Exception):
    """Raised with a message the agent is expected to read and correct."""


def _norm(value: Any) -> str:
    """
    Canonical key. Collapses the two ID conventions in the DB:
      'Black Panther' / 'BLACK PANTHER' / 'BLACK_PANTHER' → 'BLACK_PANTHER'
    """
    return str(value).strip().upper().replace("-", "_").replace(" ", "_")


def _find_by_field(coll_ref, candidates: List[str], value: str):
    """Resolve a human key to a doc: indexed lookup, then normalized scan, then doc ID."""
    probes: List[Any] = [value]
    if str(value).lstrip("-").isdigit():
        probes.append(int(value))
    for field in candidates:
        for probe in probes:
            hits = list(coll_ref.where(filter=FieldFilter(field, "==", probe)).limit(1).stream())
            if hits:
                return hits[0]

    # Normalized scan — handles display-name vs ID drift.
    needle = _norm(value)
    for doc in coll_ref.limit(300).stream():
        data = doc.to_dict() or {}
        if _norm(doc.id) == needle:
            return doc
        for field in candidates:
            if field in data and _norm(data[field]) == needle:
                return doc

    snap = coll_ref.document(value).get()
    return snap if snap.exists else None


def _find_scene(scenes_ref, key: str):
    """Scenes address by number only — sluglines repeat across a script."""
    cleaned = key.lower()
    if cleaned.startswith("sc"):
        cleaned = cleaned[2:]
    return _find_by_field(scenes_ref, ["scene_number"], cleaned or key)


def _find_shot(shots_ref, key: str):
    """Shots are 1-based in paths, 0-based in `order`, and 'shot_01' as doc ID."""
    cleaned = key.lower()
    if cleaned.startswith("sh"):
        cleaned = cleaned[2:]
    if cleaned.isdigit():
        n = int(cleaned)
        hits = list(shots_ref.where(filter=FieldFilter("order", "==", n - 1)).limit(1).stream())
        if hits:
            return hits[0]
        snap = shots_ref.document(f"shot_{n:02d}").get()
        if snap.exists:
            return snap
    return _find_by_field(shots_ref, ["order", "id"], cleaned or key)


def resolve(path: str) -> Tuple[str, Any]:
    """Return (kind, ref) where kind is 'doc' or 'collection'."""
    parts = [p for p in path.strip("/").split("/") if p]

    if not parts:
        return "doc", _project_ref

    for prefix, coll in COLLECTIONS.items():
        pre_parts = prefix.split("/")
        if parts[: len(pre_parts)] == pre_parts:
            rest = parts[len(pre_parts) :]
            coll_ref = _project_ref.collection(coll)
            if not rest:
                return "collection", coll_ref
            doc = _find_by_field(coll_ref, ["name", "title", "id", "slug"], rest[0])
            if doc is None:
                raise PathError(f"No document named '{rest[0]}' under /{prefix}")
            return "doc", doc.reference

    if parts[0] == "bible":
        raise PathError("Use /bible/characters, /bible/locations, or /bible/props")

    ep_doc = _find_by_field(
        _project_ref.collection(COLLECTIONS["episodes"]),
        ["title", "episode_number", "slug"],
        parts[0],
    )
    if ep_doc is None:
        raise PathError(f"No episode '{parts[0]}'. Call list('/') to see what exists.")
    if len(parts) == 1:
        return "doc", ep_doc.reference

    scenes = ep_doc.reference.collection(SCENES_SUBCOLLECTION)
    sc = _find_scene(scenes, parts[1])
    if sc is None:
        raise PathError(f"No scene '{parts[1]}' in {parts[0]}. Address scenes by number, e.g. sc3.")
    if len(parts) == 2:
        return "doc", sc.reference

    shots = sc.reference.collection(SHOTS_SUBCOLLECTION)
    if len(parts) == 3:
        sh = _find_shot(shots, parts[2])
        if sh is None:
            raise PathError(f"No shot '{parts[2]}' in {parts[1]}")
        return "doc", sh.reference

    raise PathError(f"Path too deep: {path}")


from uuid import uuid4
 
# Fields the tools set themselves. A node holding only these is a placeholder,
# not real work, so overwriting it is safe.
_DERIVED = {
    "id", "created_at", "updated_at", "order", "scene_number",
    "status", "location", "location_id",
}
 
 
def _has_content(data: dict) -> bool:
    return any(k not in _DERIVED for k in data)
 
 
def _allocate(path: str):
    """
    Return a ref for a node that doesn't exist yet, following the DB's own
    naming conventions so created nodes are indistinguishable from pipeline ones.
    """
    parts = [p for p in path.strip("/").split("/") if p]
 
    # /bible/characters/RAVI, /bible/props/KNIFE, ...
    for prefix, coll in COLLECTIONS.items():
        pre = prefix.split("/")
        if parts[: len(pre)] == pre and len(parts) == len(pre) + 1:
            return _project_ref.collection(coll).document(_norm(parts[-1]))
 
    def _index(token: str, strip: str) -> int:
        cleaned = token.lower()
        if cleaned.startswith(strip):
            cleaned = cleaned[len(strip):]
        if not cleaned.isdigit():
            raise PathError(f"'{token}' is not a number — use {strip}3, {strip}11, etc.")
        return int(cleaned)
 
    # /{episode}/{scene}/{shot} — parent scene must already exist
    if len(parts) == 3:
        _, scene_ref = resolve("/".join(parts[:2]))
        n = _index(parts[2], "sh")
        return scene_ref.collection(SHOTS_SUBCOLLECTION).document(f"shot_{n:02d}")
 
    # /{episode}/{scene} — parent episode must already exist
    if len(parts) == 2:
        _, ep_ref = resolve(parts[0])
        n = _index(parts[1], "sc")
        return ep_ref.collection(SCENES_SUBCOLLECTION).document(f"scene_{n}_{uuid4().hex[:4]}")
 
    raise PathError(f"Cannot create a node at {path}")
 
 
def _derive_on_create(path: str, ref) -> dict:
    """
    Fields a new node needs to sit correctly alongside existing ones. The agent
    shouldn't have to know that `order` is 0-based or that shots inherit their
    scene's location.
    """
    parts = [p for p in path.strip("/").split("/") if p]
    base = {"id": ref.id, "created_at": firestore.SERVER_TIMESTAMP}
 
    if len(parts) == 3:  # shot
        n = int(ref.id.split("_")[-1])
        _, scene_ref = resolve("/".join(parts[:2]))
        scene = scene_ref.get().to_dict() or {}
        base.update({
            "order": n - 1,  # paths are 1-based, `order` is 0-based
            "status": "draft",
            "location": scene.get("location", ""),
            "location_id": scene.get("location_id", ""),
        })
    elif len(parts) == 2:  # scene
        base.update({"scene_number": int(ref.id.split("_")[1]), "status": "draft"})
 
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Summaries — list() must never return full documents or context dies.
# ─────────────────────────────────────────────────────────────────────────────

TITLE_FIELDS = ["title", "name", "slugline", "location"]
STATUS_FIELDS = ["status", "generation_status", "script_status"]
SUMMARY_FIELDS = (
    "scene_number",
    "order",
    "shot_type",
    "time",
    "estimated_duration_seconds",
    "estimated_duration",
    "character_role",
    "category",
    "type",
)


def _first(data: dict, fields: List[str]) -> Optional[str]:
    for f in fields:
        if data.get(f):
            return str(data[f])
    return None


def _summarize(doc) -> dict:
    data = doc.to_dict() or {}
    out: Dict[str, Any] = {"key": doc.id}
    title = _first(data, TITLE_FIELDS)
    if title:
        out["title"] = title[:90]
    status = _first(data, STATUS_FIELDS)
    if status:
        out["status"] = status
    for f in SUMMARY_FIELDS:
        if data.get(f) is not None:
            out[f] = data[f]
    for f in ("characters", "products"):
        if isinstance(data.get(f), list) and data[f]:
            out[f] = data[f][:8]
    out["has_image"] = bool(data.get("image_url") or data.get("moodboard_image_url"))
    if data.get("video_url"):
        out["has_video"] = True
    return out


# ─────────────────────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────────────────────


class ListArgs(BaseModel):
    path: str = Field(description="Tree path, e.g. '/', '/bible/characters', '/ep1/sc3'")


def tool_list(path: str) -> dict:
    """Children of a path. Summaries only — never full documents."""
    
    parts = _skills_parts(path)
    if parts is not None:
        if len(parts) > 1:
            raise PathError("/skills is flat — use read() on a specific file")
        files = sorted(SKILLS_DIR.glob("*.md")) if SKILLS_DIR.exists() else []
        return {
            "path": "/skills",
            "count": len(files),
            "children": [
                {
                    "key": f.name,
                    # First heading doubles as the description.
                    "title": next(
                        (
                            ln.lstrip("# ").strip()
                            for ln in f.read_text().splitlines()
                            if ln.startswith("#")
                        ),
                        f.stem,
                    ),
                }
                for f in files
            ],
        }

    kind, ref = resolve(path)

    if kind == "collection":
        items = [_summarize(d) for d in ref.limit(300).stream()]
        items.sort(key=lambda c: str(c.get("key")))
        return {"path": path, "count": len(items), "children": items}

    subs = [c.id for c in ref.collections()]
    result: Dict[str, Any] = {"path": path, "subcollections": subs}

    depth = len([p for p in path.strip("/").split("/") if p])
    expand = {
        0: COLLECTIONS["episodes"],
        1: SCENES_SUBCOLLECTION,
        2: SHOTS_SUBCOLLECTION,
    }.get(depth)

    if expand and expand in subs:
        children = [_summarize(d) for d in ref.collection(expand).limit(300).stream()]
        children.sort(key=lambda c: (c.get("scene_number") or c.get("order") or 0))
        result["children"] = children
        result["count"] = len(children)  # computed; `metrics` is never trusted
    return result


class ReadArgs(BaseModel):
    path: str
    fields: Optional[List[str]] = Field(
        default=None, description="Optional subset of fields. Omit for the whole node."
    )


def tool_read(path: str, fields: Optional[List[str]] = None) -> dict:
    """A node's contents plus its observed shape, so the agent learns the schema."""

    parts = _skills_parts(path)
    if parts is not None:
        if len(parts) != 2:
            raise PathError("Read a specific skill, e.g. /skills/shot-listing.md")
        f = SKILLS_DIR / parts[1]
        if not f.exists():
            raise PathError(f"No skill '{parts[1]}'. Call list('/skills').")
        return {"path": path, "content": f.read_text()}

    kind, ref = resolve(path)
    if kind == "collection":
        raise PathError(f"{path} is a collection — use list()")

    data = ref.get().to_dict() or {}
    for f in NOISE_FIELDS:
        data.pop(f, None)

    if fields:
        data = {k: v for k, v in data.items() if k in fields}

    schema = {k: type(v).__name__ for k, v in sorted(data.items())}
    return {"path": path, "schema": schema, "node": data}


class WriteArgs(BaseModel):
    path: str = Field(
        description=(
            "Node to write. Creates it if it doesn't exist — write to /ep/sc1/sh11 "
            "to add an eleventh shot."
        )
    )
    patch: Dict[str, Any] = Field(description="Fields to merge into the node")
    overwrite: bool = Field(
        default=False,
        description=(
            "Required to replace a node that already holds work. Existing shots are "
            "someone's output — prefer a new path unless replacement is the intent."
        ),
    )


def tool_write(path: str, patch: Dict[str, Any], overwrite: bool = False) -> dict:
    """Create or update a node. DRY RUN by default."""
    try:
        kind, ref = resolve(path)
        if kind == "collection":
            raise PathError(f"{path} is a collection — write to a specific node")
        existing = ref.get().to_dict() or {}
        creating = False
    except PathError as e:
        # Only allocate when the leaf is missing. A bad episode or scene in the
        # path is a real error and should surface as one.
        if "No shot" not in str(e) and "No scene" not in str(e) and "No document named" not in str(e):
            raise
        ref = _allocate(path)
        existing = {}
        creating = True
 
    if not creating and _has_content(existing) and not overwrite:
        held = ", ".join(k for k in sorted(existing) if k not in _DERIVED)[:120]
        raise PathError(
            f"{path} already holds work ({held}). "
            f"Write to a new path to add a node, or pass overwrite=true to replace this one."
        )
 
    if creating:
        patch = {**_derive_on_create(path, ref), **patch}
 
    action = "create" if creating else ("overwrite" if _has_content(existing) else "update")
 
    if DRY_RUN_WRITES:
        print(f"\n  [DRY RUN {action}] {path}  →  {ref.id}")
        print("  " + json.dumps(patch, indent=2, default=str).replace("\n", "\n  ") + "\n")
        return {"path": path, "node_id": ref.id, "action": action,
                "written": False, "dry_run": True}
 
    ref.set(patch, merge=not overwrite)
    return {"path": path, "node_id": ref.id, "action": action,
            "written": True, "fields": sorted(patch)}


RefRole = Literal["identity", "style", "continuity", "location", "product", "wardrobe"]


class Ref(BaseModel):
    path: str = Field(description="Tree path to the node holding the reference image")
    role: RefRole = Field(
        description=(
            "identity: match face/hair/skin/build, ignore clothing. "
            "style: match grade and lighting, ignore subject. "
            "continuity: match background only, ignore character placement. "
            "location: pixel-lock the set. "
            "product: match the object exactly. "
            "wardrobe: match the outfit."
        )
    )


class GenerateImageArgs(BaseModel):
    prompt: str = Field(min_length=10, description="What is in frame. Intent, not provider syntax.")
    refs: List[Ref] = Field(default_factory=list, max_length=8)
    write_to: str = Field(description="Tree path where the resulting image is recorded")


def tool_generate_image(prompt: str, refs: List[dict], write_to: str) -> dict:
    """
    Generation primitive. The agent writes intent; the tool speaks the provider dialect.

    Consistency context (moodboard + genre) is assembled here at call time, not baked
    into a stored string — so a moodboard change propagates instead of going stale.
    """
    project = _project_ref.get().to_dict() or {}
    style = project.get("moodboard_style") or {}

    consistency = ". ".join(
        p
        for p in [
            "GENRE: {}".format(project.get("genre")) if project.get("genre") else None,
            "COLOR: {}".format(style.get("color_palette")) if style.get("color_palette") else None,
            "LIGHTING: {}".format(style.get("lighting")) if style.get("lighting") else None,
            "TEXTURE: {}".format(style.get("texture")) if style.get("texture") else None,
            "ATMOSPHERE: {}".format(style.get("atmosphere")) if style.get("atmosphere") else None,
        ]
        if p
    )

    resolved_refs = []
    for r in refs:
        _, ref_doc = resolve(r["path"])
        data = ref_doc.get().to_dict() or {}
        url = data.get("image_url") or data.get("moodboard_image_url")
        if not url:
            raise PathError(f"{r['path']} has no image to reference")
        resolved_refs.append({"role": r["role"], "url": url, "from": r["path"]})

    assembled = f"{prompt}. {consistency}. --ar {project.get('aspect_ratio', '16:9')}"

    if DRY_RUN_GENERATION:
        print(f"\n  [DRY RUN generate_image] → {write_to}")
        print(f"  prompt: {assembled}")
        for r in resolved_refs:
            print(f"  ref[{r['role']}]: {r['from']}")
        print()
        return {
            "dry_run": True,
            "assembled_prompt": assembled,
            "refs": resolved_refs,
            "write_to": write_to,
        }

    raise NotImplementedError("Wire the provider adapter from workers/image/main.py here")


# ─────────────────────────────────────────────────────────────────────────────
# Registry — one definition feeds both the executor and the API tool schemas.
# ─────────────────────────────────────────────────────────────────────────────

TOOLS = {
    "list": (tool_list, ListArgs, "List children of a path. Returns summaries, not full nodes."),
    "read": (tool_read, ReadArgs, "Read a node's contents and schema."),
    "write": (tool_write, WriteArgs, "Create or update a node by merging a patch."),
    "generate_image": (
        tool_generate_image,
        GenerateImageArgs,
        "Generate a still. Describe intent; references carry role-scoped authority.",
    ),
}


def tool_schemas() -> List[dict]:
    return [
        {"name": name, "description": desc, "input_schema": model.model_json_schema()}
        for name, (_, model, desc) in TOOLS.items()
    ]


def execute(name: str, args: dict) -> dict:
    fn, model, _ = TOOLS[name]
    return fn(**model(**args).model_dump())


# ─────────────────────────────────────────────────────────────────────────────
# Survey — run this file directly to see what the project actually contains.
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    project = _project_ref.get().to_dict() or {}
    print("PROJECT")
    for k in ("title", "genre", "type", "style", "engine_style", "status", "aspect_ratio"):
        if project.get(k):
            print(f"  {k}: {project[k]}")
    print("  moodboard_style: " + json.dumps(project.get("moodboard_style") or {}, indent=4))

    print("\nROOT")
    print(json.dumps(tool_list("/"), indent=2, default=str)[:1500])

    print("\nSCENES WITH SHOTS")
    for ep in _project_ref.collection(COLLECTIONS["episodes"]).stream():
        found = 0
        for sc in ep.reference.collection(SCENES_SUBCOLLECTION).stream():
            n = len(list(sc.reference.collection(SHOTS_SUBCOLLECTION).limit(50).stream()))
            if n:
                found += 1
                d = sc.to_dict() or {}
                print(
                    f"  {sc.id:24} shots={n:<3} time={str(d.get('time')):<10} "
                    f"scene={d.get('scene_number')} {d.get('slugline')}"
                )
        print(f"  → {found} scene(s) with shots in episode {ep.id}")