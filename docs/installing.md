# Installing

What a game has to do to run this library. Written as each requirement was decided rather than
reconstructed afterwards, so it describes what exists. Everything in the numbered steps is either
enforced at boot or listed under *What is not checked for you*.

## 1. Install the logging extension

`evennia-logging-extension` is a hard dependency and is not published, so it installs from its own
checkout first:

```
pip install -e path/to/evennia-logging-extension
```

## 2. Install the package

Also unpublished, so also from a checkout:

```
pip install -e path/to/evennia-effects-conditions
```

## 3. Add the app

In your settings, **below** `from evennia.settings_default import *`:

```python
INSTALLED_APPS += ["evennia_effects_conditions"]
```

## 4. Declare your catalogue

One module of your own, anywhere in your gamedir you like, declaring what conditions and effects
your game has. Subclass the library's bases; every member's value is a spec:

```python
# world/effects.py
from evennia_effects_conditions.config import WALL_CLOCK
from evennia_effects_conditions.specs import (
    Condition, ConditionSpec, EffectSpec, NamedEffect,
)


class MyConditions(Condition):
    HIDDEN = ConditionSpec(
        "hidden",
        start_first="You blend into the shadows.",
        start_third="{name} melts into the shadows.",
        end_first="You step out of the shadows.",
        end_third="{name} steps out of the shadows.",
    )


class MyEffects(NamedEffect):
    STUNNED = EffectSpec("stunned", lifecycle="combat_rounds")
    INVISIBLE = EffectSpec("invisible", condition="hidden", lifecycle=WALL_CLOCK)
```

A message field left out falls back to a generated generic; an empty string is deliberately
silent. `EffectSpec` also carries `on_apply` / `on_remove` / `on_tick` callables,
`companion_script_key`, and an `extras` mapping for anything game-specific your hooks read.

## 5. Point the settings at it

```python
EFFECTS_CONDITION_ENUM = "world.effects.MyConditions"
EFFECTS_EFFECT_ENUM = "world.effects.MyEffects"
EFFECTS_LIFECYCLES = ("combat_rounds",)
```

Both enum settings are required — the game does not start without them, and boot validates the
whole catalogue with every problem in one refusal. `EFFECTS_LIFECYCLES` declares the countdown
lifecycles your game will step; omit it entirely if you use only the wall clock.

## 6. Mix it into your typeclasses

```python
from evennia import DefaultCharacter
from evennia_effects_conditions.mixins import EffectsMixin


class Character(EffectsMixin, DefaultCharacter):
    ...
```

`EffectsMixin` carries the full system, conditions included. A typeclass that only needs the
ref-counted flags can mix in `ConditionsMixin` alone.

## 7. Answer the hooks

Three override points, all optional to start with:

```python
class Character(EffectsMixin, DefaultCharacter):

    def at_effects_changed(self):
        """Rebuild whatever your game means by stats, from scratch."""
        # read self.active_effects, re-derive everything it feeds

    def at_conditions_changed(self, condition, is_held):
        """React to something becoming true of this character, or ceasing to be."""
        # condition is the key; is_held is True on arrival, False on departure

    def effects_broadcast(self, template):
        """Filter third-person effect messages, if your game has concealment."""
        # the template arrives with {name} unformatted
```

All three default to doing nothing, so a game takes only the ones it needs. The default broadcast
sends to the holder's room, unfiltered.

**The first two answer different questions, and the difference matters.**

`at_effects_changed()` means *this holder's derived stats are now wrong*. It fires only when the
effect applied or removed carried a stat payload, because an effect that changes no number leaves
every derived value correct. A game with no stats never needs it.

`at_conditions_changed()` means *the set of things true of this holder has changed*. It fires on a
condition's 0→1 and →0 transitions however they happened — on an effect, on a bare `add_condition()`,
on a break, on a full strip — and regardless of any payload.

So a flight buff, a water-breathing potion or a darkvision spell fires the **second** and not the
first: each grants a condition and changes no number. If your game reacts to a condition arriving or
leaving — refusing something, starting a timer, moving the holder — that reaction belongs on
`at_conditions_changed()`. Reaching for `at_effects_changed()` will work for every effect that
happens to carry a payload and silently miss the ones that do not.

An effect can fire both, either, or neither.

**Transitions only.** A condition held by two sources and released by one is still held, and nothing
is announced for it. You are told when something becomes true and when it stops, never about the
counting in between.

## 8. Drive your lifecycles

Wherever your game's own event happens, step the lifecycle named for it:

```python
ended = character.advance_effects("combat_rounds")   # each combat round
character.clear_effects("combat_rounds")             # when combat ends
```

The wall clock needs no driving — applying with it and a duration sets its own one-shot timer.

Applying an effect that is already active returns False and changes nothing, unless the caller says
otherwise:

```python
character.apply_named_effect(effect, duration=60, on_active="reset")    # back to a full 60
character.apply_named_effect(effect, duration=60, on_active="extend",   # add 60 to what is left,
                             max_duration=180)                          # never past 180
```

Neither delivers start messages or fires `on_apply` — the effect never stopped, so it never
started again.

## Required settings

| Setting | What it does | Without it |
|---|---|---|
| `EFFECTS_CONDITION_ENUM` | Dotted path to your `Condition` subclass | Boot is refused |
| `EFFECTS_EFFECT_ENUM` | Dotted path to your `NamedEffect` subclass | Boot is refused |

## Optional settings

| Setting | What it does | Default |
|---|---|---|
| `EFFECTS_LIFECYCLES` | The countdown lifecycle names your game steps | `()` — wall clock only |

## What is not checked for you

- **That the library is in `INSTALLED_APPS`.** Leave it out and `AppConfig.ready()` never runs, so
  nothing validates anything — the mixins then fail at first use instead of at boot.
- **That a library import in your settings file sits below `from evennia.settings_default import *`.**
  `LOG_DIR` is set by that import, and a library imported above it is refused at boot.
- **The dual-namespace key convention.** `break_effects()` falls back from the effect route to the
  bare-condition route by *key coincidence* — a condition managed by a named effect only breaks as
  one thing if both carry the same key (FCM's `slowed` shape). Nothing can check that you meant
  the names to line up.
- **That your `at_effects_changed()` re-derives fully.** The hook's contract is rebuild-from-
  scratch on every call. An override that increments instead will drift, and nothing reports it.
- **The `.db` bypass.** The library's stores are `AttributeProperty`s set by assignment. Writing
  them through `.db`/`attributes.add()` skips whatever the descriptor does; you get exactly what
  you set.
- **Condition ref leaks.** Conditions are an incremental counter with no rebuild path — see
  [design.md](design.md) § Stated limits. A crashed script that never released its grant leaves
  the flag set.

## Watching it

`effects-conditions.log`, beside `server.log` in your `LOG_DIR`. Today the library logs one kind
of line: the boot refusal, at ERROR, carrying the same text as the raised exception.

## That is all of it

Declare the catalogue, point two settings at it, mix in, answer the hooks you need, and step your
lifecycles where your events happen.
