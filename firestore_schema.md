# Firestore Schema — MotionX-Studio-Backend

---

## `projects`

**Path:** `projects/{project_id}`
**Source:** Pydantic model `ProjectDB` in [project.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/models/project.py#L51-L72)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `str` | ✅ | |
| `owner_id` | `str` | ✅ | |
| `title` | `str` | ✅ | |
| `genre` | `str` | ✅ | |
| `type` | `str` (Literal: movie, micro_drama, ad, ugc, trailer) | ✅ | Default: `"movie"` |
| `aspect_ratio` | `str` | ✅ | Default: `"16:9"` |
| `style` | `str` | ✅ | Default: `"realistic"` |
| `moodboard` | `list[MoodboardItem]` | ✅ | Default: `[]` |
| `ugc_setup` | `str` | ❌ | |
| `runtime_seconds` | `int` | ❌ | |
| `tenant_id` | `str` | ❌ | DEPRECATED |
| `org_id` | `str` | ❌ | |
| `team_ids` | `list[str]` | ✅ | Default: `[]` |
| `is_global` | `bool` | ✅ | Default: `False` |
| `is_public` | `bool` | ✅ | Default: `False` |
| `created_at` | `datetime` | ✅ | |
| `updated_at` | `datetime` | ✅ | |
| `status` | `str` | ✅ | Default: `"active"` |
| `script_status` | `str` (Literal: empty, processing, ready, assets_pending, production_ready) | ✅ | Default: `"empty"` |
| `default_episode_id` | `str` | ❌ | |
| `metrics` | `dict` | ✅ | Default: `{scene_count:0, character_count:0, location_count:0, prop_count:0, shot_count:0}` |

**Fields written but NOT in model (⚠ disagreement):**

| Field | Written by | Notes |
|-------|-----------|-------|
| `is_free_tier` | `project.py:147` (create_project) | Injected after `ProjectDB.dict()` |
| `is_sample` | `showcase_clone.py:67` | Only on cloned sample projects |
| `format` | `showcase_clone.py:64` | Clone copies `format` from source |
| `moodboard_urls` | `showcase_clone.py:72` | Clone-only |
| `moodboard_image_url` | `showcase_clone.py:75` | Clone + production endpoints |
| `moodboard_style` | `showcase_clone.py:76` | Clone + production endpoints |
| `style_ref_url` | `showcase_clone.py:77` | Clone-only |
| `selected_mood_id` | `production.py:1488` | Set to `None` on mood delete |
| `deleted_at` | `project.py:1156` | `SERVER_TIMESTAMP` on soft-delete |
| `error` | `task_queue.py:114` | Local-dev failure marker |
| `sample_project_id` | not written to `projects` — written to `users` | |

---

### `projects/{project_id}/episodes/{episode_id}`

**Path:** `projects/{id}/episodes/{eid}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `id` | `str` | ✅ | project.py, showcase_clone.py, script worker |
| `project_id` | `str` | ✅ | project.py, showcase_clone.py |
| `title` | `str` | ✅ | project.py, showcase_clone.py |
| `number` | `int` | ✅ | project.py, showcase_clone.py |
| `episode_number` | `int` | ✅ | project.py, showcase_clone.py |
| `type` | `str` | ✅ | project.py (movie_script, ad_script, ugc_script, trailer_script, episode) |
| `synopsis` | `str` | ✅ | project.py, showcase_clone.py |
| `created_at` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` or `datetime` |
| `runtime_seconds` | `int` | ❌ | project.py (if payload has it) |
| `script_file_url` | `str` | ❌ | showcase_clone.py |
| `status` | `str` | ❌ | jewelry_service.py |

---

### `projects/{project_id}/episodes/{eid}/scenes/{scene_id}`

**Path:** `projects/{id}/episodes/{eid}/scenes/{sid}`
**Source:** no model — inferred from write sites (showcase_clone.py, script worker)

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `id` | `str` | ✅ | showcase_clone.py, script worker |
| `scene_number` | `int` | ✅ | showcase_clone.py, script worker |
| `location` | `str` | ✅ | showcase_clone.py, script worker |
| `time_of_day` | `str` | ❌ | showcase_clone.py |
| `description` | `str` | ❌ | showcase_clone.py |
| `int_ext` | `str` | ❌ | showcase_clone.py |
| `slugline` | `str` | ❌ | showcase_clone.py |
| `header` | `str` | ❌ | showcase_clone.py |
| `synopsis` | `str` | ❌ | showcase_clone.py |
| `summary` | `str` | ❌ | showcase_clone.py |
| `characters` | `list[str]` | ❌ | showcase_clone.py |
| `location_id` | `str` | ❌ | showcase_clone.py |
| `created_at` | `datetime` | ✅ | showcase_clone.py |

---

### `projects/{project_id}/episodes/{eid}/scenes/{sid}/shots/{shot_id}`

**Path:** `projects/{id}/episodes/{eid}/scenes/{sid}/shots/{shid}`
**Source:** no model — inferred from write sites. Field set defined in [showcase_clone.py:20-33](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/showcase_clone.py#L20-L33)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `str` | ✅ | |
| `status` | `str` | ✅ | Set to `"rendered"` on clone |
| `order` | `int` | ❌ | |
| `image_url` | `str` | ❌ | |
| `video_url` | `str` | ❌ | |
| `shot_type` | `str` | ❌ | |
| `camera_shot_type` | `str` | ❌ | |
| `visual_action` | `str` | ❌ | |
| `dialogue` | `str` | ❌ | |
| `character_name` | `str` | ❌ | |
| `camera_movement` | `str` | ❌ | |
| `location` | `str` | ❌ | |
| `time_of_day` | `str` | ❌ | |
| `aspect_ratio` | `str` | ❌ | |
| `duration` | `str/int` | ❌ | |
| `camera_angle` | `str` | ❌ | |
| `camera_lens` | `str` | ❌ | |
| `lighting` | `str` | ❌ | |
| `mood` | `str` | ❌ | |
| `sfx` | `str` | ❌ | |
| `music` | `str` | ❌ | |
| `voice_url` | `str` | ❌ | |
| `audio_url` | `str` | ❌ | |
| `reference_image_url` | `str` | ❌ | |
| `reference_images` | `list[str]` | ❌ | |
| `inpaint_url` | `str` | ❌ | |
| `prompt` | `str` | ❌ | |
| `enhanced_prompt` | `str` | ❌ | |
| `negative_prompt` | `str` | ❌ | |
| `video_prompt` | `str` | ❌ | |
| `video_status` | `str` | ❌ | |
| `video_settings` | `dict` | ❌ | |
| `lip_sync_url` | `str` | ❌ | |
| `lip_sync_status` | `str` | ❌ | |
| `characters` | `list[str]` | ❌ | |
| `scene_description` | `str` | ❌ | |
| `estimated_duration` | `float` | ❌ | |
| `location_angle` | `str` | ❌ | |
| `camera_direction` | `str` | ❌ | |
| `continuity_note` | `str` | ❌ | |
| `ambient_scene` | `str` | ❌ | |
| `morph_to_next` | `bool` | ❌ | |

**Additional fields written by workers (not in SHOT_FIELDS constant):**

| Field | Written by |
|-------|-----------|
| `image_status` | task_queue.py (error marker) |
| `error_message` | task_queue.py, video worker |
| `error_code` | video worker |

---

### `projects/{project_id}/characters/{asset_id}`

**Path:** `projects/{id}/characters/{aid}`
**Source:** Pydantic model `CreateAssetRequest` in [assets.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/models/assets.py#L23-L40) (request model, not DB model)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `str` | ✅ | |
| `name` | `str` | ✅ | |
| `type` | `str` | ✅ | |
| `visual_traits` | `list[str] \| dict` | ❌ | Default: `{}` |
| `atmosphere` | `str` | ❌ | |
| `lighting` | `str` | ❌ | |
| `terrain` | `str` | ❌ | |
| `voice_config` | `dict` | ❌ | Default: `{}` |
| `prompt` | `str` | ❌ | |
| `product_metadata` | `ProductMetadata` | ❌ | Characters don't use this |
| `image_url` | `str` | ❌ | Written by assets.py generate |
| `ref_image_url` | `str` | ❌ | Written by upload-reference |
| `status` | `str` | ❌ | Written by assets.py generate |
| `last_generated_prompt` | `str` | ❌ | Written by assets.py generate |
| `created_at` | `str/datetime` | ✅ | Written as ISO string |
| `updated_at` | `Timestamp` | ❌ | `SERVER_TIMESTAMP` on update |
| `spatial_context` | `str` | ❌ | Locations only |

**⚠ Model vs write-site note:** The `CreateAssetRequest` model is a request schema, not a DB model. The actual Firestore document includes additional fields (`id`, `image_url`, `status`, `created_at`, `ref_image_url`, `last_generated_prompt`, `spatial_context`, `image_views`) that are not in the model.

### `projects/{project_id}/locations/{asset_id}`

Same schema as `characters` above — same model, same write sites.

### `projects/{project_id}/products/{asset_id}`

Same schema as `characters` above, plus `product_metadata` is populated.

---

### `projects/{project_id}/scripts/{script_id}`

**Path:** `projects/{id}/scripts/{sid}`
**Source:** no model — inferred from write sites (script worker)

Written by script worker batch writes. Field structure is dynamic (script text, metadata).

### `projects/{project_id}/drafts/{draft_id}`

**Path:** `projects/{id}/drafts/{did}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `id` | `str` | ✅ | ingest_service.py |
| `name` | `str` | ✅ | ingest_service.py |
| `content` | `str` | ✅ | ingest_service.py |
| `created_at` | `Timestamp` | ✅ | ingest_service.py |

### `projects/{project_id}/moodboard_options/{mood_id}`

**Path:** `projects/{id}/moodboard_options/{mid}`
**Source:** no model — inferred from write sites (production.py)

Written by moodboard generation endpoints. Fields are dynamic (style analysis output).

### `projects/{project_id}/cast_clusters/{cluster_id}`

**Path:** `projects/{id}/cast_clusters/{cid}`
**Source:** no model — no direct write site found in codebase. Referenced only in cleanup delete lists.

### `projects/{project_id}/meta/{meta_id}`

**Path:** `projects/{id}/meta/{mid}`
**Source:** no model — no direct write site found in codebase. Referenced only in cleanup delete lists.

---

## `users`

**Path:** `users/{uid}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `onboarding` | `dict` (map of `{tour_id: bool}`) | ❌ | user.py `complete_onboarding` |
| `welcome_email_sent` | `bool` | ❌ | user.py `complete_onboarding`, `init_user` |
| `subscription_credits` | `float` | ❌ | credit_service.py, payment.py |
| `topup_credits` | `float` | ❌ | credit_service.py, payment.py |
| `credits` | `float` | ❌ | credit_service.py (Increment), payment.py |
| `plan` | `str` | ❌ | payment.py (`"free"`, plan_type) |
| `low_credit_email_sent` | `bool` | ❌ | credit_service.py |
| `free_credits_expired` | `bool` | ❌ | user.py `init_user` |
| `sample_project_cloned` | `bool` | ❌ | user.py `init_user` |
| `sample_project_id` | `str` | ❌ | user.py `init_user` |
| `free_tier_usage` | `dict` (map of `{limit_type: int}`) | ❌ | free_tier_service.py, workers |
| `credits_expire_at` | `Timestamp` | ❌ | Read by user.py (not written by backend — likely set by frontend/admin) |

**Note:** The `users` document is created by the frontend (`syncUserToFirestore`), not by the backend. The backend only merges/updates fields.

### `users/{uid}/subscription/current`

**Path:** `users/{uid}/subscription/current`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `status` | `str` (`"authenticated"`, `"active"`, `"pending"`, `"halted"`, `"expired"`) | ✅ | payment.py webhook |
| `plan_id` | `str` | ✅ | payment.py |
| `plan_name` | `str` | ❌ | payment.py `_tx_renew_subscription` |
| `razorpay_sub_id` | `str` | ✅ | payment.py |
| `next_billing_at` | `any` | ❌ | payment.py `_tx_renew_subscription` |
| `current_period_start` | `Timestamp` | ❌ | `SERVER_TIMESTAMP` |
| `amount` | `float` | ❌ | payment.py |
| `currency` | `str` | ❌ | payment.py |
| `credits_per_cycle` | `int` | ❌ | payment.py |
| `limits` | `dict` | ❌ | payment.py |
| `cancel_at_period_end` | `bool` | ❌ | payment.py |
| `cancel_requested_at` | `Timestamp` | ❌ | `SERVER_TIMESTAMP` |
| `expires_at` | `any` | ❌ | payment.py |
| `ended_at` | `Timestamp` | ❌ | `SERVER_TIMESTAMP` (on cancel) |
| `previous_plan` | `str` | ❌ | payment.py `_tx_cancel_subscription` |
| `updated_at` | `Timestamp` | ❌ | `SERVER_TIMESTAMP` |

### `users/{uid}/usage/limits`

**Path:** `users/{uid}/usage/limits`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `credits_monthly_allowance` | `int` | ✅ | payment.py `_tx_renew_subscription`, `_tx_cancel_subscription` |
| `storage_limit_gb` | `int` | ✅ | payment.py |
| `projects_limit` | `int` | ✅ | payment.py |
| `seats_limit` | `int` | ✅ | payment.py |

### `users/{uid}/transactions/{auto_id}`

**Path:** `users/{uid}/transactions/{auto_id}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `amount` | `float` | ✅ | credit_service.py, workers |
| `type` | `str` (`"debit"`, `"refund"`, `"charge"`) | ✅ | credit_service.py, workers |
| `description` | `str` | ✅ | credit_service.py, workers |
| `timestamp` | `Timestamp/datetime` | ✅ | |
| `user_uid` | `str` | ❌ | credit_service.py (tx path only) |
| `user_email` | `str` | ❌ | credit_service.py |
| `project_id` | `str` | ❌ | credit_service.py |
| `balanceAfter` | `float` | ❌ | credit_service.py (tx path only) |
| `split_detail` | `dict` | ❌ | credit_service.py (tx path only) |

### `users/{uid}/kling_elements/{element_id}`

**Path:** `users/{uid}/kling_elements/{eid}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `id` | `str` | ✅ | production.py |
| `user_id` | `str` | ✅ | production.py |
| `created_at` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` |
| `kling_data` | `dict` | ✅ | production.py (full Kling API response) |
| `name` | `str` | ✅ | production.py |
| `description` | `str` | ❌ | production.py |
| `cover_url` | `str` | ✅ | production.py |
| `type` | `str` | ✅ | production.py (`refer_type`) |

---

## `organizations`

**Path:** `organizations/{slug}`
**Source:** Partial model `OrganizationListItem` in [enterprise.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/models/enterprise.py#L36-L45) (read model, not DB model)

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `organization_name` | `str` | ✅ | enterprise_service.py |
| `slug` | `str` | ✅ | enterprise_service.py |
| `allowed_domains` | `list[str]` | ✅ | enterprise_service.py |
| `tenant_id` | `str` | ✅ | enterprise_service.py (GCIP mode: tenant ID; seed mode: `""`) |
| `provider_id` | `str` | ✅ | enterprise_service.py (empty initially, updated by `configure_idp`) |
| `is_active` | `bool` | ✅ | enterprise_service.py |
| `billing_plan` | `str` | ✅ | enterprise_service.py (`"enterprise"`) |
| `credits_balance` | `float` | ✅ | enterprise_service.py (0 initially), credit_service.py (Increment) |
| `admins` | `list[str]` | ✅ | enterprise_service.py, organization.py (ArrayUnion/ArrayRemove) |
| `role_bindings` | `dict` (map of `{email: role}`) | ❌ | enterprise_service.py `seed_enterprise_workspace`, organization.py |
| `subscription_credits` | `float` | ❌ | credit_service.py `_deduct_org_credits` |
| `topup_credits` | `float` | ❌ | credit_service.py, payment.py |

**⚠ Model vs write-site note:** `OrganizationListItem` is a read/response model, not a DB model. It lacks `billing_plan`, `credits_balance`, `role_bindings`, `subscription_credits`, `topup_credits`, which are all written to Firestore.

### `organizations/{slug}/transactions/{auto_id}`

**Path:** `organizations/{slug}/transactions/{auto_id}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `amount` | `float` | ✅ | credit_service.py, payment.py, workers |
| `type` | `str` (`"debit"`, `"refund"`, `"top_up"`, `"charge"`) | ✅ | credit_service.py, payment.py, workers |
| `description` | `str` | ✅ | credit_service.py, payment.py, workers |
| `timestamp` | `Timestamp/datetime` | ✅ | |
| `user_uid` | `str` | ❌ | credit_service.py, payment.py, workers |
| `user_email` | `str` | ❌ | credit_service.py |
| `project_id` | `str` | ❌ | credit_service.py |
| `payment_id` | `str` | ❌ | payment.py |
| `balanceAfter` | `float` | ❌ | credit_service.py (tx path only) |
| `split_detail` | `dict` | ❌ | credit_service.py (tx path only) |

---

## `transactions`

**Path:** `transactions/{auto_id}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `uid` | `str` | ✅ | payment.py |
| `type` | `str` (`"payment_failed"`, `"subscription_charge"`, `"subscription_cancelled"`, `"top_up"`, `"subscription_cancel_requested"`) | ✅ | payment.py |
| `amount` | `float` | ❌ | payment.py |
| `currency` | `str` | ❌ | payment.py |
| `payment_id` | `str` | ❌ | payment.py |
| `payment_method` | `str` | ❌ | payment.py |
| `source` | `str` | ✅ | Always `"Razorpay"` |
| `timestamp` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` |
| `org_id` | `str` | ❌ | payment.py (top-up only) |
| `credits_added` | `int` | ❌ | payment.py |
| `plan` | `str` | ❌ | payment.py (subscription_charge) |
| `razorpay_sub_id` | `str` | ❌ | payment.py |
| `triggered_by` | `str` | ❌ | payment.py (`"razorpay_webhook"`, `"user"`) |
| `reason` | `str` | ❌ | payment.py |
| `razorpay_ended_at` | `any` | ❌ | payment.py (cancel) |
| `previous_plan` | `str` | ❌ | payment.py (cancel) |
| `new_plan` | `str` | ❌ | payment.py (cancel) |
| `current_plan` | `str` | ❌ | payment.py (cancel_requested) |
| `cancel_at_period_end` | `bool` | ❌ | payment.py (cancel_requested) |
| `package_id` | `str` | ❌ | payment.py (top-up) |
| `error_code` | `str` | ❌ | payment.py (payment_failed) |
| `error_reason` | `str` | ❌ | payment.py (payment_failed) |
| `split_detail` | `dict` | ❌ | payment.py |

---

## `task_tracking`

**Path:** `task_tracking/{task_id}`
**Source:** Pydantic model `TaskRecord` in [task_tracking.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/models/task_tracking.py#L26-L41)

| Field | Type | Required | Model | Written |
|-------|------|----------|-------|---------|
| `task_id` | `str` | ✅ | ✅ | ✅ |
| `job_id` | `str` | ❌ | ✅ | ✅ |
| `project_id` | `str` | ❌ | ✅ | ✅ |
| `task_type` | `str` (TaskType enum) | ✅ | ✅ | ✅ |
| `status` | `str` (TaskStatus enum) | ✅ | ✅ | ✅ |
| `queue_name` | `str` | ✅ | ✅ | ✅ |
| `endpoint` | `str` | ✅ | ✅ | ✅ |
| `user_email` | `str` | ❌ | ✅ | ✅ |
| `metadata` | `dict` | ❌ | ✅ | ✅ |
| `attempt_number` | `int` | ✅ | ✅ Default: 0 | ✅ |
| `scheduled_at` | `datetime` | ❌ | ✅ | ✅ |
| `started_at` | `datetime` | ❌ | ✅ | ✅ |
| `resolved_at` | `datetime` | ❌ | ✅ | ✅ |
| `error_details` | `str` | ❌ | ✅ | ✅ |

**Fields written but NOT in model (⚠ disagreement):**

| Field | Written by | Notes |
|-------|-----------|-------|
| `cost_credits` | `task_tracker.py:102` | Observability field |
| `model_name` | `task_tracker.py:103` | Observability field |
| `resolution` | `task_tracker.py:104` | Observability field |
| `prompt` | `task_tracker.py:105` | Truncated to 500 chars |
| `error_code` | `task_tracker.py:156` | Written on fail if provided |

---

## `jobs`

**Path:** `jobs/{job_id}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `status` | `str` (`"processing"`, `"queued"`, etc.) | ✅ | script.py, ingest_service.py |
| `progress` | `str` | ✅ | script.py, ingest_service.py |
| `created_at` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` |

Additional fields written via `set(data, merge=True)` by ingest_service.py and script worker (variable content from pipeline output).

---

## `playgrounds`

### `playgrounds/{uid}/generations/{generation_id}`

**Path:** `playgrounds/{uid}/generations/{gid}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `status` | `str` (`"generating"`, `"ready"`, `"error"`) | ✅ | playground.py, task_queue.py, image worker |
| `prompt` | `str` | ✅ | playground.py |
| `shot_type` | `str` | ❌ | playground.py |
| `aspect_ratio` | `str` | ❌ | playground.py |
| `style` | `str` | ❌ | playground.py |
| `characters` | `list[str]` | ❌ | playground.py |
| `location` | `str` | ❌ | playground.py |
| `products` | `list[str]` | ❌ | playground.py |
| `provider` | `str` | ❌ | playground.py |
| `model_tier` | `str` | ❌ | playground.py |
| `output_resolution` | `str` | ❌ | playground.py |
| `created_at` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` |
| `image_url` | `str` | ❌ | image worker (on success) |
| `error_message` | `str` | ❌ | task_queue.py (local dev error), image worker |

---

## `piapi_tasks`

**Path:** `piapi_tasks/{task_id}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `project_id` | `str` | ✅ | video worker |
| `episode_id` | `str` | ✅ | video worker |
| `scene_id` | `str` | ✅ | video worker |
| `shot_id` | `str` | ✅ | video worker |
| `user_id` | `str` | ✅ | video worker |
| `org_id` | `str` | ❌ | video worker |
| `provider` | `str` | ✅ | video worker (`"seedance-2"`, `"kling-v3"`) |
| `task_type` | `str` | ✅ | video worker |
| `prompt` | `str` | ❌ | video worker |
| `duration` | `str/int` | ❌ | video worker |
| `credits_charged` | `float` | ❌ | video worker |
| `tracking_id` | `str` | ❌ | video worker |
| `context_type` | `str` | ❌ | video worker (`"project"`, `"playground"`) |
| `context_id` | `str` | ❌ | video worker |
| `generation_id` | `str` | ❌ | video worker |
| `is_free_tier` | `bool` | ❌ | video worker |
| `created_at` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` |

---

## `jewelry_runs`

**Path:** `jewelry_runs/{run_id}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `run_id` | `str` | ✅ | jewelry_automation.py |
| `user_uid` | `str` | ✅ | jewelry_automation.py |
| `project_id` | `str` | ✅ | jewelry_automation.py |
| `template_id` | `str` | ✅ | jewelry_automation.py |
| `brand_preset` | `str` | ✅ | jewelry_automation.py |
| `status` | `str` (`"queued"`, `"processing"`, `"error"`, `"completed"`) | ✅ | jewelry_automation.py, jewelry_service.py |
| `progress` | `int` | ✅ | jewelry_automation.py (0-100) |
| `step_desc` | `str` | ✅ | jewelry_automation.py |
| `inputs` | `dict` | ✅ | jewelry_automation.py |
| `sku` | `str` | ✅ | jewelry_automation.py |
| `product_description` | `str` | ❌ | jewelry_automation.py |
| `aspect_ratio` | `str` | ❌ | jewelry_automation.py |
| `credits_charged` | `float` | ✅ | jewelry_automation.py, jewelry_service.py |
| `final_video_url` | `str` | ❌ | jewelry_automation.py (null initially) |
| `error` | `str` | ❌ | jewelry_automation.py (null initially), jewelry_service.py |
| `created_at` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` |
| `org_id` | `str` | ❌ | jewelry_automation.py |

---

## `workflow_executions`

**Path:** `workflow_executions/{execution_id}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `id` | `str` | ✅ | workflow_executor.py |
| `workflow_id` | `str` | ✅ | workflow_executor.py |
| `user_uid` | `str` | ✅ | workflow_executor.py |
| `user_email` | `str` | ✅ | workflow_executor.py |
| `project_id` | `str` | ❌ | workflow_executor.py |
| `pipeline_type` | `str` | ✅ | workflow_executor.py |
| `title` | `str` | ✅ | workflow_executor.py |
| `status` | `str` (`"pending"`, `"running"`, `"completed"`, `"failed"`) | ✅ | workflow_executor.py |
| `steps` | `list[dict]` | ✅ | workflow_executor.py |
| `user_inputs` | `dict` | ✅ | workflow_executor.py |
| `total_estimated_credits` | `float` | ✅ | workflow_executor.py |
| `total_credits_charged` | `float` | ✅ | workflow_executor.py |
| `current_step` | `int` | ✅ | workflow_executor.py |
| `created_at` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` |
| `updated_at` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` |

Step sub-fields (updated via dotted paths like `steps.{i}.status`):

| Field | Type | Written by |
|-------|------|-----------|
| `steps.{i}.status` | `str` | workflow_executor.py |
| `steps.{i}.output_url` | `str` | workflow_executor.py |
| `steps.{i}.error` | `str` | workflow_executor.py |
| `steps.{i}.credits_charged` | `float` | workflow_executor.py |

---

## `processed_webhooks`

**Path:** `processed_webhooks/{event_id}`
**Source:** no model — inferred from write sites

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `event` | `str` | ✅ | payment.py (Razorpay event type) |
| `timestamp` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` |

---

## `system_metadata`

**Path:** `system_metadata/{doc_id}`
**Source:** no model — inferred from write sites

### `system_metadata/global_feed`

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `feed` | `list[dict]` (list of `FeedItem`) | ✅ | jobs.py |
| `items_count` | `int` | ✅ | jobs.py |
| `last_updated` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` |

### `system_metadata/community_feed`

| Field | Type | Required | Written by |
|-------|------|----------|------------|
| `feed` | `list[dict]` (list of `CommunityFeedItem`) | ✅ | jobs.py |
| `items_count` | `int` | ✅ | jobs.py |
| `last_updated` | `Timestamp` | ✅ | `SERVER_TIMESTAMP` |

---

## `configs`

**Path:** `configs/{doc_id}`
**Source:** no model — inferred from write sites

### `configs/moodboard_manifest`

Written by one-off init scripts: [init_mood_realistic.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/static/moodboard/init_mood_realistic.py), [init_mood_animation.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/static/moodboard/init_mood_animation.py). Full overwrite with manifest data (dynamic structure).

### `configs/free_tier_limits`

Read-only from backend perspective — read by `free_tier_service.py` and script worker. Not written by any router or worker (assumed seeded manually or by admin).

### `configs/token_pricing`

Read-only from backend perspective — read by `pricing.py`. Not written by any router or worker.

---

## `series` (legacy)

**Path:** `series/{series_id}/episodes/{eid}/scenes/{sid}/shots/{shid}`
**Source:** no model — inferred from write sites in [production_workers.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/production_workers.py)

Legacy collection. Same shot structure as `projects/.../shots`. Functions `worker_generate_shot` and `worker_animate_shot` in `production_workers.py` write to this path. These functions are not wired to any currently mounted router — likely dead code.

---

## Model vs Write-Site Disagreements Summary

| Collection | Issue |
|-----------|-------|
| `projects` | `is_free_tier`, `is_sample`, `format`, `moodboard_urls`, `moodboard_image_url`, `moodboard_style`, `style_ref_url`, `selected_mood_id`, `deleted_at`, `error` are all written but not in `ProjectDB` model |
| `organizations` | `OrganizationListItem` is a read schema. `billing_plan`, `credits_balance`, `role_bindings`, `subscription_credits`, `topup_credits` are written but absent from the model |
| `task_tracking` | `cost_credits`, `model_name`, `resolution`, `prompt`, `error_code` are written but not in `TaskRecord` model |
| `projects/.../characters,locations,products` | `CreateAssetRequest` is a request model. Firestore docs contain `id`, `image_url`, `status`, `created_at`, `ref_image_url`, `last_generated_prompt`, `spatial_context`, `image_views` which are not in the model |
| `users` | No model exists at all |
| `transactions` | No model exists at all |
