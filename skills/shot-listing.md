# Shot listing

Breaking a scene into shots. Read `scene-context.md` first — the six department
answers are what fill each shot's atmosphere.

Before starting, read the scene node, the characters in it from the bible, the
location, and any set design or wardrobe attached to the scene. If the location
has generated views, look at which angles exist. Composing shots for a space you
can see produces better coverage than composing for a slugline, which is why
building the set first is usually worth it — though a director who already knows
the room can skip it.

---

## Build atmosphere before faces

**Shot 1 is the space, not a person.** A wide or establishing frame showing the
full location, with characters absent or as small silhouettes. The audience
needs to know where they are before they are asked to care what happens there.

**Shot 2 is usually a detail.** A texture, an object, an atmospheric element.
This is what gives a scene weight rather than urgency.

Faces and dialogue start from shot 3. Cutting to a close-up in the first frame
of a scene is a music-video instinct; it burns the location and leaves the
audience spatially lost.

Think Fincher or Villeneuve rather than a trailer. Do not rush.

## Every cut needs a shot

This is a shot division, not a storyboard. You are not selecting the memorable
moments — you are providing a frame for every edit point.

Between any two significant actions there is: the action, the reaction, an
insert of whatever object is involved, and the transitional beat that gets from
one to the other. If a character crosses a room, that is the start, the
crossing, and the arrival — not just the arrival.

Sit at the timeline. Every three to ten seconds is a new shot. A scene that
should run 45 seconds and produces four shots has skipped the connective tissue,
and it will cut like a slideshow.

## Objects get their own frame

If the screenplay names an object — a cigarette, a phone, a glass, a weapon —
give it an extreme close-up before or during the interaction with it.

The insert is how an object becomes significant. A gun that only appears in wide
shots is set dressing. A gun that gets a macro on the trigger guard is a threat.

## Eye-lines and the 180-degree rule

When two characters interact, know where each is looking. Cross the line and the
audience loses which way people face; the scene stops being a conversation and
becomes two monologues.

State positions explicitly — who is standing, who is sitting, what furniture
they are near. Without this, consecutive shots will place the same character in
physically impossible relationships to the room.

## Lens variety

Use real terminology, because it carries framing, compression, and distance in
one phrase: *Tight 85mm on eyes*, *Low-angle wide 24mm*, *Macro 100mm*,
*Over-the-shoulder*, *Medium 50mm*.

Vary it. Ten shots at the same focal length is not coverage, it is repetition.
Wide for geography, medium for relationship, long lens for isolation and
compression, macro for significance.

## Beats, not just lines

The interesting frame is often not the line — it is the micro-expression before
it, or the reaction three seconds after. A shot list built only around dialogue
misses where the scene actually turns.

## Coverage follows subtext

When two shots are both technically correct, choose the one that serves the
power dynamic. Tightening on someone losing control, staying on the listener
during a lie, giving air to whoever holds the room. This is the difference
between covering a scene and directing it.

---

## What each shot needs

- **`visual_action`** — what the camera sees, written as a cinematographer's
  description. This is the text the image is generated from, so it is the most
  important field on the shot. Describe the frame: subject, position, what is
  behind them, the quality of light, the texture. Name characters by name and
  describe their appearance from their bible traits. Everything below supports
  this field; none of it replaces it.
- **`shot_type`** — the lens and framing, in professional terms.
- **`camera_direction`** — where the camera physically is and what it faces.
  "Camera low near the centre of the room, looking toward the far doors."
- **`ambient_scene`** — the environmental state: light quality, atmosphere,
  mood. This comes straight from the six department answers. If it reads
  generically, the department pass was skipped.
- **`continuity_note`** — how this shot connects to the previous one, and where
  everyone and everything is standing. Both halves matter; the edit connection
  without the positions is not enough to keep the space coherent.
- **`characters`** — only who is visible in this frame. An ECU holds one person.
  An over-the-shoulder holds two. A wide may hold none.
- **`products`** — only what is actually in this frame, not everything in the
  scene.
- **`estimated_duration`** — how long this take runs. The shot durations should
  sum to roughly the scene's estimated duration; if they don't, either the
  coverage or the estimate is wrong.

Each shot is one continuous take from one camera position. If a shot needs the
camera to be in two places, or contains more than a couple of distinct actions,
it is two shots.

## Location angles

If the location has generated views, each shot should name which one it is
shooting against — the wall or background visible behind the subject. Choose
from what actually exists; a shot composed against a wall with no reference will
be generated blind and will not match the rest of the scene.

Vary the angles. A scene shot entirely against one wall feels like a stage set.
Three or more different backgrounds across a scene of any length reads as a real
room.

## Stay inside the screenplay

Every shot maps to a beat, action line, or dialogue exchange that is actually in
the scene. Do not invent dialogue and do not invent action. Coverage is a
reading of the scene, not an extension of it.

---

## Reviewing your own list

Before finishing, read the list back as an edit and cut what fails:

- **Redundant** — two shots at similar angle and content. Keep the stronger.
- **Spatially impossible** — a position that contradicts an earlier shot or the
  set layout.
- **Low value** — a shot that neither advances the scene nor builds atmosphere.
- **Underspecified** — generic lighting or atmosphere, a character with no
  wardrobe, a frame that could belong to any scene in any film. Fix rather than
  cut: the department answers already hold what is missing.

Then check the whole against the scene: does the light match the `time` field
throughout, does the grade match the moodboard, does every named character
resolve to someone in the bible.
