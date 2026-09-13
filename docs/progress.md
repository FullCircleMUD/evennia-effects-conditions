# Progress

Running log of milestones with links to evidence. Reverse chronological — newest first.

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
  third-person delivery, spec callables for side effects and escapes. The library never learns
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
