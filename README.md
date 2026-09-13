# evennia-effects-conditions

Conditions and timed effects for Evennia — the states an actor can be in, the things that put them
there, and the clock that takes them away again.

## Status

**Core built, not yet proven in a live game.** The catalogue declaration, the boot check, both
mixins, the lifecycle machinery and the break/clear verbs exist, covered by the cases in
[docs/test-plan.md](https://github.com/FullCircleMUD/evennia-effects-conditions/blob/main/docs/test-plan.md).
See [docs/progress.md](https://github.com/FullCircleMUD/evennia-effects-conditions/blob/main/docs/progress.md).

## The problem it solves

Every combat MUD grows the same pile. A stun that lasts two rounds. A shield that adds armour for
thirty seconds. A poison that ticks. Darkvision from a race, and darkvision from a spell, and only
one of them going away when the spell does. Each is added where it was needed — a script here, a
flag there, a number written straight onto a stat — and none of them knows about the others.

What that costs shows up later, not at the time:

- **Two sources of the same state fight over one flag.** The spell ends, the flag clears, and the
  racial trait it was also standing for goes with it.
- **The same buff applied twice doubles.** Nothing says whether it should.
- **Removal is written separately from application**, so the two drift, and a stat ends up a few
  points off with nothing to say when it happened.
- **Every new effect is a new decision** about where to store it, how to time it, and what removes
  it — decided again each time, by whoever is writing that feature.

The mechanism underneath all of it is the same regardless of game: something is true of an actor for
a while, more than one thing can make it true, and it has to come off cleanly.

## The shape

The library holds the machinery — ref-counted condition flags, tracked anti-stacking effect
records, countdown lifecycles you step from your own events, one library-driven wall clock, break
and clear verbs. Your game declares the catalogue (two enums of frozen specs, named in settings and
validated at boot) and answers two hooks: `at_effects_changed()` rebuilds whatever you mean by
stats, and `effects_broadcast()` filters third-person messages if your game has concealment. The
library never learns what a stat, a round or invisibility is.

```python
class MyEffects(NamedEffect):
    STUNNED = EffectSpec("stunned", lifecycle="combat_rounds")

target.apply_named_effect("stunned", duration=2)
target.advance_effects("combat_rounds")   # wherever a round happens in your game
```

## Is this for you?

Probably, if your game has buffs, debuffs or status flags and you would rather configure the
lifecycle than rewrite it per effect. Not for you if you want the library to ship effects — it
deliberately ships none.

## Install

**What a game declares is in
[docs/installing.md](https://github.com/FullCircleMUD/evennia-effects-conditions/blob/main/docs/installing.md).**

Nothing is published yet. Editable install for development against a checkout:

```
git clone https://github.com/FullCircleMUD/evennia-effects-conditions.git
cd evennia-effects-conditions
python -m venv venv
# Activate the venv (platform-specific)
pip install evennia
pip install -e path/to/evennia-logging-extension
pip install -e .
python runtests.py
```

## Learn more

- [docs/INDEX.md](https://github.com/FullCircleMUD/evennia-effects-conditions/blob/main/docs/INDEX.md) — the design wiki
- [docs/test-plan.md](https://github.com/FullCircleMUD/evennia-effects-conditions/blob/main/docs/test-plan.md) — every case the library commits to covering, and what is still open
- [docs/installing.md](https://github.com/FullCircleMUD/evennia-effects-conditions/blob/main/docs/installing.md) — what a consumer declares
- [docs/interoperability.md](https://github.com/FullCircleMUD/evennia-effects-conditions/blob/main/docs/interoperability.md) — this library against its siblings
- [CLAUDE.md](https://github.com/FullCircleMUD/evennia-effects-conditions/blob/main/CLAUDE.md) — context for LLM agents working in this repo

## Licence

BSD 3-Clause. See [LICENSE](https://github.com/FullCircleMUD/evennia-effects-conditions/blob/main/LICENSE).
