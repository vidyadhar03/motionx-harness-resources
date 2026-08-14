# Idempotency Key — Parameter Audit

Every outbound generation call in the MotionX codebase, with every parameter classified as:

| Category | Meaning | Hash? |
|---|---|---|
| **OUTPUT‑AFFECTING** | Changes what the provider returns | ✅ YES |
| **ROUTING** | Selects which provider/endpoint but doesn't change the result for the same provider | ⚠️ YES (composite key) |
| **VOLATILE** | Changes between identical requests due to tokens, timestamps, or randomness | ❌ NO — needs stable substitute |
| **METADATA** | Bookkeeping only (task IDs, user IDs, Firestore paths) | ❌ NO |

---

## 1. Gemini Image Generation (Storyboard Shots)

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L1380-L1402)  
> **Endpoint**: `POST /worker/generate-image-gemini`  
> **API call**: `client.aio.models.generate_content(model=..., contents=..., config=...)`

| Parameter | Source | Category | Justification |
|---|---|---|---|
| `model` (e.g. `gemini-3-pro-image-preview` / `gemini-3.1-flash-image-preview`) | `MODEL_PRO` / `MODEL_FLASH` env var, selected by `model_tier` | OUTPUT‑AFFECTING | Different model = different image |
| `contents` (multimodal prompt array) | Built by `build_gemini_prompt()` — see sub-parameters below | OUTPUT‑AFFECTING | Core semantic input |
| `aspect_ratio` | `ImageGenPayload.aspect_ratio` (default `"16:9"`) | OUTPUT‑AFFECTING | Changes composition |
| `image_size` | Derived from `output_resolution`: `{"1k":"2K","2k":"2K","4k":"4K"}` | OUTPUT‑AFFECTING | Changes pixel dimensions |
| `response_modalities` | Always `["IMAGE"]` | METADATA | Constant |
| `automatic_function_calling` | Always `disabled` | METADATA | Constant |

### Sub-parameters embedded in `contents` (all OUTPUT‑AFFECTING)

| Sub-parameter | Source field | Notes |
|---|---|---|
| `shot_prompt` | `ImageGenPayload.shot_prompt` | Core action description |
| `shot_type` | `ImageGenPayload.shot_type` (default `"Wide Shot"`) | Framing instruction |
| `char_list` | `ImageGenPayload.char_list` | Which characters appear |
| `location` / `location_id` | `ImageGenPayload.location`, `.location_id` | Environment selection |
| `location_angle` | `ImageGenPayload.location_angle` | Camera angle in set |
| `camera_direction` | `ImageGenPayload.camera_direction` | Spatial camera description |
| `camera_transform` | `ImageGenPayload.camera_transform` (dict: x,y,z,rx,ry,fov) | 3D camera position → NL text |
| `style` | `ImageGenPayload.style` (default `"realistic"`) | Rendering style |
| `continuity_note` | `ImageGenPayload.continuity_note` | Inter-shot continuity |
| `ambient_scene` | `ImageGenPayload.ambient_scene` | Background extras |
| `product_list` | `ImageGenPayload.product_list` | Props to include |
| `ref_image_urls` / `ref_image_url` | `ImageGenPayload.ref_image_urls` | Composition guide images |
| `background_url` | `ImageGenPayload.background_url` | Skybox viewport capture |
| `pg_style` | `ImageGenPayload.pg_style` (Playground only) | Inline style override |
| `context_type` | `ImageGenPayload.context_type` | Controls asset resolution path (project vs playground) |
| `continuity_shot_id` | `ImageGenPayload.continuity_shot_id` | Override for N-1 continuity |

> [!WARNING]
> **Reference images are VOLATILE**: Character portraits, location images, set design images, style references, and continuity shots are all fetched from GCS URLs containing ephemeral `firebaseStorageDownloadTokens`. The *content* (bytes) is what matters, not the URL. You need a content-based identifier (e.g. GCS object path without the token, or a content hash).

> [!IMPORTANT]
> **DB-derived context is OUTPUT‑AFFECTING but indirect**: `build_gemini_prompt()` fetches project moodboard style (`color_palette`, `lighting`, `texture`, `atmosphere`), scene mood overrides, character visual traits, wardrobe overrides, location spatial context, and set design URLs from Firestore. All of these affect the prompt text and reference images. For idempotency, you must either:
> 1. Hash the *final assembled prompt + image bytes*, OR
> 2. Hash the *DB document versions/timestamps* of all fetched documents

| Parameter | Category | Justification |
|---|---|---|
| `project_id`, `episode_id`, `scene_id`, `shot_id` | ROUTING + METADATA | Determines Firestore path; also selects which DB context feeds the prompt |
| `user_id` | METADATA | Billing only |
| `org_id` | METADATA | Billing routing only |
| `model_tier` | ROUTING | Selects model (already covered above) |
| `task_id` (tracking_id) | METADATA | Cloud Tasks tracking |
| `credits_charged` | METADATA | Refund amount |
| `is_free_tier` | METADATA | Free tier counter |
| `image_gen_id` | METADATA | History tracking ID |
| `output_resolution` | OUTPUT‑AFFECTING | Maps to `image_size` — already covered |

---

## 2. Gemini Image — Moodboard Generation

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L2715-L2929)  
> **Endpoint**: `POST /worker/generate-mood-image`

| Parameter | Source | Category |
|---|---|---|
| `mood.name` | `MoodImagePayload.mood` | OUTPUT‑AFFECTING |
| `mood.image_prompt` | `MoodImagePayload.mood` | OUTPUT‑AFFECTING |
| `mood.color_palette` | `MoodImagePayload.mood` | OUTPUT‑AFFECTING |
| `mood.lighting` | `MoodImagePayload.mood` | OUTPUT‑AFFECTING |
| `mood.texture` | `MoodImagePayload.mood` | OUTPUT‑AFFECTING |
| `mood.atmosphere` | `MoodImagePayload.mood` | OUTPUT‑AFFECTING |
| `genre` | `MoodImagePayload.genre` | OUTPUT‑AFFECTING |
| `engine_style` | `MoodImagePayload.engine_style` | OUTPUT‑AFFECTING |
| `taxonomy_profile` | `MoodImagePayload.taxonomy_profile` | OUTPUT‑AFFECTING (blueprint tokens) |
| `model` | Always `MODEL_FLASH` for Gemini fallback | OUTPUT‑AFFECTING |
| `aspect_ratio` | Always `"16:9"` | OUTPUT‑AFFECTING (constant) |
| `image_provider` | Resolved at runtime (Luma or Gemini) | ROUTING |
| `project_id`, `option_id` | Firestore path | METADATA |

---

## 3. Gemini Image — Scene Asset / Set Design

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L2932-L3500)  
> **Endpoint**: `POST /worker/image/generate-scene-asset`

| Parameter | Source | Category |
|---|---|---|
| `image_prompt` | `SceneAssetPayload.image_prompt` | OUTPUT‑AFFECTING |
| `asset_type` | `SceneAssetPayload.asset_type` (set_design/wardrobe/style_reference) | OUTPUT‑AFFECTING |
| `engine_style` | `SceneAssetPayload.engine_style` | OUTPUT‑AFFECTING |
| `target_angle` | `SceneAssetPayload.target_angle` | OUTPUT‑AFFECTING (selects camera instruction) |
| `mode` | `SceneAssetPayload.mode` (anchor_only / expand_legacy / None) | OUTPUT‑AFFECTING |
| `anchor_image_url` | `SceneAssetPayload.anchor_image_url` | OUTPUT‑AFFECTING (VOLATILE — GCS URL) |
| `topography_360` | `SceneAssetPayload.topography_360` | OUTPUT‑AFFECTING (per-wall descriptions) |
| `location_name` / `location_id` | `SceneAssetPayload` | OUTPUT‑AFFECTING (fetches location image + spatial context) |
| `model` | Always `MODEL_PRO` | OUTPUT‑AFFECTING |
| `aspect_ratio` | Always `"16:9"` | OUTPUT‑AFFECTING (constant) |
| `project_id`, `episode_id`, `scene_id` | Firestore path | ROUTING + METADATA |

---

## 4. Seedream Image Generation

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L1547-L1868)  
> **Endpoint**: `POST /worker/generate-image-seedream`  
> **API call**: `POST {SEEDREAM_URL}` (Volcano Engine)

| Parameter | Sent to API | Category |
|---|---|---|
| `model` | `SEEDREAM_MODEL` env var (default `"seedream-1-5-pro"`) | OUTPUT‑AFFECTING |
| `prompt` | Assembled from same fields as Gemini (see §1 sub-params) | OUTPUT‑AFFECTING |
| `size` | Always `"2K"` | OUTPUT‑AFFECTING |
| `response_format` | Always `"url"` | METADATA |
| `sequential_image_generation` | Always `"disabled"` | OUTPUT‑AFFECTING |
| `watermark` | Always `false` | OUTPUT‑AFFECTING |
| `image` (reference image URLs array) | Assembled from characters, products, locations, continuity shots | OUTPUT‑AFFECTING (VOLATILE — GCS URLs) |

> All `ImageGenPayload` fields from §1 apply identically — they feed the prompt assembly.

---

## 5. Luma uni-1 Image Generation

> **File**: [luma_engine.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/luma_engine.py#L358-L543)  
> **Endpoint**: `POST /worker/generate-image-luma` (via worker), also used inline for moodboard  
> **API call**: `POST {LUMA_API_BASE}/generations`

| Parameter | Sent to API | Category |
|---|---|---|
| `prompt` | Built by `build_luma_shot_prompt()` or `build_luma_moodboard_prompt()` | OUTPUT‑AFFECTING |
| `aspect_ratio` | From payload (default `"16:9"`) | OUTPUT‑AFFECTING |
| `model` | Always `"uni-1"` (constant `LUMA_MODEL`) | OUTPUT‑AFFECTING |
| `image_ref` | Array of `{"url": url}` — up to 9 image URLs | OUTPUT‑AFFECTING (VOLATILE — GCS URLs) |

### Luma Shot Prompt sub-parameters (all OUTPUT‑AFFECTING)

| Sub-parameter | Source |
|---|---|
| `shot_prompt` | Core action description |
| `shot_type` | Framing (Wide, Close-Up, etc.) |
| `genre` | Project genre |
| `engine_style` | Render style |
| `characters` | Character descriptions (name, age, hair, clothing, vibe) |
| `location_name` / `location_tags` | Environment descriptors |
| `products` | Visible props |
| `camera_angle` / `camera_direction` / `camera_transform_text` | Camera positioning |
| `color_palette` / `lighting` / `texture` / `atmosphere` / `project_style` | Visual style context |
| `ambient_scene` | Background extras |
| `image_refs` | Reference image descriptors |

---

## 6. Blockade Labs — 360° Skybox

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L4026-L4250)  
> **Endpoint**: `POST /worker/generate-skybox`  
> **API call**: `POST {BLOCKADE_LABS_BASE_URL}/skybox`

| Parameter | Sent to API | Category |
|---|---|---|
| `prompt` | From payload, enhanced by Gemini Vision analysis (if `image_url` present) | OUTPUT‑AFFECTING |
| `negative_text` | Default: `"people, characters, humans, animals, text, watermark"` | OUTPUT‑AFFECTING |
| `skybox_style_id` | Default: `2` (realistic) | OUTPUT‑AFFECTING |
| `enhance_prompt` | Always `true` | OUTPUT‑AFFECTING |
| `control_image` | Binary image data from `image_url` (Nano Banana image as structure guide) | OUTPUT‑AFFECTING (VOLATILE — GCS URL) |
| `image_url` (source for Vision analysis + control_image) | Payload field | OUTPUT‑AFFECTING (VOLATILE) |

> [!IMPORTANT]
> The Gemini Vision analysis step generates a *non-deterministic* `enhanced_prompt` from the `image_url`. This means even with the same inputs, the enhanced prompt may vary slightly. For idempotency, you should hash the *original* `prompt` + `image_url` content, NOT the enhanced prompt.

| Parameter | Category |
|---|---|
| `project_id`, `location_id` | METADATA |
| `user_id`, `org_id` | METADATA |

---

## 7. Kling v2 — Image-to-Video (Direct API)

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/video/main.py#L408-L528)  
> **Endpoint**: `POST /worker/animate-kling`  
> **API call**: `POST {KLING_API_BASE}/videos/image2video`

| Parameter | Sent to API | Category |
|---|---|---|
| `model_name` | `KLING_MODEL` env var (default `"kling-v2-6"`) | OUTPUT‑AFFECTING |
| `image` | `image_url` from payload | OUTPUT‑AFFECTING (VOLATILE — GCS URL) |
| `prompt` | From payload | OUTPUT‑AFFECTING |
| `cfg_scale` | Always `0.5` | OUTPUT‑AFFECTING |
| `mode` | Always `"pro"` | OUTPUT‑AFFECTING |
| `duration` | Always `"5"` | OUTPUT‑AFFECTING |
| `sound` | `"on"` or `"off"` from payload | OUTPUT‑AFFECTING |
| `image_tail` | `end_frame_url` from payload (optional) | OUTPUT‑AFFECTING (VOLATILE) |

---

## 8. Kling v3 — Text-to-Video (Direct API)

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/video/main.py#L1492-L1636)  
> **Endpoint**: `POST /worker/text2video-kling-v3`  
> **API call**: `POST {KLING_API_BASE}/videos/text2video`

| Parameter | Sent to API | Category |
|---|---|---|
| `model_name` | `KLING_MODEL_V3` env var (default `"kling-v3"`) | OUTPUT‑AFFECTING |
| `prompt` | From payload | OUTPUT‑AFFECTING |
| `mode` | Default `"pro"` | OUTPUT‑AFFECTING |
| `aspect_ratio` | Default `"16:9"` | OUTPUT‑AFFECTING |
| `duration` | Default `"5"` | OUTPUT‑AFFECTING |
| `sound` | `"on"` or `"off"` | OUTPUT‑AFFECTING |
| `negative_prompt` | Optional | OUTPUT‑AFFECTING |
| `cfg_scale` | Optional | OUTPUT‑AFFECTING |
| `multi_shot` | Boolean | OUTPUT‑AFFECTING |
| `shot_type` | Only when `multi_shot=true` | OUTPUT‑AFFECTING |
| `multi_prompt` | Only when `multi_shot=true` | OUTPUT‑AFFECTING |
| `element_list` | Optional (Kling character/IP elements) | OUTPUT‑AFFECTING |
| `voice_list` | Optional | OUTPUT‑AFFECTING |
| `watermark` | Boolean → `watermark_info.enabled` | OUTPUT‑AFFECTING |

---

## 9. Kling v3 — Image-to-Video (Direct API)

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/video/main.py#L1639-L1800)  
> **Endpoint**: `POST /worker/i2v-kling-v3`  
> **API call**: `POST {KLING_API_BASE}/videos/image2video`

| Parameter | Sent to API | Category |
|---|---|---|
| `model_name` | `KLING_MODEL_V3` (default `"kling-v3"`) | OUTPUT‑AFFECTING |
| `image` | `image_url` from payload | OUTPUT‑AFFECTING (VOLATILE) |
| `prompt` | From payload | OUTPUT‑AFFECTING |
| `mode` | Default `"pro"` | OUTPUT‑AFFECTING |
| `aspect_ratio` | Default `"16:9"` | OUTPUT‑AFFECTING |
| `duration` | Default `"5"` | OUTPUT‑AFFECTING |
| `sound` | `"on"` or `"off"` | OUTPUT‑AFFECTING |
| `image_tail` | `end_frame_url` (optional) | OUTPUT‑AFFECTING (VOLATILE) |
| `negative_prompt` | Optional | OUTPUT‑AFFECTING |
| `cfg_scale` | Optional | OUTPUT‑AFFECTING |
| `multi_shot` | Boolean | OUTPUT‑AFFECTING |
| `shot_type` | Only when `multi_shot=true` | OUTPUT‑AFFECTING |
| `multi_prompt` | Only when `multi_shot=true` | OUTPUT‑AFFECTING |
| `element_list` | Optional | OUTPUT‑AFFECTING |
| `voice_list` | Optional | OUTPUT‑AFFECTING |
| `watermark` | Boolean → `watermark_info.enabled` | OUTPUT‑AFFECTING |

---

## 10. Kling v3 Omni (via PiAPI)

> **File**: [preflight_kling_omni.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/services/preflight_kling_omni.py#L171-L220), [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/video/main.py#L2051)  
> **Endpoint**: `POST /worker/omni-kling-v3`  
> **API call**: `POST {PIAPI_BASE_URL}/task` with `task_type: "omni_video_generation"`

| Parameter | Sent to PiAPI | Category |
|---|---|---|
| `model` | Always `"kling"` | ROUTING |
| `task_type` | Always `"omni_video_generation"` | ROUTING |
| `version` | Always `"3.0"` | OUTPUT‑AFFECTING |
| `prompt` | Tag-injected prompt (auto-adds `@image_N`, `@video`) | OUTPUT‑AFFECTING |
| `resolution` | `"720p"` or `"1080p"` | OUTPUT‑AFFECTING |
| `aspect_ratio` | Default `"16:9"` | OUTPUT‑AFFECTING |
| `duration` | 3–15 seconds | OUTPUT‑AFFECTING |
| `enable_audio` | Boolean | OUTPUT‑AFFECTING |
| `images` | Array of image URLs (up to 12, or 4 with video) | OUTPUT‑AFFECTING (VOLATILE) |
| `video` | Single video URL | OUTPUT‑AFFECTING (VOLATILE) |
| `keep_original_audio` | Boolean (when video present) | OUTPUT‑AFFECTING |
| `multi_shots` | Array of `{prompt, duration}` dicts | OUTPUT‑AFFECTING |

---

## 11. Seedance 1.5 (Direct Volcano Engine API)

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/video/main.py#L532-L633)  
> **Endpoint**: `POST /worker/animate-seedance`  
> **API call**: `POST {SEEDANCE_URL}`

| Parameter | Sent to API | Category |
|---|---|---|
| `model` | `MODEL_VIDEO` env var (default `"seedance-1-5-pro-251215"`) | OUTPUT‑AFFECTING |
| `content[0].text` | `"{prompt} --duration {duration} --camerafixed false --audio {audio_flag}"` | OUTPUT‑AFFECTING |
| `content[1].image_url.url` | `image_url` from payload | OUTPUT‑AFFECTING (VOLATILE) |
| `prompt` (embedded) | From payload | OUTPUT‑AFFECTING |
| `duration` (embedded) | Default `"5"` | OUTPUT‑AFFECTING |
| `audio` (embedded flag) | `"true"` / `"false"` from `sound` | OUTPUT‑AFFECTING |
| `camerafixed` | Always `false` | OUTPUT‑AFFECTING (constant) |

---

## 12. Seedance 2.0 (via PiAPI)

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/video/main.py#L637-L1182)  
> **Endpoint**: `POST /worker/piapi-seedance2`  
> **API call**: `POST {PIAPI_BASE_URL}/task`

| Parameter | Sent to PiAPI | Category |
|---|---|---|
| `model` | Always `"seedance"` | ROUTING |
| `task_type` | Computed: `"seedance-2"`, `"seedance-2-fast"`, `"seedance-2-preview"`, `"seedance-2-fast-preview"`, plus `-vip` suffix | OUTPUT‑AFFECTING |
| `prompt` | From payload (with auto-injected @imageN, @videoN, @audioN tags) | OUTPUT‑AFFECTING |
| `mode` | `"omni_reference"` / `"first_last_frames"` / `"text_to_video"` | OUTPUT‑AFFECTING |
| `duration` | 4–15 (official) or snapped to 5/10/15 (preview) | OUTPUT‑AFFECTING |
| `aspect_ratio` | Default `"16:9"` | OUTPUT‑AFFECTING |
| `resolution` | `"480p"`, `"720p"`, or `"1080p"` | OUTPUT‑AFFECTING |
| `image_urls` | Array of image URLs (max 9) | OUTPUT‑AFFECTING (VOLATILE) |
| `video_urls` | Array of video URLs (max 12 official, 3 preview) | OUTPUT‑AFFECTING (VOLATILE) |
| `audio_urls` | Array of audio URLs (max 3 preview) | OUTPUT‑AFFECTING (VOLATILE) |
| `parent_task_id` | For video extension mode | OUTPUT‑AFFECTING |
| `quality` | `"fast"` or `"pro"` | OUTPUT‑AFFECTING (selects task_type) |
| `model_version` | `"official"` or `"preview"` | OUTPUT‑AFFECTING (selects task_type + schema) |
| `end_frame_url` | Added to `image_urls` array | OUTPUT‑AFFECTING (VOLATILE) |

---

## 13. Seedance 2.0 — Burst Set 360°

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/video/main.py#L1256-L1486)  
> **Endpoint**: `POST /worker/burst-set-360`

| Parameter | Sent to PiAPI | Category |
|---|---|---|
| `prompt` | Always `BURST_360_PROMPT` (hardcoded Chinese 360° pan instruction) | OUTPUT‑AFFECTING (constant) |
| `mode` | Always `"omni_reference"` | OUTPUT‑AFFECTING (constant) |
| `image_urls` | `[anchor_image_url]` (single front-wall image) | OUTPUT‑AFFECTING (VOLATILE) |
| `duration` | `burst_duration` (default 4) | OUTPUT‑AFFECTING |
| `aspect_ratio` | Always `"16:9"` | OUTPUT‑AFFECTING (constant) |
| `task_type` | Always `"seedance-2"` (pro quality) | OUTPUT‑AFFECTING |

---

## 14. ElevenLabs — Text-to-Speech (Voiceover)

> **File**: [production.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/production.py#L6744-L6788)  
> **Endpoint**: `POST /generate_voiceover`  
> **API call**: `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`

| Parameter | Sent to API | Category |
|---|---|---|
| `text` | From `VoiceoverRequest.text`, with emotion prefix if non-Neutral | OUTPUT‑AFFECTING |
| `voice_id` | From `VoiceoverRequest.voice_id` (default `"21m00Tcm4TlvDq8ikWAM"`) | OUTPUT‑AFFECTING |
| `model_id` | Always `"eleven_v3"` | OUTPUT‑AFFECTING |
| `emotion` | `VoiceoverRequest.emotion` (default `"Neutral"`) — prepended to text as `[direction]` | OUTPUT‑AFFECTING |

---

## 15. ElevenLabs — Sound Effects (SFX)

> **Files**: [production.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/production.py#L6890-L6930), [postprod.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/postprod.py#L868-L934)  
> **Endpoint**: `POST /generate_sfx`  
> **API call**: `POST https://api.elevenlabs.io/v1/sound-generation`

| Parameter | Sent to API | Category |
|---|---|---|
| `text` | Prompt describing the sound effect | OUTPUT‑AFFECTING |
| `duration_seconds` | Optional, 0.5–22.0 (clamped in postprod) | OUTPUT‑AFFECTING |
| `prompt_influence` | Default `0.3`, range 0.0–1.0 | OUTPUT‑AFFECTING |

---

## 16. ElevenLabs — Background Music (BGM)

> **File**: [postprod.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/postprod.py#L937-L1000)  
> **Endpoint**: `POST /generate_bgm`  
> **API call**: `POST https://api.elevenlabs.io/v1/music`

| Parameter | Sent to API | Category |
|---|---|---|
| `prompt` | Music description | OUTPUT‑AFFECTING |
| `music_length_ms` | `duration_seconds × 1000` (5–300s, clamped) | OUTPUT‑AFFECTING |
| `force_instrumental` | Default `true` | OUTPUT‑AFFECTING |

---

## 17. SyncLabs — Lip Sync

> **File**: [production.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/app/routers/production.py#L6810-L6886), [audio/main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/audio/main.py#L165-L257)  
> **Endpoint**: `POST /lipsync_shot` → Cloud Task → `POST /worker/lipsync`  
> **API call**: `POST https://api.sync.so/v2/generate`

| Parameter | Sent to API | Category |
|---|---|---|
| `model` | `LipSyncRequest.model` (default `"sync-3"`) | OUTPUT‑AFFECTING |
| `input[0].type="video"` + `url` | `video_url` from request | OUTPUT‑AFFECTING (VOLATILE) |
| `input[1].type="audio"` + `url` | `audio_url` from request | OUTPUT‑AFFECTING (VOLATILE) |

---

## 18. Viewport Extraction (Not a generation call — deterministic transform)

> **File**: [main.py](file:///Users/vidyadhar/Desktop/MotionX/MotionX-Studio-Backend/workers/image/main.py#L4253-L4352)  
> **Endpoint**: `POST /worker/extract-viewport`

| Parameter | Category | Notes |
|---|---|---|
| `skybox_url` | OUTPUT‑AFFECTING (VOLATILE) | Source equirectangular image |
| `camera_rx` | OUTPUT‑AFFECTING | Pitch in degrees |
| `camera_ry` | OUTPUT‑AFFECTING | Yaw in degrees |
| `fov` | OUTPUT‑AFFECTING | Horizontal FOV |
| `output_width` | OUTPUT‑AFFECTING | Default 1920 |
| `output_height` | OUTPUT‑AFFECTING | Default 1080 |

> This is a fully deterministic mathematical projection (no AI). Same inputs = same output, always.

---

## Answers to Your Five Questions

### Q1. Deduplicated list of OUTPUT‑AFFECTING parameters

The canonical whitelist for your idempotency key hash, grouped by domain:

**Universal (all providers)**:
- `provider` (which provider/endpoint)
- `model` / `model_name` / `model_id` (specific model version)
- `prompt` / `text` (the assembled text prompt)
- `aspect_ratio`

**Image-specific (Gemini, Seedream, Luma)**:
- `image_size` / `output_resolution`
- `style` / `engine_style`
- `shot_type`
- `reference_image_content` (see Q3 for stable identifier)

**Video-specific (Kling, Seedance, Seedance 2.0)**:
- `duration`
- `mode` (pro/fast/std)
- `sound` / `enable_audio`
- `cfg_scale`
- `negative_prompt`
- `resolution` (480p/720p/1080p)
- `multi_shot` + `shot_type` + `multi_prompt`
- `element_list`
- `voice_list`
- `watermark`
- `image_url` content (start frame)
- `end_frame_url` content
- `video_url` content (for edits)
- `reference_image_urls` content
- `reference_video_urls` content
- `reference_audio_urls` content
- `parent_task_id` (video extension)
- `quality` (fast/pro)
- `model_version` (official/preview)
- `task_type` (seedance-2/seedance-2-fast/etc.)
- `keep_original_audio`

**Blockade Labs**:
- `negative_text`
- `skybox_style_id`
- `enhance_prompt` (always true)
- `control_image` content

**ElevenLabs TTS**:
- `voice_id`
- `emotion`

**ElevenLabs SFX**:
- `duration_seconds`
- `prompt_influence`

**ElevenLabs BGM**:
- `music_length_ms`
- `force_instrumental`

**SyncLabs**:
- `video_url` content
- `audio_url` content

### Q2. Parameters missing from a naive whitelist

> [!CAUTION]
> These are the most likely to be missed:

1. **`model_version`** (Seedance 2.0) — `"official"` vs `"preview"` produces completely different outputs using different PiAPI endpoints
2. **`task_type`** (Seedance 2.0) — the full computed string including `-vip` suffix (e.g. `seedance-2-preview-vip`) routes to different PiAPI models
3. **`quality`** (Seedance 2.0) — `"fast"` vs `"pro"` → different task_type
4. **`resolution`** (Seedance 2.0, Kling Omni) — `480p`/`720p`/`1080p`
5. **`mode`** (Seedance 2.0) — `"omni_reference"` / `"first_last_frames"` / `"text_to_video"` — same prompt with different modes produces different outputs
6. **`element_list`** (Kling v3) — IP character preservation elements; missing from key = collision between element-constrained and unconstrained generations
7. **`voice_list`** (Kling v3) — voice synthesis elements
8. **`multi_shot` + `multi_prompt`** (Kling v3) — multi-segment generation
9. **`keep_original_audio`** (Kling Omni) — affects audio track in output
10. **`cfg_scale`** (Kling) — guidance scale for diffusion
11. **`image_size`** / `output_resolution` (Gemini) — `"2K"` vs `"4K"` produces different pixel output
12. **DB-derived context** (Gemini/Seedream) — moodboard style, wardrobe overrides, scene mood, set design — all fetched from Firestore and baked into the prompt. If the DB changes between two "identical" requests, the output changes.

### Q3. Stable identifiers for reference images

Current problem: GCS URLs contain `firebaseStorageDownloadTokens` which are ephemeral UUIDs.

**Recommendation**: Use the **GCS object path** (the `blob_name`) as the stable identifier. It's:
- Deterministic: `{project_id}/characters/{char_id}_{hex}.png`
- Extractable: Parse the URL path between `/o/` and `?alt=media`, then URL-decode
- Content-stable: The blob is immutable once uploaded

Example extraction:
```
URL:  https://firebasestorage.googleapis.com/v0/b/motionx-studio.firebasestorage.app/o/my-project%2Fcharacters%2Fzane_abc123.png?alt=media&token=<ephemeral-uuid>
Path: my-project/characters/zane_abc123.png  ← hash THIS
```

**Alternative**: Hash the raw image bytes (content-addressable). More robust if the same image is re-uploaded to different paths, but requires downloading images at key-construction time (expensive).

### Q4. Sources of randomness/variation

| Source | Where | Impact |
|---|---|---|
| AI model non-determinism | All providers (Gemini, Seedream, Luma, Kling, Seedance, ElevenLabs, SyncLabs) | Same prompt → different output. This is expected and is WHY you need idempotency keys — to prevent charging twice for the same *intent*. |
| Gemini Vision enhancement | Blockade Labs skybox (line 4089–4102) | `image_url` → Gemini → `enhanced_prompt` is non-deterministic. Hash the *input* (`prompt` + `image_url` blob path), not the enhanced prompt. |
| `uuid.uuid4()` in blob paths | All workers (GCS upload) | Only affects storage location, not generation output. METADATA. |
| Key rotation (`get_nano_banana_client()`) | Gemini image gen | Different API keys may access different model versions/quotas, but the *intended* model is the same. Treat as ROUTING. |
| `stagger_delay` (random 0.5–3s) | Seedance 2.0 (line 983) | Timing only — no output impact. METADATA. |
| `firebaseStorageDownloadTokens` | All GCS URLs | Ephemeral token in URL. VOLATILE — use blob path instead. |

### Q5. Impact of `multi_shot` / `multi_prompt` arrays on Kling/PiAPI

**Kling v3 (direct API)**:
- `multi_shot: true` enables multi-segment generation
- `shot_type` selects the shot transition type
- `multi_prompt` is an array of per-segment prompts
- All three must be in the idempotency key when present. The order of `multi_prompt` matters — it's positional.

**Kling Omni (PiAPI)**:
- `multi_shots` is an array of `{prompt, duration}` dicts (max 6)
- When present, top-level `prompt` and `duration` are *ignored*
- Total duration across shots must be ≤ 15s
- Each shot's prompt + duration is output-affecting
- **For hashing**: serialize the entire `multi_shots` array in its original order (position matters)

**Seedance 2.0 (PiAPI)**:
- Does NOT have a `multi_shot` concept
- Reference media (images, videos, audio) are positional arrays — the order of `image_urls`, `video_urls`, `audio_urls` matters because `@imageN` tags bind by position
- **For hashing**: preserve array order

---

## Summary: Recommended Idempotency Key Composition

```python
key_parts = {
    # ROUTING
    "provider": "gemini" | "seedream" | "luma" | "kling-v2" | "kling-v3-t2v" | "kling-v3-i2v" | "kling-v3-omni" | "seedance-1.5" | "seedance-2" | "blockade-labs" | "elevenlabs-tts" | "elevenlabs-sfx" | "elevenlabs-bgm" | "synclabs-lipsync",
    
    # MODEL (OUTPUT‑AFFECTING)
    "model": <model name/version string>,
    
    # CORE CONTENT (OUTPUT‑AFFECTING)
    "prompt": <final assembled prompt text>,
    "reference_media": [<sorted list of GCS blob paths>],
    
    # GENERATION CONFIG (OUTPUT‑AFFECTING)
    "aspect_ratio": ...,
    "duration": ...,
    "resolution": ...,
    "mode": ...,       # pro/fast/std
    "quality": ...,    # fast/pro (Seedance 2)
    "task_type": ...,  # full computed type (Seedance 2 / Omni)
    "sound": ...,
    "cfg_scale": ...,
    "negative_prompt": ...,
    
    # PROVIDER-SPECIFIC (OUTPUT‑AFFECTING, include only when relevant)
    "multi_shot": ...,
    "multi_prompt": ...,
    "element_list": ...,
    "voice_list": ...,
    "watermark": ...,
    "keep_original_audio": ...,
    "image_size": ...,
    "skybox_style_id": ...,
    "negative_text": ...,
    "voice_id": ...,
    "emotion": ...,
    "duration_seconds": ...,
    "prompt_influence": ...,
    "force_instrumental": ...,
}

idempotency_key = sha256(canonical_json(key_parts))
```

> [!TIP]
> For the `prompt` field in image generation (Gemini/Seedream), the prompt is assembled from many DB-sourced fields. You have two strategies:
> 1. **Hash the final assembled prompt** — simplest, but means DB changes (e.g. editing a character's wardrobe) correctly produce a new key
> 2. **Hash the input fields** (`shot_prompt`, `char_list`, `location_id`, etc.) — faster (no DB fetch needed), but misses DB-side changes
> 
> Strategy 1 is safer for correctness.
