"""
MotionX harness — schema v1.1 (locked).

Principle: reads tolerate the old shape, writes enforce this one. Nothing is
migrated. The tool layer normalises legacy documents into these models via
`from_legacy()`; `write` validates against them and refuses anything else.

The shot god object (~45 fields) is split along the four concerns it mixed:

    intent            → Shot          (what the director wants)
    generation inputs → assembled by the tool at call time, never stored
    outputs           → Track / Take  (media, with provenance)
    execution state   → Run           (async jobs, provider receipts, cost)

Field counts vs today: shot 45 → 12, scene 13 → 10, character 15 → 8.

v1.1 — HYBRID SHOOT SUPPORT
The Dehleez series shoots practical and generated coverage against the same
project tree. The additions below are what that requires, and no more. There is
no hybrid mode, no parallel model, no branch in the tool layer:

  + Shot.source          REQUIRED, no default on read. Whether this shot is
                         generated or shot on camera. The one field that must
                         never be inferred — a shot misread as generated is the
                         spike's invisible ceiling with a crew standing around.
  ~ Take.media_url       now Optional. Footage exists on a card for hours before
                         ingest, and the moment of capture is the moment the
                         metadata is accurate. Requiring a URL to write a take
                         pushes on-set logging into a spreadsheet.
  ~ Take.source          "practical" split out from "uploaded". A camera
                         negative and a director's uploaded fix are different
                         populations for eval and cannot be separated later.
  + Take identity        camera_roll / slate / timecode_start — the minimum
                         needed to match a Take document to a file on a card.
  + RejectionReason      practical-only block. Without it every DoP reject
                         collapses to `other`, which is the exact failure the
                         enum exists to prevent.
  ~ Scene.status         "covered" → "shot_listed". To a crew, covered means the
                         footage exists; here it meant shots are planned.

DELIBERATELY ABSENT: `project.mode`. A project-level hybrid flag cannot answer
the only question asked at tool time — can the agent generate THIS shot — so it
is not a control. If the UI wants a label it derives one from the shots'
sources. A stored flag would be a second source of truth for a fact Shot.source
already owns, and would drift the first time a pure-AI project gains one
practical shot.

v1.0 CHANGES — from the provider parameter audit across 18 outbound calls and
11 providers:

  ~ IDEMPOTENCY_FIELDS   extended to cover every output-affecting parameter the
                         audit found: negative_prompt, model_version, task_type
                         (Seedance's -vip suffix), mode (omni_reference vs
                         first_last_frames; std vs pro), quality, resolution,
                         cfg_scale, element_list, voice_list, multi_prompt,
                         voice_id, sound. Missing any of these means two
                         genuinely different requests collide on one key and the
                         second silently receives the first's result.
  + reroll               Kling exposes no seed, so "try again" is a legitimate
                         request indistinguishable from a duplicate submission.
                         An explicit counter in the hash makes the re-roll a
                         deliberate, logged decision instead of one inferred
                         from a clock.
  ~ resolved_prompt      hashed instead of the agent's intent string, because
                         moodboard and wardrobe context is assembled into the
                         prompt at call time — change the moodboard and the
                         semantic fields are identical while the output differs.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Node(BaseModel):
    """
    Every node carries an id and timestamps. All three are tool-managed — the
    agent never sets them, which is why they are optional on the model.
    """
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}  # unknown fields are a write error, never a silent merge


# ─────────────────────────────────────────────────────────────────────────────
# PROJECT
#
# Dropped: metrics (computed on read — the counters drift), script_status and
# default_episode_id (derivable), moodboard_urls, moodboard_image_url,
# style_ref_url, format, is_sample, is_free_tier, tenant_id (deprecated),
# selected_mood_id (superseded by moodboard_id), team_ids (no users behind it).
#
# Not added: `mode`. See the v1.1 note at the top of this file — the hybrid
# distinction lives on Shot.source, and a project-level copy would be a second
# source of truth with nothing reading it.
# ─────────────────────────────────────────────────────────────────────────────

ProjectType = Literal["movie", "micro_drama", "ad", "ugc", "trailer"]

# Confirmed by audit: `style` is the persisted field. `engine_style` is derived
# at read time and the derivation is inconsistent — script.py falls back through
# both, while production.py and taxonomy.py read `style` directly. The tool
# normalises on read; nothing writes engine_style.
Style = Literal["realistic", "animation_2d", "animation_3d"]


class Taxonomy(BaseModel):
    """
    Cinematography grammar — HOW the film is shot. Distinct from the moodboard,
    which is WHAT the frame looks like. The legacy auto-direct prompt appended
    this as the CINEMATOGRAPHY BLUEPRINT and instructed the model to follow its
    camera movement, lens rules, and lighting approach.

    Applies to practical coverage too: a shot list handed to a DoP is the same
    grammar, addressed to a human instead of a provider.

    `archetype` is validated against the catalogue in taxonomy_archetypes.py
    (110 entries: 50 live-action, 30 2D, 30 3D). Not a Literal — a 110-value
    union is unreadable and the catalogue changes independently of this file.
    """
    archetype: str
    match_percentage: Optional[int] = None

    # Live-action blueprint
    emotional_philosophy: Optional[str] = None
    camera_movement: Optional[str] = None
    lens_rules: Optional[str] = None
    lighting_color: Optional[str] = None

    # Animation blueprint — populated instead of the above when style is
    # animation_2d or animation_3d
    dimensionality: Optional[str] = None
    physics_logic: Optional[str] = None
    rendering_style: Optional[str] = None
    frame_rate: Optional[str] = None

    # The dimension scores that selected this archetype. Persisted today as
    # `taxonomy_measured_metrics`; kept because re-derivation has no guard and
    # without the inputs there is no way to tell whether a re-run should differ.
    character_interiority: Optional[int] = None
    thematic_subtext: Optional[int] = None
    scene_duration_pacing: Optional[int] = None
    derived_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}


class Project(Node):
    title: str
    genre: str
    type: ProjectType = "movie"
    style: Style = "realistic"
    aspect_ratio: str = "16:9"
    runtime_seconds: Optional[int] = None

    # Story grounding. The strongest instruction in the legacy prompt set
    # demanded cultural and geographic specificity — "if the story is set in
    # India, reference Indian architecture, skin tones, light quality, not
    # Hollywood defaults" — and nothing in the database held the inputs.
    logline: Optional[str] = None
    setting: Optional[str] = None              # place, region, era

    # The two style axes, deliberately separate.
    moodboard_id: Optional[str] = None         # palette and atmosphere
    taxonomy: Optional[Taxonomy] = None        # camera grammar

    # UGC only: podcast | talking_head | voiceover_broll | tutorial | vlog.
    # Selects a format skill file instead of branching in code.
    ugc_setup: Optional[str] = None

    owner_id: str
    org_id: Optional[str] = None               # org debit path is live in credit_service
    is_public: bool = False
    status: Literal["active", "archived", "deleted"] = "active"


class Moodboard(Node):
    """
    Structured, not a prose blob. These five fields are what generation tools
    assemble into consistency context at call time — which is why a single
    freeform `moodboard` string could not support deterministic assembly.
    """
    name: str
    color_palette: str
    lighting: str
    texture: str
    atmosphere: str
    image_url: Optional[str] = None
    source: Literal["generated", "uploaded"] = "generated"


# ─────────────────────────────────────────────────────────────────────────────
# EPISODE — kept because every path in the existing data goes through it, and
# micro-dramas genuinely need it. A movie has exactly one.
# ─────────────────────────────────────────────────────────────────────────────

class Episode(Node):
    number: int
    title: str
    synopsis: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# SCENE
#
# Collapsed: description/synopsis/summary → synopsis. slugline/header → slugline.
# time_of_day/time → time. The `location` string is dropped; location_id is the
# truth. int_ext parses from the slugline. Dropped ai_logs, visual_prompt, and
# context_layer — department-head notes are cheap to regenerate and go stale
# against a scene that has since been rewritten.
# ─────────────────────────────────────────────────────────────────────────────

TimeOfDay = Literal["DAY", "NIGHT", "DAWN", "DUSK", "CONTINUOUS"]


class Dialogue(BaseModel):
    speaker: str                               # may include (V.O.) / (O.S.)
    line: str
    model_config = {"extra": "forbid"}


class SetDesign(BaseModel):
    """
    Scene-specific dressing of a location. This is where the night/golden-hour
    contradiction lived in production: set_design described golden light on a
    scene whose `time` was NIGHT, and every shot inherited the error. Nothing
    here enforces agreement — the skill file tells the agent to check.
    """
    atmosphere: Optional[str] = None
    architecture_notes: Optional[str] = None
    image_views: Dict[str, str] = Field(default_factory=dict)   # wide/front/left/right/back
    model_config = {"extra": "forbid"}


class Scene(Node):
    number: int
    slugline: str                              # "INT. LUXURY APARTMENT" — repeats; never an address
    location_id: Optional[str] = None
    time: TimeOfDay
    synopsis: str
    characters: List[str] = Field(default_factory=list)   # ids, physically visible on screen
    props: List[str] = Field(default_factory=list)
    dialogue: List[Dialogue] = Field(default_factory=list)
    duration_seconds: Optional[int] = None
    set_design: Optional[SetDesign] = None
    wardrobe: Dict[str, str] = Field(default_factory=dict)   # character_id → outfit for this scene

    # `shot_listed` means shots exist. Renamed from "covered" in v1.1: to a
    # crew, covered means the footage is in the can, and the same word meaning
    # two things on one production is a misread waiting to happen.
    #
    # TOOL CONTRACT — not enforced by this model: `write` on a scene must
    # compare incoming `synopsis` and `dialogue` against stored values and mark
    # every descendant shot `stale` when either changes. Audit finding: today a
    # scene rewrite leaves its shots untouched, so they silently describe the
    # previous version of the scene. This field is where that surfaces, but
    # nothing here detects it.
    status: Literal["draft", "ready", "shot_listed", "stale"] = "draft"


# ─────────────────────────────────────────────────────────────────────────────
# SHOT — intent only.
#
# Moved to Track:  image_url, video_url, voice_url, audio_url, lip_sync_url,
#                  inpaint_url, video_status, lip_sync_status, sfx, music,
#                  video_prompt
# Moved to Run:    error_message, error_code, video_settings, provider,
#                  model_used, seedance_task_id
# Tool-assembled:  prompt, enhanced_prompt, negative_prompt, reference_image_url,
#                  reference_images, scene_description, aspect_ratio, location,
#                  time_of_day, mood, lighting
# Collapsed:       shot_type / camera_shot_type / type          → shot_type
#                  duration / estimated_duration                → duration_seconds
#                  camera_movement / camera_angle / camera_lens → shot_type +
#                                                                 camera_direction
# Dropped:         morph_to_next (a transition belongs to the timeline),
#                  character_name (superseded by characters[]),
#                  dialogue (no lip-sync system exists; the scene holds the
#                  lines and copies here would drift on rewrite)
# ─────────────────────────────────────────────────────────────────────────────

LocationAngle = Literal["wide", "front", "left", "right", "back"]

# How this shot gets made. Not how it turned out — that is Take.source.
ShotSource = Literal["generated", "practical"]


class Shot(Node):
    order: int                                 # 0-based; authoritative for sequence
    visual_action: str                         # what the camera sees — the image comes from this
    shot_type: str                             # "Tight 85mm on eyes", "Low-angle wide 24mm"
    camera_direction: Optional[str] = None     # where the camera is and what it faces
    ambient_scene: Optional[str] = None        # light quality, atmosphere, mood
    continuity_note: Optional[str] = None      # edit connection + character positions
    location_angle: Optional[LocationAngle] = None
    characters: List[str] = Field(default_factory=list)   # visible in THIS frame only
    props: List[str] = Field(default_factory=list)
    duration_seconds: int = 5                  # one continuous take: 3–15s

    # REQUIRED, and deliberately without a default.
    #
    # This is the field that decides whether a generation tool may act on this
    # shot at all. A default would let an unmigrated or malformed document read
    # as "generated", and the agent would render coverage the crew is booked to
    # shoot — the spike's invisible-ceiling failure, except the cost is a call
    # sheet rather than a missing shot.
    #
    # `from_legacy()` must set this explicitly. There is no fallback: a legacy
    # shot predates hybrid work and is therefore "generated", but that decision
    # belongs in the coercion layer where it is visible, not in a field default
    # where it is silent.
    source: ShotSource

    # `stale` is set by the tool when the parent scene's synopsis or dialogue
    # changes — see the Scene.status contract above.
    status: Literal["draft", "ready", "rendered", "stale"] = "draft"


# ─────────────────────────────────────────────────────────────────────────────
# TRACK / TAKE
#
# Tracks are horizontal: the layers of one shot, played together.
# Takes are vertical: attempts at one layer, one of them selected.
#
# `video_history` was takes without a selection field. `voice_url` and
# `audio_url` were tracks flattened into columns, which is why a shot could hold
# exactly one of each and no provenance for either.
#
# Takes are a subcollection rather than an array so a collection-group query can
# reach every take in a project. That is the eval layer's access pattern: the
# approval signal is take-level, and the rejects are the training data.
#
# HYBRID: a practical take is a take. Same collection, same review path, same
# rejection enum. That single fact is what makes a camera negative and a
# generated frame comparable — and it is the only place in the product where
# they are.
# ─────────────────────────────────────────────────────────────────────────────

TrackType = Literal["image", "video", "dialogue", "sfx", "music"]


class Track(Node):
    type: TrackType
    prompt: str                                # intent for this layer, in plain language
    selected_take_id: Optional[str] = None
    order: int = 0                             # layering order within the shot


class RejectionReason(str, Enum):
    """
    Structured because this field is the proprietary half of the eval dataset,
    and a year of free-text notes cannot be retroactively categorised. Free text
    goes alongside in `rejection_note`, never instead.

    Three blocks. The shared block applies to any take regardless of origin and
    is where the practical-vs-generated comparison actually lives — a DoP
    rejecting a real frame for lighting_mismatch and a director rejecting a
    generated one for the same reason is the signal worth having.

    Do not let practical rejects fall into `other`. That was the failure this
    enum was built to prevent, and it is what happens if the practical block
    below is missing.
    """

    # ── Shared — either origin ────────────────────────────────────────────────
    face_inconsistent = "face_inconsistent"        # identity drift from the reference
    body_anatomy = "body_anatomy"                  # hands, limbs, proportion
    wardrobe_wrong = "wardrobe_wrong"              # not the specified outfit
    lighting_mismatch = "lighting_mismatch"        # contradicts scene time or set
    grade_mismatch = "grade_mismatch"              # off-moodboard colour
    set_inconsistent = "set_inconsistent"          # background differs from the location
    composition = "composition"                    # framing does not match shot_type
    pacing = "pacing"                              # wrong speed or duration
    audio_sync = "audio_sync"                      # audio only
    quality = "quality"                            # resolution, noise, artefacts

    # ── Generated only ────────────────────────────────────────────────────────
    prompt_drift = "prompt_drift"                  # rendered something not asked for
    motion_artifact = "motion_artifact"            # warping, morphing, temporal instability

    # ── Practical only ────────────────────────────────────────────────────────
    focus_miss = "focus_miss"                      # soft where it needed to be sharp
    exposure = "exposure"                          # clipped, crushed, or wrongly stopped
    performance = "performance"                    # the take the actor gave
    continuity_break = "continuity_break"          # contradicts an adjacent take
    equipment_in_frame = "equipment_in_frame"      # boom, stand, crew, shadow
    camera_operation = "camera_operation"          # unintended shake, bad move, missed mark

    other = "other"


# Enforced by the review tool, not the model — Pydantic cannot see `source` and
# `rejection_reason` as a pair without a validator, and a validator here would
# make legacy reads fail. The tool checks membership before writing.
GENERATED_ONLY_REASONS = frozenset({
    RejectionReason.prompt_drift,
    RejectionReason.motion_artifact,
})

PRACTICAL_ONLY_REASONS = frozenset({
    RejectionReason.focus_miss,
    RejectionReason.exposure,
    RejectionReason.performance,
    RejectionReason.continuity_break,
    RejectionReason.equipment_in_frame,
    RejectionReason.camera_operation,
})


# `refs` role vocabulary. Closed by convention rather than by type, because a
# provider will add a reference kind before this file is next opened — but an
# open vocabulary in practice means five spellings of the same role and no
# usable query. Add here, do not invent at the call site.
#
#   character   identity reference for a person in frame
#   location    the set or environment
#   prop        an object in frame
#   style       moodboard or grade reference
#   first_frame start frame for a video generation
#   last_frame  end frame for a video generation
#   plate       the source take a derived take was made from — this is how a
#               Beeble relight, an upscale, or an inpaint records its lineage.
#               Without it a derived take looks like an original attempt and
#               the eval layer counts it as one.
REF_ROLES = frozenset({
    "character", "location", "prop", "style",
    "first_frame", "last_frame", "plate",
})


class Take(Node):
    """
    An asset with provenance. `source` is what keeps hybrid workflows possible
    without a rewrite: a camera negative is a take like any other, it simply has
    a slate instead of a provider.
    """

    # OPTIONAL as of v1.1. A practical take is logged at the moment of capture,
    # which is hours before the card is ingested and a URL exists. Requiring a
    # URL to write the document means the log happens later from memory, or in a
    # spreadsheet — and the metadata that makes a take findable is exactly the
    # metadata that decays.
    #
    # TOOL CONTRACT: a take with source == "generated" MUST have media_url on
    # write. A practical take may be written without one and filled in at
    # ingest. Nothing selects a take into a Timeline without a media_url.
    media_url: Optional[str] = None

    # "practical" is split from "uploaded" deliberately. Both arrive as files
    # rather than provider responses, but a camera negative and a director's
    # uploaded fix are different populations — one is the shoot, the other is a
    # patch — and merging them cannot be undone after the fact.
    source: Literal["generated", "uploaded", "practical"] = "generated"

    duration_seconds: Optional[float] = None   # actual, which often differs from intended

    # ── Present only when source == "generated" ───────────────────────────────
    provider: Optional[str] = None             # kling-v3-omni, seedance-2, gemini, elevenlabs
    model: Optional[str] = None
    resolved_prompt: Optional[str] = None      # what was actually sent, in provider dialect
    refs: List[Dict[str, str]] = Field(default_factory=list)   # [{path, role}] — see REF_ROLES
    seed: Optional[str] = None                 # Seedance accepts one; Kling does not
    reroll: int = 0                            # deliberate re-attempt of an identical request
    run_id: Optional[str] = None

    # ── Present only when source == "practical" ───────────────────────────────
    #
    # The minimum needed to find the file again. Without these a Take document
    # cannot be matched to a clip on a card, and the eval signal is attached to
    # footage nobody can locate. Three fields — resist a fourth. Crew, kit, and
    # scheduling are production logistics and do not belong in the harness tree.
    camera_roll: Optional[str] = None          # "A001" — card or magazine
    slate: Optional[str] = None                # "12A/3" — scene/setup/take as called on set
    timecode_start: Optional[str] = None       # "10:24:13:07" — HH:MM:SS:FF

    # DENORMALISED for display. Run.credits is the source of truth — it is what
    # reconciles against the transaction ledger. This copy exists so a take can
    # show its cost without a join, and must never be summed for billing.
    # Null on practical takes: a shoot day is not billed in credits.
    credits: Optional[float] = None

    # Eval signal. Nullable until judged. Rejected takes are never deleted —
    # they are the half of the dataset no competitor can replicate. Provenance
    # matters: an approval with no judge and no timestamp cannot be weighted.
    #
    # This is the field the hybrid shoot exists to feed. A DoP circling takes on
    # a monitor produces the same structured signal as a director approving
    # generated frames, against the same enum, in the same collection-group
    # query. Nobody else has both halves in one tree.
    approved: Optional[bool] = None
    rejection_reason: Optional[RejectionReason] = None
    rejection_note: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# BIBLE — characters, locations, props. One shape, three collections.
#
# `description` is authoritative: it is what the agent reads and what feeds
# generation. `traits` is structured metadata for UI forms only. If both were
# read independently they would drift exactly as prompt/visual_action did.
#
# Image fields follow one convention throughout, replacing the four names the
# audit found (image_url, ref_image_url, image_views, angle_urls):
#     image_url    — the canonical single reference
#     image_views  — angle-keyed variants, dict[str, str]
# ─────────────────────────────────────────────────────────────────────────────

class BibleEntry(Node):
    name: str
    description: str                           # prose; single source of truth for generation
    image_url: Optional[str] = None            # canonical reference
    image_views: Dict[str, str] = Field(default_factory=dict)
    aliases: List[str] = Field(default_factory=list)   # dedup across script spellings
    traits: Dict[str, Any] = Field(default_factory=dict)   # UI-facing only
    source: Literal["generated", "uploaded"] = "generated"
    status: Literal["draft", "ready"] = "draft"


class Character(BibleEntry):
    # image_views keys: primary, full_body, close_up, left_profile, right_profile
    #
    # On a hybrid production these are reference stills of the actual actor, and
    # they are what makes generated coverage match practical coverage. Same
    # field, same use — the reference just has a person behind it.
    type: Literal["human", "animal", "creature", "robot", "object"] = "human"
    role: Optional[Literal["primary", "secondary", "tertiary", "extra"]] = None
    voice_id: Optional[str] = None             # ElevenLabs or equivalent


class Location(BibleEntry):
    # image_views keys: wide, front, left, right, back.
    # Audit finding: the upload path does not populate these, so an uploaded
    # location has no angles and shots against it fall back to image_url. On a
    # hybrid shoot this is the recce photo set, and it is the highest-value
    # upload on the production — populate it.
    spatial_notes: Optional[str] = None        # room layout, for composition grounding


class Prop(BibleEntry):
    category: Optional[str] = None             # vehicle, weapon, wardrobe, food, document


# ─────────────────────────────────────────────────────────────────────────────
# SCRIPT — replaces `scripts` + `drafts`. A draft is a script with status "raw";
# that was the only difference between two collections.
# ─────────────────────────────────────────────────────────────────────────────

class Script(Node):
    name: str
    content: str
    status: Literal["raw", "parsed"] = "raw"
    source: Literal["uploaded", "generated", "breakdown_sheet"] = "uploaded"


# ─────────────────────────────────────────────────────────────────────────────
# TIMELINE — the assembled cut. References takes, not shots: the cut is made of
# specific approved attempts, and `media_op` needs somewhere to write.
#
# A hybrid cut is a timeline whose entries point at takes of both sources. There
# is nothing to add here — that the model already permits it is the point.
# ─────────────────────────────────────────────────────────────────────────────

class TimelineEntry(BaseModel):
    take_path: str                             # tree path to the chosen take
    order: int
    transition: Optional[str] = None           # cut, dissolve, morph — where morph_to_next went
    model_config = {"extra": "forbid"}


class Timeline(Node):
    name: str = "Main cut"
    entries: List[TimelineEntry] = Field(default_factory=list)
    export_url: Optional[str] = None
    status: Literal["draft", "exported"] = "draft"


# ─────────────────────────────────────────────────────────────────────────────
# RUN — replaces jobs, piapi_tasks, task_tracking, workflow_executions.
#
# Top-level, not project-scoped: provider webhooks arrive knowing only a task id.
# This is the durable-execution record — a run outlives the process that started
# it, which matters because a shot list took 151s in the spike and a video
# generation is longer still.
#
# There is no Run for a practical take. Nothing was executed, nothing was
# charged, and there is no receipt to reconcile. A practical take with a run_id
# is a bug.
#
# ORCHESTRATION — one source of truth. A batch run's `steps[]` is the plan of
# record: a resuming worker reads it and nothing else to decide what remains.
# `parent_run_id` on children is a back-reference for queries only, never
# consulted for progress. Two sources would eventually disagree.
#
# IDEMPOTENCY — Firestore has no unique constraints, so the guard cannot be a
# query. The run's document ID *is* its idempotency key, and creation uses
# `create()`, which raises AlreadyExists if the document is present. That is the
# only atomic check-and-set Firestore offers. Implemented as a query followed by
# a write, two concurrent requests would both find nothing and both charge.
# ─────────────────────────────────────────────────────────────────────────────

class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


RunKind = Literal["batch", "image", "video", "audio", "llm", "media_op", "agent_turn"]


class RunStep(BaseModel):
    """
    A planned step inside a batch run. Written before execution begins, so a
    process that dies mid-sequence leaves a plan another worker can resume.
    This is what workflow_executions.steps[] should have been.
    """
    index: int
    kind: RunKind
    target_path: str
    status: RunStatus = RunStatus.pending
    run_id: Optional[str] = None               # child Run, once started
    model_config = {"extra": "forbid"}


class Run(Node):
    # `id` is the idempotency key. See the module note above: the key is the
    # document ID and creation uses create(), not set().
    kind: RunKind
    status: RunStatus = RunStatus.pending
    target_path: str                           # tree path the result is written to
    project_id: str
    user_id: str
    org_id: Optional[str] = None               # who the credits bill to

    # Multi-step orchestration. `steps[]` on a batch run is authoritative;
    # `parent_run_id` on a child is a back-reference for querying siblings.
    parent_run_id: Optional[str] = None
    steps: List[RunStep] = Field(default_factory=list)   # batch runs only
    current_step: Optional[int] = None

    provider: Optional[str] = None
    model: Optional[str] = None
    provider_task_id: Optional[str] = None     # the receipt — how a crashed run resumes
    request: Dict[str, Any] = Field(default_factory=dict)   # enough to retry without rebuilding

    # Cost. Run.credits is the source of truth; Take.credits denormalises it.
    # transaction_id joins to users/{uid}/transactions or
    # organizations/{slug}/transactions, which today record only project_id —
    # so a 12-step run that dies at step 7 cannot be reconciled.
    credits: Optional[float] = None
    transaction_id: Optional[str] = None
    refund_transaction_id: Optional[str] = None

    attempt: int = 1
    error: Optional[str] = None
    started_at: Optional[datetime] = None

    # A provider that dies without delivering a webhook leaves a run at
    # `running` forever. A sweeper queries status == running AND
    # timeout_at < now, then fails or retries. Without this nothing ever
    # increments `attempt`.
    timeout_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# IDEMPOTENCY
#
# What the guard is for: the same instruction must not be charged twice. It is
# NOT a reproducibility guarantee — Kling exposes no seed at all, so two
# identical submissions legitimately produce different video, and Seedance is
# "highly similar, not pixel-identical" even with one.
#
# The whitelist is every parameter the provider audit found to affect output,
# across 18 calls and 11 providers. A missing parameter means two genuinely
# different requests collide on one key and the second silently receives the
# first's result — a worse failure than the double charge this prevents.
#
# Excluded and why:
#   signed URLs      Firebase Storage tokens rotate; hash the tree path instead
#   timestamps       differ on every retry
#   callback URLs    routing, not semantics
#   task ids         assigned after submission
#   retry counters   the retry is the thing being deduplicated
#
# `prompt` must be the RESOLVED prompt, after the tool has assembled moodboard,
# taxonomy, and wardrobe context into it. The agent's intent string is stable
# while the assembled output is not: change the project moodboard and every
# semantic field matches while the generated image differs.
#
# `reroll` is how a director asks for another attempt at an identical request.
# The guard fires, the agent surfaces "this exact request already ran" and asks;
# on confirmation the counter increments and the key changes. In the manual UI
# the button click is the confirmation. Without this, a legitimate re-roll is
# indistinguishable from an accidental double-submit.
#
# None of this applies to practical takes. There is no run, no key, no charge.
# ─────────────────────────────────────────────────────────────────────────────

IDEMPOTENCY_FIELDS = (
    # Prompt surface
    "prompt",              # RESOLVED, not the agent's intent
    "negative_prompt",     # Kling 3.0 Pro; Seedance does not expose it
    "multi_prompt",        # Kling multi-shot: per-segment prompts and durations

    # References — tree or blob paths, never signed URLs
    "ref_paths",
    "element_list",        # Kling v3 subject elements
    "voice_list",          # Kling v3 voice bindings

    # Model routing
    "provider",
    "model",
    "model_version",       # Seedance 2.0
    "task_type",           # Seedance 2.0, includes the -vip suffix
    "mode",                # omni_reference | first_last_frames; std | pro

    # Output shape
    "quality",
    "resolution",
    "aspect_ratio",
    "duration_seconds",
    "sound",               # native audio changes the result and the price

    # Sampling
    "seed",                # Seedance accepts one; Kling has no seed parameter
    "cfg_scale",           # Kling 3.0 Pro, 0–1, default 0.5

    # Voice
    "voice_id",            # ElevenLabs

    # Deliberate re-attempt of an otherwise identical request
    "reroll",
)


def idempotency_key(target_path: str, kind: str, request: Dict[str, Any]) -> str:
    """
    Deterministic document ID for a Run, stable across retries of one request
    and distinct for any request that would produce different output.

    Use as the document ID with create(), which fails if the run already exists:

        ref = db.collection("runs").document(idempotency_key(path, kind, req))
        try:
            ref.create(run.model_dump())
        except AlreadyExists:
            # Same instruction. Return the existing run rather than charging
            # again. If the caller intended a fresh attempt, increment
            # request["reroll"] — a decision the director makes, not the clock.
            return ref.get()
    """
    semantic = {k: request[k] for k in IDEMPOTENCY_FIELDS if k in request}
    payload = json.dumps(semantic, sort_keys=True, default=str)
    return hashlib.sha256(f"{target_path}|{kind}|{payload}".encode()).hexdigest()[:32]


# ─────────────────────────────────────────────────────────────────────────────
# THREAD / MESSAGE — persistent agent history. Neither the spike nor the earlier
# TypeScript harness had this; both kept the loop in memory, so a crashed
# process lost the session.
#
# project_id is nullable so a thread can span projects: "make this look like the
# jewelry film" is a real request a project-scoped thread cannot serve.
# ─────────────────────────────────────────────────────────────────────────────

class Thread(Node):
    title: str = "New session"
    project_id: Optional[str] = None
    user_id: str


class Message(Node):
    role: Literal["user", "assistant", "tool"]
    content: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    run_id: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# Registry — node kind → model. `write` resolves the kind from the path shape,
# looks it up here, and validates before anything reaches Firestore.
#
# Reads are lenient, writes are strict. That asymmetry is what lets the harness
# ship without migrating four years of data first — but it means every model
# needs a `from_legacy()` in the tool layer that strips and maps unknown fields
# before construction. `extra="forbid"` applies at construction, so passing a
# raw 45-field legacy shot document straight into Shot() will raise.
#
# v1.1 note for `from_legacy()` on Shot: `source` is required and has no
# default, so the coercion layer must set it. Every legacy shot predates hybrid
# work and is therefore "generated" — but write that line explicitly in
# from_legacy() where a reader can see it, and never as a field default.
# ─────────────────────────────────────────────────────────────────────────────

NODE_MODELS = {
    "project": Project,
    "moodboard": Moodboard,
    "episode": Episode,
    "scene": Scene,
    "shot": Shot,
    "track": Track,
    "take": Take,
    "character": Character,
    "location": Location,
    "prop": Prop,
    "script": Script,
    "timeline": Timeline,
    "run": Run,
    "thread": Thread,
    "message": Message,
}