# Design

Current thinking on how this library is put together — what it holds, what it hands back to the
game, and how the join between the two works. This is the plan we intend to build against, not a
settled specification: parts of it will turn out wrong once there is code, and changing them is
expected rather than a problem.

The system being extracted is FCM's `EffectsManagerMixin`, described in FCM's
[design/effects-system.md](../../../design/effects-system.md). Everything below was agreed by
walking that system and deciding, seam by seam, which side of the library boundary each piece
lands on.

## The shape

The library holds **state and lifecycle**. The game holds **everything a state means**.

| The library | The consumer |
|---|---|
| The ref-counted condition store, and the transitions in and out of it | Which conditions exist, and what any of them means to gameplay |
| The named-effect records: apply, anti-stack, remove, reverse | Which effects exist, their text, their payloads |
| The countdown machinery, stepped from outside; the wall-clock timer, driven from inside | What a round, a dance or a day is, and when one has happened |
| Delivering first-person text; one seam for third-person broadcast | Who in the room is allowed to see the broadcast |
| The break and clear verbs | When to call them, and which effects they cover |
| Calling `at_effects_changed()` after every change | What a stat is, and rebuilding stats from the records |

Everything below follows from that split.

## The problems, and how we plan to solve them

### The catalogue, without the library owning it

The library ships two frozen dataclasses — `ConditionSpec` and `EffectSpec` — and two member-less
base enums, `Condition` and `NamedEffect`. The consumer declares one subclass of each, every member
carrying a spec as its value:

```python
class MyConditions(Condition):
    HIDDEN = ConditionSpec("hidden", start_first="You blend into the shadows.", ...)

class MyEffects(NamedEffect):
    STUNNED = EffectSpec("stunned", lifecycle="combat_rounds", ...)
```

The base's `__new__` accepts exactly the spec class and nothing else, so a malformed member fails
at declaration. It sets the member's `_value_` to the spec's `key` string — which is what keeps
`MyEffects("stunned")` resolving, so game code can pass raw strings everywhere and most consumer
modules never import the enum at all.

The enums reach the library as settings naming modules, per
[library-standards.md](../../../design/library-standards.md) § Consumer-authored config:

```python
EFFECTS_CONDITION_ENUM = "world.effects.MyConditions"
EFFECTS_EFFECT_ENUM = "world.effects.MyEffects"
```

Neither has a safe default, so both are checked at boot and the game does not start without them.
Boot also judges each set as a whole — aliased members (Python silently folds two members declaring
the same key into one; boot is the only place that can be seen), field types, and the two
cross-checks: every `EffectSpec.condition` names a declared condition, every lifecycle names a
declared one. Every problem is collected and raised once.

An **empty** consumer enum is allowed — an effects-only game has no conditions to declare, and the
other way round. This diverges from evennia-survival, whose meters are meaningless without stages;
here each half of the system stands alone.

**No cross-enum key-uniqueness check.** The same key in both enums is the legitimate dual-system
case — a named effect managing the lifecycle of a condition flag of the same name — and the break
verb's fallback depends on the names coinciding. The coincidence is a consumer convention the
library cannot enforce; `installing.md` names it.

`EffectSpec.condition` is a **string key**, not an enum member, so the two consumer modules never
need to import each other; membership is checked at boot instead.

### Consumer payload on a spec

Anything game-specific a spec needs to carry — save DCs, block messages, whatever the consumer's
hooks read — goes in the spec's `extras` mapping, stored read-only. `apply_named_effect()` also
takes a per-application `extras=`, merged over the spec's, so values known only at cast time reach
the record. Subclassing the spec dataclasses is not blocked but not supported; `extras` is the one
declared shape.

### Stats, without the library knowing any

An effect's `effects` payload is stored verbatim and never interpreted. After any change that adds
or removes a payload, the library calls one hook on the holder — `at_effects_changed()`, a no-op by
default. The consumer overrides it to rebuild whatever it means by stats, reading `active_effects`
directly. FCM's `_recalculate_stats()` is that override in its game; nothing about it crosses.

The consequence is a contract, not code: **whatever a consumer's hook derives from the records, it
must fully re-derive on every call.** The library guarantees only that the hook fires after the
records change.

**Apply is unwound if the hook raises.** `apply_named_effect()` persists the record and the
condition ref first — the hook has to be able to see them — then calls the hook inside a try. If it
raises, record and ref are rolled back and the exception propagates untouched: a raising override
is the consumer's bug, and the library's job is only to not be left half-applied. Messages, the
timer and `on_apply` all sequence after the hook succeeds.

### Two clocks and a blank, chosen per record

Every effect record is on exactly one lifecycle:

- **A consumer-named countdown** (`"combat_rounds"`, `"fair_dances"`, …). The library holds a
  number and is otherwise passive; the consumer calls `advance_effects(name)` at the point in its
  own code where the event happens. The library decrements every record on that name and removes
  what reaches zero. It never knows what the unit is or whether it is paused. The names are
  declared in `EFFECTS_LIFECYCLES` and checked at boot; `clear_effects(name)` removes everything on
  a name at once, which is how combat-end cleanup generalises.
- **The wall clock** — the one lifecycle the library drives itself, because real time is the one
  unit with no game event to ride on. Applying with the reserved wall-clock lifecycle and a
  duration creates a one-shot persistent script that removes the effect when it fires. No ticking;
  one deferred callback. `get_effect_remaining_seconds()` reads the script's start stamp.
- **Unmanaged** (`lifecycle=None`) — the library holds the record and something outside ends it by
  calling `remove_named_effect()`. DoT scripts are the standing example.

The reserved wall-clock name may not appear in `EFFECTS_LIFECYCLES`, and `advance_effects()` refuses
it — otherwise two clocks would drive one record.

**`duration=None` on a countdown lifecycle means "until cleared"**: nothing counts the record
down and it falls to `clear_effects()`. This is the stance semantic — an effect that belongs to
combat but does not expire on its own.

**The tick.** A spec may carry an `on_tick(target, record) -> bool`, called once per record on every
countdown step, before any decrement. What a tick *does* is entirely the consumer's — damage, a save
roll, a message, any combination — decided inside their callable from what it reads in `extras`. The
library reads only the return: truthy ends the effect immediately, at its full remaining duration;
falsy leaves the normal decrement.

It runs for every record on the lifecycle, `duration=None` included — only the decrement is skipped
for those. A permanent is a record nothing wears down, not one nothing happens to, and a truthy
return still ends it, so "permanent until you escape it" is expressible without standing a large
number in for infinity.

### Messages, without the library filtering them

Specs carry four message fields: start and end, each in first and third person. Two rules:

- **A missing field falls back to a generated generic; an empty string is deliberately silent.**
  The two are different statements and both are needed.
- **First person the library delivers itself** (`self.msg`) — there is no filtering question in
  telling an actor about their own state. **Third person goes through one overridable method**,
  `effects_broadcast(template)`, whose default is a naive broadcast to the holder's location. A
  game with concealment overrides that one method with its own visibility filtering; the library
  never learns the game has concealment. The template reaches the override unformatted (`{name}`
  intact) so a game can render the name per observer.

`apply_named_effect()` also accepts a per-application `messages=` override — some text is built
from runtime values and cannot live on a spec.

### Ending things early

- `remove_named_effect(key)` — the symmetric reversal, with end messages. The public way anything
  external ends an effect.
- `break_effect(key)` — force-removal for break-on-action effects: **zeros** the condition's ref
  count (it does not decrement), drops the record, stops the timer, fires the hook, sends **no**
  messages — the caller knows what just happened and says so itself.
- `break_effects(keys, excluded=()) -> list` — the plural, for "this action ends these". Per key:
  skipped if excluded or inactive; broken via `break_effect`, falling back to a plain
  `remove_condition` where the key is only a bare condition. Returns what actually broke, in
  order, so callers drive messaging and consequences off the result. Which keys an action ends is
  game policy — the caller supplies the set, and the library has no concept of a hostile action.
- `clear_effects(lifecycle)` — everything on one lifecycle, with messages.
- `clear_all_effects()` — every record, silently, for death-shaped moments. Bare conditions —
  refs not contributed by a record — are untouched. Spec-declared companion scripts
  (`companion_script_key`) are stopped here, and only here: companion scripts end their own effect
  from inside their own tick, and stopping them from remove or break risks a script deleting
  itself mid-call.

### Side effects on the spec, not in the library

Three optional callables per `EffectSpec`, replacing the extracted system's hardcodes and
registries: `on_apply(target, source, duration)` after a successful apply, `on_remove(target,
record)` after a removal, and `on_tick` above. What they do is entirely the consumer's; the
library only guarantees when they fire.

## The record

```python
active_effects = {
    "shield": {
        "condition": "some_condition" or None,   # key string
        "effects": [...],                        # opaque payload, never read
        "duration": int or None,
        "lifecycle": "combat_rounds" | <wall-clock> | None,
        "messages": {...},                       # resolved at apply: spec + overrides
        "extras": {...},                         # spec.extras + per-application extras
    },
}
```

Against the extracted system: `duration_type` is now `lifecycle`, and the `save_*` fields are gone —
their content rides in `extras`, read by the consumer's tick hook.

## Stated limits

- **No condition reconciliation.** Conditions are an incremental counter with no rebuild path — a
  ref leaked by a crashed script stays leaked. Stats self-heal on every `at_effects_changed()`;
  conditions do not. Known, inherited, accepted.
- **Break zeroes.** A condition granted by three sources and broken once is gone entirely. That is
  the semantic of *break* — concealment ends, whoever granted it — not a bug.
- **The `.db` bypass.** Attributes the library validates are set by assignment; a consumer writing
  through `.db` gets whatever they set.

## Out of scope

- **Interpreting effect payloads.** No stat names, no bonus arithmetic, no damage types.
- **Convenience wrappers** (`apply_stunned(…)`-style). Sugar over `apply_named_effect()` is the
  consumer's four lines per effect.
- **Policy sets** — what breaks on a hostile action, what incapacitates, what blocks movement.
  Tuples in the consumer's repo, passed in or checked with the query API.
- **Companion scripts themselves.** DoT ticking, their damage, their timing all stay consumer-side;
  the spec only names the script key so `clear_all_effects()` can stop it.
- **Tables.** All state is Attributes on the holder; no models, no alias, no `db_spec.py`.

## What is still open

Open questions live in [test-plan.md](test-plan.md) § Open decisions, so they are picked up where
behaviour is agreed.
