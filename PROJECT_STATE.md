# MotionX Filmmaking Harness — Project State

*Last updated: August 2026*

---

## The goal

Replace MotionX Studio's linear Python pipeline with a single agent: minimal
general tools, the project database as its filesystem, domain knowledge in skill
files the agent reads at runtime instead of hardcoded pipeline steps.

The shape is borrowed from Pi. Pi is powerful because its tools are general
primitives — read, write, bash — over a substrate the agent can freely explore.
The trap in filmmaking is building a tool set that is small but *domain-shaped*
(`generate_storyboard()`, `add_to_timeline()`), which is the existing pipeline
made callable: same rigidity, now with latency and nondeterminism on top.

So the design question was: **what is the filesystem of a film?** The answer is
the project data — scenes, shots, characters, sets, takes — exposed as a tree the
agent can list, read, and write, with a few generation primitives underneath.
Then "make shot 12 match the lighting in shot 4" is something the agent composes
rather than something someone built a code path for.

**Scope:** pure AI generation. Not hybrid, not traditional production. Input-side
hybrid already works (real location photos are treated as references); output-side
hybrid stays possible because a take is modelled as an asset with provenance
rather than as a generation.

---

## Phase 1 — Prompt archaeology

### What was extracted

Two repo-agent passes over the legacy backend produced a full inventory of every
LLM and generation prompt: 25 prompt sites across 5 files in the first pass, 12
more across 5 files in the second.

The second pass mattered more than the first. It surfaced:

- **`context_builder.py` §9A** — six department heads (gaffer, VFX, hair &
  makeup, key grip, colorist, subtext) analysing a scene. The best filmmaking
  artifact in the codebase.
- **`context_builder.py` §9B** — a director's-cut pass that verifies candidate
  shots against set design, wardrobe, and lighting, then curates down.
- **`agent_playbook.md`** — 542 lines driving an existing DOM-based agent.
- **`spatial_agent.py`** — the 4-wall burst-frame generator, bilingual because
  Seedance has character limits.

A third targeted pass traced the auto-direct flow end to end: `[data-agent='auto-direct']`
→ `POST /suggest_shots` → Cloud Task → three sequential LLM calls (context layer,
shot division, director's cut).

### The distinction that organised everything

The legacy prompts fuse two things:

**Domain knowledge** — what a shot list needs, how a scene decomposes, why the
master location precedes the sub-area in a slugline. True whether MotionX exists
or not. **Extract all of it.**

**Control flow** — the order steps run in. This is precisely what the agent
replaces.

Applied to the ~17-rule auto-direct prompt:

| Category | Share | Destination |
|---|---|---|
| Genuine craft | ~40% | skill files |
| Provider dialect | ~20% | tools |
| Compensating for blindness | ~25% | deleted — the agent reads the DB |
| Pipeline mechanics | ~15% | deleted |

The clearest example of the third category: "EVERY shot MUST set `location` to
the EXACT location string." That rule exists because the LLM receives a flat
payload and cannot see where the shot lives. In the harness a shot sits under its
scene and location is structural.

The clearest example of the fourth: "Generate 50% MORE shots than you normally
would — we will curate down." That single line is why shot division is three LLM
calls instead of one.

Also notable: rule 16 spends heavily on teaching the model to assign
`location_angle` from a five-value enum with variety quotas — followed by **four
post-processing passes that override the model's choice anyway.**

### The existing agent

`DIRECTOR_INSTRUCTION` plus the playbook is already a single agent with minimal
tools — `click_element`, `type_text`, `scroll_to_element`, `navigate_to_page`.
The Pi shape is there. The substrate is the DOM.

Which is why the playbook is ~90% UI navigation: selector tables, page-detection
heuristics, "wait 700ms after clicking a card," modal recovery procedures. Swap
the DOM for the project tree and nearly all of it evaporates — not refactored,
deleted.

---

## Phase 2 — The spike

**Question:** can a general agent, given skill files and the project tree,
produce a shot list as good as the three-month-tuned pipeline?

**Setup:** `spike_tools.py` (four tools over real Firestore), `agent_gemini.py`
(the loop), two skill files. Deliberately Gemini 3.1 Pro — the same model family
the pipeline uses — so the diff isolates architecture rather than model quality.
Both write paths in dry run throughout.

### The four tools

| Tool | Role |
|---|---|
| `list(path)` | children as summaries, never full documents |
| `read(path)` | one node plus its observed schema |
| `write(path, patch)` | create or update any node |
| `generate_image(prompt, refs, write_to)` | generation primitive, dry-run |

Skills live *in the tree* at `/skills`, read with the same `read` tool. No new
tool — the agent finds them by listing.

### Results

Four runs on the "Not Yet" project:

| Request | Turns | Time | Peak context |
|---|---|---|---|
| List the scenes | 3 | 15s | 1.4k |
| Shot list, scene 1 | 9 | 151s | 24.5k |
| Shot list, scene 2 | 8 | 71s | 14.7k |
| What is this project about | 4 | 21s | 7.2k |
| What characters are these | 3 | 15s | 3.9k |

**On shot listing.** The agent listed `/skills` unprompted on turn 1 and read
both files before touching the scene. Coverage followed the craft: establishing
wide with no people, then a detail insert, faces from shot 3. Objects got their
own frames — zipper, earring, lipstick, heels. Eye-lines anchored to real
geography (bed left, mirror right) and held across ten shots. Subtext threaded
through every `ambient_scene`. Character traits from the bible reached the
prompts, which the pipeline never did.

On scene 2 it produced seven shots, not ten — stopped where the beat ended
rather than padding to a target. Direct consequence of deleting the
over-generate-then-curate rule.

**On the open-ended queries.** "What is this project about" has no route, no
button, no prompt in the legacy system. The agent read the project, listed
scenes, read both, and synthesised the premise, the themes, and the mirror
reveal across two scenes — in 21 seconds. That is the strongest artifact from the
week: the shot list proves parity, this proves capability the pipeline
architecturally cannot have.

### What the spike measured

- **Context is not the constraint.** Peak 24.5k, then 14.7k after trimming noise
  fields. Trivial against a 1M window. The larger driver is the agent's own
  output — 2,172 tokens of shot patches in one turn, which persist for the rest
  of the run.
- **`list`-returns-summaries is what makes it work.** 45 characters listed for a
  few hundred tokens; reading 45 documents would be 30k+.
- **Latency rules out synchronous HTTP.** 71–151s for a shot list. Video is
  longer. Durable execution is required, not optional.
- **Four general tools covered every request**, including two nobody designed
  for. The minimal-general-tools bet holds against real data.
- **Readable errors are a feature.** `/bible/products` failed, the message named
  the valid paths, the agent retried correctly in the same turn.

### The compression

Three LLM calls → one loop. 542 lines of playbook → two skill files. ~17 prompt
rules → roughly six that survived.

### One failure worth recording

`write` could not create nodes, so when the agent wrote 13 shots the last three
failed and it settled for 10. Not a wrong number — but a *plumbing constraint
silently converted into a creative decision*, invisible in the final output.

The general lesson: every capability gap becomes an invisible ceiling. If
`generate_audio` doesn't exist, the agent stops writing sound design and never
mentions it. Mitigations are better tool errors (say what *is* possible) and a
system-prompt line requiring the agent to surface when tool failures changed its
approach. Human-in-the-loop does *not* catch this class — the agent doesn't know
anything went wrong.

---

## Phase 3 — Schema

Five iterations, each driven by an audit or review rather than intuition.

### The starting problem

The Firestore audit found **two Pydantic models across the entire database**
(`ProjectDB`, `TaskRecord`), both disagreeing with their write sites. Ten fields
land on `projects` that aren't in the model. `users`, `transactions`, and every
scene, shot, character, and location have no model at all.

So it isn't that the schemas are wrong. There are almost none. Enforced writes
would be the first time they existed.

The shot document is a **~45-field god object** mixing four concerns, with
`shot_type`/`camera_shot_type`, `duration`/`estimated_duration`, and
`prompt`/`enhanced_prompt`/`visual_action` all holding the same information under
different names. Four collections — `jobs`, `piapi_tasks`, `task_tracking`,
`workflow_executions` — do the same job with no authority between them.

### The core split

```
intent            → Shot          what the director wants
generation inputs → assembled by the tool at call time, never stored
outputs           → Track / Take  media with provenance
execution state   → Run           async jobs, receipts, cost
```

Shot 45 → 11 fields. Scene 13 → 10. Character 15 → 8.

### Locked decisions

**`extra="forbid"` on every model.** A field not in the schema is a write error,
not a silent merge. This is how `is_free_tier`, `is_sample`, `format`, and
`moodboard_urls` arrived on projects without anyone deciding.

**Tracks and takes are different axes.** Tracks are horizontal — the layers of
one shot (video, dialogue, sfx, music), played together. Takes are vertical —
attempts at one layer, one selected. `video_history` was takes without a
selection field; `voice_url` and `audio_url` were tracks flattened into columns.

**Takes are a subcollection, not an array**, so a collection-group query reaches
every take in a project. That is the eval layer's access pattern. Rejected takes
are never deleted — they are the proprietary half of the dataset.

**`RejectionReason` is a 13-value enum** with free text alongside, never instead.
A year of prose cannot be retroactively categorised, and this field is the moat.

**`description` is authoritative on bible entries; `traits` is UI-only.** If both
were read independently they would drift exactly as `prompt`/`visual_action` did.

**Moodboard and taxonomy are separate axes.** Moodboard is palette and
atmosphere — what the frame looks like. Taxonomy is camera grammar — how it's
shot, drawn from a 110-entry archetype catalogue. Dropping taxonomy was an
omission caught in review.

**One `Run` collection** replaces four, top-level rather than project-scoped,
because provider webhooks arrive knowing only a task id.

### The three live bugs the audit confirmed

Every structural review point turned out to describe production behaviour, not a
hypothetical:

1. **No idempotency guard on the debit path.** Two `processed_webhooks`
   collections exist *downstream* because this guard was missing upstream.
2. **No resume path for multi-step runs.** `workflow_executions` stalls
   permanently if the executing process dies. `piapi_tasks` and `task_tracking`
   don't reference a parent.
3. **Transactions carry only `project_id`.** A 12-step run that dies at step 7
   cannot be reconciled against what was charged. Failed steps leave completed-step
   credits consumed with no rollback.

The schema answers each: `Run.id` *is* the idempotency key (created with
`create()`, which is Firestore's only atomic check-and-set — there are no unique
constraints); `steps[]` on a batch run is the plan of record, written before
execution; `transaction_id` joins the ledger.

### Idempotency, specifically

The guard prevents **double charging for one instruction**. It is not a
reproducibility guarantee — Kling exposes no seed parameter at all, so two
identical submissions legitimately produce different video, and Seedance is
"highly similar, not pixel-identical" even with one.

`IDEMPOTENCY_FIELDS` is a 20-field whitelist covering every output-affecting
parameter found across 18 outbound calls and 11 providers. Two things it must get
right:

- **`prompt` means the resolved prompt**, after the tool assembles moodboard,
  taxonomy, and wardrobe context. The agent's intent string is stable while the
  assembled output is not.
- **References are tree paths, never signed URLs.** Firebase Storage tokens
  rotate; hashing them produces a fresh key every retry and the guard silently
  does nothing while appearing to work.

`Take.reroll` handles the case Kling's missing seed creates: a director asking
for another attempt at an identical request. The guard fires, the agent asks, and
on confirmation the counter increments and the key changes. In the manual UI the
button click is the confirmation.

---

## Architecture decisions

**One backend, two front doors.**

```
Manual UI ──┐
            ├──→ harness service ──→ same tools, same Firestore
Agent    ───┘
```

The manual UI must keep working without the agent — most users will never talk
to it, and it is the revenue. So the legacy backend can't simply be dropped;
instead both paths converge on one tool layer. "Generate shot" from a button and
`generate_image` from the agent hit the same code.

Three consequences:

- Tools cannot assume an agent is present. Validation, cost accounting, and
  provenance live in the tool body.
- `ask_director` has no meaning on the manual path, so approval gating lives in
  the **agent loop**, not inside the tools.
- Tools must assemble their own context. A button click has no reasoning behind
  it, so the tool reads the moodboard and taxonomy itself — which is correct
  anyway, and fixes a real bug: today's stored prompts freeze the moodboard at
  generation time and go stale when it changes.

**Stack:** Python and FastAPI. The Pydantic argument was weak (there are almost
no models to preserve). The real argument is the provider layer — `workers/image/main.py`
alone is 4,296 lines of Kling, Seedance, Luma, PiAPI, and Gemini integration with
retry logic and tag dialects debugged in production. Rewriting it produces zero
new capability.

**Strangler fig, not rewrite.** New service, same Firestore. Reads tolerate the
old shape via `from_legacy()`; writes enforce the new one. UI buttons repoint a
few at a time. Legacy routes are deleted when traffic reaches zero, not on a plan.

---

## What's next

**Immediate — the Run lifecycle.** How a turn creates a batch run, writes its
plan, spawns children, resumes after a crash, and reconciles credits. This
determines whether tools are synchronous or enqueue, which shapes every
signature. Design before writing code.

**Then, in order:**

1. The eight tools as real code — `list`, `read`, `write`, `generate_image`,
   `generate_video`, `media_op`, `ask_director`, `search` — validating every
   write against the schema, with `from_legacy()` on reads.
2. FastAPI wrapper: `/tools/{name}` for the UI, `/agent/turn` for the loop.
3. Provider adapters lifted from `workers/` as a library.
4. Migration: repoint UI buttons incrementally.

**Deferred, deliberately:** the eval layer (needs the services arm's
approval data; the schema reserves the hooks), and HERMES self-improvement (needs
volume the current user base can't produce — tuning against noise otherwise).

---

## Findings worth acting on independently of the harness

These are live production bugs surfaced by the audits. None depend on the
harness shipping.

- **Scene rewrites leave existing shots untouched.** Rewrite a scene and its shot
  list silently describes the previous version. No staleness marking anywhere.
- **No idempotency guard on the credit debit path.** A retry double-charges.
- **Multi-step runs have no resume path.** Process death stalls them permanently
  with credits consumed and no rollback.
- **Character generation applies the moodboard; shot generation may not.**
  Observed on one project: character prompts carried the project's Midnight Noir
  style verbatim while every shot used unrelated descriptors.
- **Stored prompts freeze the moodboard at generation time.** Change the
  moodboard and every stored prompt is stale.
- **Counters in `metrics` drift** — `scene_count: 59` alongside `shot_count: 10`
  on a project with shots in one scene.
- **The location upload path doesn't populate `image_views`**, so uploaded
  locations have no angles and shots against them fall back to a single image.
- **Duplicate worker code**: `_worker_generate_context_layer` and
  `_worker_verify_and_curate_shots` exist in both `context_builder.py` and the
  script worker, already described as "slightly simplified" — drift in progress.

---

## Artifacts

| File | What it is |
|---|---|
| `schema.py` | Locked v1. Fifteen models, `IDEMPOTENCY_FIELDS`, `idempotency_key()` |
| `spike_tools.py` | Four tools over Firestore, both write paths dry-run |
| `agent_gemini.py` | The loop, ~200 lines, Gemini SDK |
| `skills/scene-context.md` | Six department heads |
| `skills/shot-listing.md` | Scene → shot list |
| `runs/*.json` | Five run transcripts — the evidence |
| `prompt_inventory.md` | 37 prompt sites, verbatim |
| `codebase_analysis.md` | Seven-question audit |
| `idempotency_key_parameter_audit.md` | 18 calls, 11 providers, parameters classified |
| `benchmark_scene1.json` | Pipeline output for the diff |

**Back up `runs/` outside the spike directory.** The spike is meant to be
deleted; those transcripts are the evidence for the rewrite.
