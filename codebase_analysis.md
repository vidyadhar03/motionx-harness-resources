# Codebase Architecture Analysis — 7 Questions

---

## 1. STYLE vs ENGINE_STYLE

### 1a. Which field is read at each decision point that branches on realistic vs animation_2d vs animation_3d?

**`engine_style`** is the field name read at every branch site. It is always a local variable or function parameter — never read directly from Firestore at the branch point.

| Branch Site | File | Line(s) |
|---|---|---|
| `find_top_archetypes()` — forks to `ANIMATION_2D_ARCHETYPES` / `ANIMATION_3D_ARCHETYPES` / `LIVE_ACTION_ARCHETYPES` | [taxonomy_matcher.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/taxonomy_matcher.py#L57-L62) | 57–62 |
| `analyze_semantic_metrics()` — adapts LLM evaluation lens | [taxonomy_ai.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/taxonomy_ai.py#L45) | 45 |
| `generate_silent_taxonomy()` — animation-specific top_k | [workers/script/main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L635) | 635, 711, 752 |
| `build_character_prompt()` — animation prompt variants | [workers/script/main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L1284-L1311) | 1284, 1308, 1311 |
| Script worker `process_episode_logic()` — fallback archetypes | [workers/script/main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L1632) | 1632 |
| Image worker — animation style prompt injection | [workers/image/main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L2838) | 2838, 2981, 3604 |
| `build_luma_prompt()` — Luma engine style branching | [luma_engine.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/luma_engine.py#L139) | 139, 261 |
| Script worker `extract_assets()` — animation branch | [workers/script/main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L2691) | 2691 |

### 1b. Which field is WRITTEN to the project document, and by what code?

**`style`** is the field written to Firestore. It is set during project creation via the Pydantic model:

- [ProjectCreateRequest.style](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/models/project.py#L21) → default `"realistic"`
- Written to Firestore at [project.py:148](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/project.py#L148) (`batch.set(project_ref, project_dict)`)

**`engine_style` is NEVER written as a persistent field on the project document** (with one exception: the script worker writes it into the `moodboard_options` subcollection — [workers/script/main.py:1471](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L1471) — which is a task payload, not the project doc itself).

### 1c. Are they the same value, different values, or does one derive from the other?

**`engine_style` derives from `style` at read-time, via a fallback chain.** The pattern is consistent across the codebase:

```python
engine_style = project_data.get("engine_style", project_data.get("style", "realistic"))
```

Evidence:
- [app/routers/script.py:528](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/script.py#L528), [script.py:656](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/script.py#L656)
- [workers/script/main.py:2629](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L2629)

**Both inconsistently**, however: the `production.py` router uses a simpler pattern that skips the `engine_style` field entirely:

```python
"engine_style": project_data.get("style", "realistic"),
```

Evidence: [production.py:2488](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/production.py#L2488), [2703](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/production.py#L2703), [2793](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/production.py#L2793), [2955](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/production.py#L2955), [3146](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/production.py#L3146), [3244](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/production.py#L3244), [3412](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/production.py#L3412)

And the taxonomy router uses yet another variant — reads only `style`:

```python
engine_style = project_data.get("style", "realistic")
```

Evidence: [taxonomy.py:164](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/taxonomy.py#L164)

> [!WARNING]
> **Inconsistency finding**: The `engine_style` Firestore field is referenced by `get("engine_style", get("style", ...))` in script.py, but `production.py` and `taxonomy.py` skip it and read `style` directly. If someone ever writes `engine_style` to the project doc, the production router would ignore it.

### 1d. Full set of values each can hold

| Field | Values | Source |
|---|---|---|
| `style` | `"realistic"`, `"animation_2d"`, `"animation_3d"`, `""` (empty string from frontend) | [ProjectCreateRequest](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/models/project.py#L21) — free string, default `"realistic"` |
| `engine_style` | `"realistic"`, `"animation_2d"`, `"animation_3d"` | Derived from `style`. Branching code checks `.lower()` for `"animation"`, or exact match `"animation_2d"` / `"animation_3d"` |

---

## 2. TAXONOMY STORAGE

### 2a. Where is the result stored?

Two-phase storage on the **project document** at `projects/{project_id}`:

1. **Pending** (before user selection): field `taxonomy_pending`
   - [taxonomy.py:190–194](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/taxonomy.py#L190-L194)

2. **Final** (after user locks in archetype): field `taxonomy_profile`
   - [taxonomy.py:254–257](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/taxonomy.py#L254-L257)
   - `taxonomy_pending` is deleted (via `firestore.DELETE_FIELD`)

Additionally, the script worker saves to the project doc:
- `candidate_archetypes` (list) — [workers/script/main.py:1661](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L1661)
- `taxonomy_measured_metrics` (dict) — [workers/script/main.py:1662](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L1662)

### 2b. Complete shape of the stored object

**`taxonomy_pending`** (transient):
```json
{
  "metrics": {
    "dialogue_action_ratio": int,       // 0–10
    "fragmentation_whitespace": int,    // 0–10
    "character_interiority": int,       // 0–10
    "thematic_subtext": int,            // 0–10
    "scene_duration_pacing": int        // 0–10
  },
  "top_matches": [                      // list of up to 10
    {
      "id": str,                        // e.g. "Poetic_Realism"
      "name": str,                      // e.g. "Poetic Realism"
      "match_percentage": int,          // 0–100
      "ideal_metrics": { same 5 keys }, // archetype's ideal scores
      "blueprint": {                    // live-action or animation variant
        // Live-action keys:
        "emotional_philosophy": str,
        "camera_movement": str,
        "lens_rules": str,
        "lighting_color": str,
        // Animation keys differ (e.g. "dimensionality", "physics_logic", "rendering_style", "frame_rate")
      }
    }
  ]
}
```

**`taxonomy_profile`** (final locked-in): a single item from `top_matches` — same shape as one match entry above.

### 2c. Are dimension scores persisted or discarded?

**Persisted.** They are saved in two places:
1. `taxonomy_pending.metrics` on the project doc — [taxonomy.py:191](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/taxonomy.py#L191)
2. `taxonomy_measured_metrics` on the project doc — [workers/script/main.py:1662](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L1662)

Note: `taxonomy_pending` is deleted when the user selects, but `taxonomy_measured_metrics` survives.

### 2d. Fixed catalogue of archetypes

Yes. Defined as Python constants in [app/core/taxonomy_archetypes.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/core/taxonomy_archetypes.py):

| Constant | Count |
|---|---|
| `LIVE_ACTION_ARCHETYPES` | **50** |
| `ANIMATION_2D_ARCHETYPES` | **30** |
| `ANIMATION_3D_ARCHETYPES` | **30** |
| **Total** | **110** |

A duplicate copy exists at [workers/script/taxonomy_archetypes.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/taxonomy_archetypes.py) for the standalone script worker.

### 2e. Is taxonomy ever re-derived?

**Yes.** Two paths can derive it:

1. **API router** `POST /generate-taxonomy` — [taxonomy.py:98](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/taxonomy.py#L98) — callable by the user at any time
2. **Script worker** `generate_silent_taxonomy()` — [workers/script/main.py:1596–1601](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L1596-L1601) — runs automatically during script ingestion

There is no guard preventing re-derivation; each run overwrites `candidate_archetypes` and `taxonomy_measured_metrics`.

---

## 3. CREDIT CHARGING AND TRANSACTION RECEIPTS

### 3a. Debit function signatures and bodies

The full credit service is at [credit_service.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py).

**Public API entry point:**
```python
def charge_user(
    uid: str,
    cost: float,
    action_name: str,
    org_id: Optional[str] = None,
    user_email: Optional[str] = None,
    project_id: Optional[str] = None,
) -> float:  # returns new_balance
```
[credit_service.py:257–376](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py#L257-L376)

Routes to one of two transactional functions:
- `_deduct_personal_credits()` — [credit_service.py:123–181](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py#L123-L181)
- `_deduct_org_credits()` — [credit_service.py:184–252](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py#L184-L252)

Both use `@firestore.transactional` — the balance deduction and receipt are written atomically.

### 3b. Transaction document fields

Built by `_build_tx_doc()` at [credit_service.py:93–120](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py#L93-L120), then enriched inside the transactional functions:

| Field | Type | Notes |
|---|---|---|
| `amount` | float | Negative for debits, positive for refunds |
| `type` | str | `"debit"` or `"refund"` |
| `description` | str | e.g. `"Image Generation"` or `"REFUND: PiAPI failed..."` |
| `timestamp` | ServerTimestamp | |
| `user_uid` | str (optional) | Set on org transactions to identify who triggered it |
| `user_email` | str (optional) | |
| `project_id` | str (optional) | |
| `balanceAfter` | float | Total balance after this transaction |
| `split_detail` | dict | `{sub_used, topup_used, sub_remaining, topup_remaining}` |

Written to:
- **Personal**: `users/{uid}/transactions/{auto_id}` — [credit_service.py:178–179](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py#L178-L179)
- **Org**: `organizations/{slug}/transactions/{auto_id}` — [credit_service.py:249–250](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py#L249-L250)

### 3c. Reference back to job/task/shot?

**Yes — `project_id`** is the only back-reference. There is **no** `job_id`, `task_id`, `shot_id`, or `scene_id` stored on the transaction document.

### 3d. Transaction document ID generation

**Auto-ID.** Both paths use `.document()` (no argument = Firestore auto-generated ID):
- Personal: `user_ref.collection("transactions").document()` — [credit_service.py:178](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py#L178)
- Org: `org_ref.collection("transactions").document()` — [credit_service.py:249](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py#L249)

Refunds use `.add()` which is also auto-ID: [credit_service.py:411](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py#L411), [432](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py#L432)

### 3e. Refund path

`refund_user()` at [credit_service.py:379–436](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/credit_service.py#L379-L436).

The refund path **does NOT locate the original charge**. It simply increments `topup_credits` and `credits` (or `credits_balance` for orgs) by the amount, and writes a new transaction doc with `type: "refund"` and a description. There is no foreign key to the original debit transaction.

Refunds are triggered from:
- Webhook failure handler — [webhook.py:376–384](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/webhook.py#L376-L384) (reads `credits_charged` from `piapi_tasks` metadata)
- Burst extraction failure — [webhook.py:291–297](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/webhook.py#L291-L297)

### 3f. Idempotency / duplicate-charge guard on the debit path

**No.** There is no idempotency key, no deduplication token, and no guard against calling `charge_user()` twice for the same job. The `@firestore.transactional` decorator provides atomicity within a single call but does not prevent duplicate calls.

---

## 4. WEBHOOK DEDUPLICATION

### 4a. Which collections exist

| Collection | Provider | Written at | Read at |
|---|---|---|---|
| `processed_webhooks` | Razorpay (payments) | [payment.py:406–415](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/payment.py#L406-L415) | [payment.py:407](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/payment.py#L407) |
| `processed_piapi_webhooks` | PiAPI (video gen) | [webhook.py:174–177](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/webhook.py#L174-L177) | [webhook.py:167–169](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/webhook.py#L167-L169) |

### 4b. Deduplication key

| Collection | Key | Source |
|---|---|---|
| `processed_webhooks` | `X-Razorpay-Event-Id` header (or payment entity ID fallback) | [payment.py:403](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/payment.py#L403) |
| `processed_piapi_webhooks` | `task_id` from the PiAPI payload | [webhook.py:157,167](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/webhook.py#L157) |

### 4c. Which providers deliver webhooks vs. are polled?

| Provider | Mode | Evidence |
|---|---|---|
| **PiAPI** (Seedance, Kling) | **Webhook** in production, **polling** in local dev | [webhook.py:135](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/webhook.py#L135); [workers/video/main.py:1054–1067](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/video/main.py#L1054-L1067) — conditional on `is_local_dev` |
| **Razorpay** | **Webhook** only | [payment.py:382](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/payment.py#L382) |
| **Gemini** (image gen) | **Synchronous** — not polled, not webhook | Image worker calls Gemini API inline and waits for response |

### 4d. For polled providers (PiAPI local dev), any guard against duplicate task submission?

**No explicit guard.** The video worker in local dev mode polls in a `while` loop ([workers/video/main.py:1066–1068](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/video/main.py#L1066-L1068)). The `piapi_tasks` document is written with the task_id as the document ID ([video/main.py:1029](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/video/main.py#L1029)), which gives a natural dedup key for the task metadata — but there's no check at **submission time** to prevent enqueueing the same shot twice.

---

## 5. MULTI-STEP JOB ORCHESTRATION

### 5a. What creates a workflow_execution?

`create_execution()` in [workflow_executor.py:33–83](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/workflow_executor.py#L33-L83), called from the `/execute` endpoint at [workflow.py:230–237](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/workflow.py#L230-L237).

The only entry point is `POST /api/v1/workflow/execute`.

### 5b. Resume path if process dies mid-sequence

**There is no resume path.** The execution stalls permanently.

The chain advances via `on_worker_completion()` in [workflow_hooks.py:17–64](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/workflow_hooks.py#L17-L64), which calls `advance_workflow()` in [workflow_executor.py:345–434](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/workflow_executor.py#L345-L434). This hook fires from within the worker process. If that process dies between completing a step and calling `on_worker_completion`, the `workflow_execution` doc remains stuck at `status: "running"` with the step marked `"running"`. There is no cron, health check, or reconciliation loop that detects stalled executions.

### 5c. Do jobs/piapi_tasks/task_tracking reference a parent workflow_execution?

**Partially.** The worker payload includes `workflow_execution_id` and `workflow_step` ([workflow_executor.py:150–152](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/workflow_executor.py#L150-L152)). However:

- `piapi_tasks` documents: **No** — the `piapi_tasks` schema doesn't include `workflow_execution_id` ([workers/video/main.py:1029–1047](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/video/main.py#L1029-L1047))
- `task_tracking` documents: **No** — `TaskTracker.schedule_task()` does not record `workflow_execution_id` ([task_tracker.py:63–111](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/core/task_tracker.py#L63-L111))
- `jobs` collection: not used by the workflow system

The `workflow_execution_id` only exists transiently in the Cloud Tasks payload.

### 5d. When a step fails, what happens to credits for completed steps?

**Nothing — they are consumed permanently.** There is no rollback. `advance_workflow()` tallies `total_credits_charged` but only as an accounting field ([workflow_executor.py:380–383](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/workflow_executor.py#L380-L383)). If step 2 fails after step 1 charged credits, the credits from step 1 are not refunded. The workflow status is set to `"failed"` but no refund logic is triggered.

---

## 6. SHOT ↔ SCENE DIALOGUE

### 6a. Does any shot document store dialogue?

**No — shot documents do not store a `dialogue` or `dialogues` field.** Dialogue is stored on the **scene** document as `dialogues: [{speaker: str, line: str}, ...]`:

- Written at [workers/script/main.py:2097](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L2097): `"dialogues": scene.get("dialogues", [])`
- Schema: `[{speaker: str, line: str}]` — [workers/script/main.py:886–892](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L886-L892)

Dialogue is **baked into** the shot's `video_prompt` text (as inline quoted speech) and `image_prompt` text at shot generation time — but not as a structured field. The LLM is instructed to include dialogue verbatim in `video_prompt`: [workers/script/main.py:3311–3313](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/script/main.py#L3311-L3313).

### 6b. How does lip-sync determine which text to speak?

**There is no lip-sync feature in the codebase.** No references to `lip_sync`, `lipsync`, or `lip-sync` were found anywhere. The voice pipeline is a **Voice AI Director** (WebSocket-based Whisper STT → Gemini → TTS) at [voice_director.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/voice_director.py), which is a conversational UI control agent — not a per-shot lip-sync system.

### 6c. When a scene is rewritten (rewrite_scene / extend_scene), what happens to existing shots?

**They are left alone.** Neither `rewrite_scene` nor `extend_scene` touches the shots subcollection:

- `rewrite_scene()` at [script.py:690–745](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/script.py#L690-L745) — returns new text to the frontend. It does **not** write back to Firestore at all (no `scene_ref.update`).
- `extend_scene()` at [script.py:2174–2265](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/script.py#L2174-L2265) — generates a **new** scene object and returns it. Does not modify existing scenes or shots.
- `update_scene()` at [script.py:2072–2086](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/script.py#L2072-L2086) — updates scene fields but does not cascade to shots.

**Existing shots are never invalidated or regenerated automatically** when a scene is edited.

---

## 7. REFERENCE IMAGE FIELDS

### 7a. Which fields exist per asset type?

#### Characters (`projects/{pid}/characters/{cid}`)

| Field | Shape | Written by |
|---|---|---|
| `image_url` | `str` — single GCS URL | AI generation: [assets.py:576](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L576); Upload: [assets.py:824](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L824) |
| `ref_image_url` | `str` — single GCS URL | User upload: [assets.py:701](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L701) |

#### Locations (`projects/{pid}/locations/{lid}`)

| Field | Shape | Written by |
|---|---|---|
| `image_url` | `str` — single GCS URL (the wide/primary view) | AI generation: [assets.py:536](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L536); Upload: [assets.py:824](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L824) |
| `image_views` | `dict` — `{wide: url, front: url, left: url, right: url, back: url}` | AI generation: [assets.py:537–539](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L537-L539) (starts with `{wide: url}`, more views added later) |
| `ref_image_url` | `str` — single GCS URL | User upload: [assets.py:701](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L701) |

Set design (on scene doc, not location): `set_design.image_urls` is `dict{front, right, back, left}` — written by burst extraction: [webhook.py:265](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/webhook.py#L265)

#### Products (`projects/{pid}/products/{pid}`)

| Field | Shape | Written by |
|---|---|---|
| `image_url` | `str` — single GCS URL | AI generation: [assets.py:576](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L576); Upload: [assets.py:824](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L824) |
| `ref_image_url` | `str` — single GCS URL | User upload: [assets.py:701](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L701) |

> [!NOTE]
> `angle_urls` does NOT appear anywhere in the codebase. `image_urls` appears only on `set_design` (scene subcollection), not on asset docs.

### 7b. Keys used in dict-shaped fields

| Field | Keys |
|---|---|
| `image_views` (locations) | `wide`, `front`, `left`, `right`, `back` — [workers/image/main.py:1099](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L1099), [assets.py:537](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L537) |
| `set_design.image_urls` (scenes) | `front`, `right`, `back`, `left` — [webhook.py:57](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/webhook.py#L57) (`WALL_ORDER`) |

### 7c. Which field does the shot generation path actually read?

**For characters:** `image_url` (with wardrobe portrait_url as priority override)
- [workers/image/main.py:871](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L871): `ref_url = c_data.get("image_url")`
- Priority: wardrobe `portrait_url` > `image_url`
- [workers/image/main.py:856–861](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L856-L861)

**For locations:** `image_views` (dict, angle-aware), with `image_url` as legacy fallback
- [workers/image/main.py:1013–1123](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L1013-L1123)
- Priority chain: `set_design.image_urls[angle]` > `image_views[location_angle]` > `image_views` all views fallback > `image_url` legacy

**For products:** `image_url`
- [workers/image/main.py:950–951](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L950-L951)

### 7d. Are any fields written by more than one code path with different shapes?

**Yes — `image_url` for locations.** It is written as:
1. A **wide view URL** during AI generation: [assets.py:536](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L536) (always the wide/overhead)
2. A **user-uploaded image URL** via upload: [assets.py:824](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/assets.py#L824) (arbitrary angle from user)

Both write a single `str`, so the shape is consistent, but the *semantic meaning* differs (AI path = wide view; upload path = whatever the user uploaded).

For `image_views`, only the AI generation path initializes it (with `{wide: url}`) — the upload path does **not** populate `image_views`, which means an uploaded location has `image_url` but no `image_views`, and the shot gen path falls through to the `image_url` legacy path.
