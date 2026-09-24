# Progress

Running log of milestones with links to evidence. Reverse chronological — newest first.

## 2026-09-24 — a second consumer seam for conditions

115 tests, all passing. `CN-12` to `CN-18` added `at_conditions_changed(condition, is_held)`, a no-op
override point that fires on a condition's 0→1 and →0 transitions.

It exists because `at_effects_changed()` could not answer the question. That hook fires only when the
effect applied or removed carried a stat payload — right for a stat rebuild, and silent for every
effect whose whole purpose is a condition. FCM found it from the other end: a room type needed to know
when flight lapsed, and a flight buff carries no payload, so nothing ever told it.

- Both ref-count helpers announce their own transition, so `apply_named_effect`,
  `remove_named_effect`, `clear_all_effects` and the public `add_condition` / `remove_condition` are
  covered by one edit each.
- `break_effect()` zeroed a condition by hand, bypassing the helper and its announcement. Now routed
  through it, looping to zero — same end state, one transition emitted. `CN-15` is that case, and
  every `BK` case still passes.
- `CN-17` is the case the seam exists for: the hook fires whether or not a payload was carried.

## 2026-09-13 — the core built, surface by surface

88 tests, all passing. 79 new cases across seven surfaces, `SP-01` to `CL-05`, each surface agreed
in the plan, written red, then implemented — see the per-unit commits.

- **SP** — the declaration surface: frozen specs as enum member values, string-key lookup, wrong
  spec class and duplicate keys refused at the `class` statement.
- **CF** — `config.py` + `apps.py`: the three settings, every problem in one logged, cause-chained
  refusal; the refusal read back from the log file, never mocked.
- **CN** — the ref-counted conditions mixin with transition-only messaging and the
  `effects_broadcast` seam. Undeclared keys refused (recorded divergence from FCM).
- **EF** — the effects core: anti-stacking, spec auto-fill, merge semantics for messages/extras,
  and the unwind-on-raise guarantee around `at_effects_changed()`.
- **LC** — consumer-named countdowns stepped by `advance_effects()`, `clear_effects()` for
  combat-end shapes, and the wall-clock timer script.
- **BK/CL** — the break verbs (silent, zeroing, condition-first, policy set caller-supplied) and
  the silent full strip that spares bare condition grants.
- Docs brought up to the built state: installing.md carries the full consumer story;
  interoperability's archive/scaling sections now answer the settled lifecycle question (records
  travel as Attributes, timer scripts do not).

**Validated live** in `examples/demo`, wired as a real consumer (own catalogue in
`world/effects.py`, the three settings, `EffectsMixin` on Character):

- A 6-second wall-clock blessing arrived with its start message, reported ~4.5s remaining when
  queried mid-count, expired **on its own timer** with the end message, and dropped its condition.
- A 2-round stun survived one `advance_effects("combat_rounds")` and expired on the second,
  returning `["stunned"]`.
- `EFFECTS_CONDITION_ENUM` pointed at a class that does not exist refused the boot naming the
  setting and the path, with the same text at ERROR in `server/logs/effects-conditions.log`;
  restored, the game booted again.

One Evennia launcher gotcha found on the way (not a library issue): a fresh database with no TTY
sends `check_database()` into infinite recursion at superuser creation — the workaround is in
`examples/README.md`.

## 2026-09-13 — architecture agreed

The design conversation happened against FCM's working system, seam by seam, and the result is
recorded in [design.md](design.md). 1 test, passing (`SC-01`); no behaviour cases yet — they land
surface by surface.

- **The split**: the library holds state and lifecycle; the game holds everything a state means.
- **The catalogue is consumer-declared** — frozen specs as enum member values, two settings naming
  the modules, boot validating the whole set with every problem collected into one raise.
- **Lifecycles**: consumer-named countdowns stepped by `advance_effects(name)`, one library-driven
  wall clock, and unmanaged records for external scripts.
- **Hooks over knowledge**: `at_effects_changed()` for stats, `effects_broadcast()` for
  third-person delivery, spec callables for side effects and ticks. The library never learns
  what a stat, a round, or concealment is.
- Out-of-scope rulings recorded in [../CLAUDE.md](../CLAUDE.md); two open decisions carried in
  [test-plan.md](test-plan.md) § Open decisions.

## 2026-09-13 — repo scaffolded

The structure exists and nothing else. One smoke test (`SC-01`) proving the package imports and the
runner works; no library behaviour.

- Repo cloned into `libraries/evennia-effects-conditions/`, with `LICENSE` and `.gitignore` already in
  place from the GitHub initial commit.
- The standard surfaces: `README.md`, `CLAUDE.md`, `docs/INDEX.md`, `docs/installing.md`,
  `docs/test-plan.md`, `docs/interoperability.md`, `docs/archive/`.
- `pyproject.toml` declaring Evennia and `evennia-logging-extension`.
- `log.py` binding `effects_conditions_log` to `effects-conditions.log`. Nothing calls it yet, so the
  file does not appear.
- `runtests.py`, `tests/test_settings.py` and `tests/urls.py`, adapted from `evennia-environment`.
- `examples/` with its own venv, a `requirements.txt` installing Evennia, `sqlean.py` on macOS and
  both local checkouts editable, and a stock `demo/` gamedir. Its settings carry the macOS SQLite
  swap directly under the Evennia import, and install the app. Never started — there is nothing to
  exercise.

No `config.py` and no `apps.py`. Both exist to check settings, and no setting is agreed yet.

**The design is not started.** No behaviour has been discussed, so [test-plan.md](test-plan.md)
carries only the scaffold case. FCM's
[design/effects-system.md](../../../design/effects-system.md) is the source material and is not a
specification for this library.
