# CLAUDE.md

> **Project-wide working rules and cross-repo context live in the FCM umbrella repo's `CLAUDE.md`**,
> loaded automatically when you work from the umbrella root. If you opened this repo directly instead
> of via the umbrella, relaunch from the umbrella root for the full context. This file holds only this
> repo's specific instructions.

Instructions for Claude (and other LLM agents) working in this repository.

## What this project is

`evennia-effects-conditions` gives [Evennia](https://www.evennia.com/) actors the states they can be
in and the lifecycle that manages them — something is true of an actor for a while, more than one
thing can make it true, and it has to come off cleanly. Tagline: **"Conditions and timed effects for
Evennia."**

FullCircleMUD is the intended first consumer and has a working version of this, described in its
[design/effects-system.md](../../design/effects-system.md). Nothing has been taken from it.

For the big-picture overview, read [README.md](README.md).
For the design wiki, read [docs/INDEX.md](docs/INDEX.md).

## Project status

**Architecture agreed, build in progress.** The design — what the library holds, what the consumer
declares, the lifecycle model, the hooks — is recorded in [docs/design.md](docs/design.md). Cases
land in [docs/test-plan.md](docs/test-plan.md) surface by surface as each is built. See
[docs/progress.md](docs/progress.md) for what exists.

## Where to read first

1. [docs/test-plan.md](docs/test-plan.md) — the cases the library commits to, and § Open decisions.
   **A behavioural change starts here**, not in the code. **Start here.**
2. [docs/design.md](docs/design.md) — the agreed shape: the library/consumer split, the catalogue,
   the lifecycles, the hooks, the stated limits.
3. [README.md](README.md) — what the library is and its status.
4. [docs/INDEX.md](docs/INDEX.md) — map of all design docs.
5. [docs/installing.md](docs/installing.md) — what a consumer declares.
6. [docs/interoperability.md](docs/interoperability.md) — this library against its siblings.

**FCM's [design/effects-system.md](../../design/effects-system.md) describes the system being
extracted, not this library.** Read it for how the mechanism behaves today. It is not a specification
for what belongs here — it names spells, combat rounds, damage types, saving throws, hit points and
several dozen FCM effect names, and most of that stays in FCM.

## Load-bearing architectural principles

Every implementation decision must respect them.

1. **The library does not own game concepts.** Hit points, spells, combat, saving throws, damage
   types, stats and what any particular effect *means* belong to the consumer game. Where exactly the
   line falls is the first thing to settle, and it is settled from this side of it.

2. **No FCM-specific assumptions.** FCM is the first consumer. Its effect names, its condition list,
   its combat round, its stat names and its typeclass names all stay in FCM. Default to "consumer
   concern" when uncertain.

3. **Test-first.** A case lands in [docs/test-plan.md](docs/test-plan.md), then the test, then the
   code. See [test-first-process.md](../../design/test-first-process.md) for the process and the
   rationale.

Further principles land here as the design is agreed. Three is what the standard requires of every
library and is not a claim that the design is settled.

## Out of scope

Rulings so far, each with its reasoning in [docs/design.md](docs/design.md) § Out of scope:

- **Interpreting effect payloads.** What any effect *means* is the consumer's. `bucket_effects()`
  reads one key — `type` — to sort payloads into buckets, and nothing else; sorting by a key is not
  interpreting, and the function behaves identically if every type string is a random UUID. Acting on
  a payload stays with the consumer's `at_effects_changed()` override.
- **Convenience wrappers** (`apply_stunned(…)`-style) — consumer sugar over `apply_named_effect()`.
- **Policy sets** — what a hostile action breaks, what incapacitates, what blocks movement.
- **Companion scripts** — DoT ticking and timing; the spec only names the script key for cleanup.
- **Tables.** All state is Attributes on the holder; no models, no alias, no `db_spec.py`.

Record further rulings here as they are made, with the reasoning, so they are not reopened by the
next session.

## Working conventions

- **Behavioural change starts in the test plan.** Add the case, write the test, then implement. Fill
  the **Test function** column when the test exists — it is a coverage claim and the linter checks it
  both ways.
- **Editing design docs.** Update or add design documents whenever an architectural decision is made
  or refined. Capture the *why*, not just the *what*. Index new docs in [docs/INDEX.md](docs/INDEX.md).
- **Don't put implementation detail in this file or README.** Link out to `docs/` instead. Keep
  `CLAUDE.md` and `README.md` stable; let `docs/` churn.
- **License.** BSD 3-Clause. Source files carry an SPDX header on the first line
  (`# SPDX-License-Identifier: BSD-3-Clause`).

## Documentation discipline (load-bearing)

Design documents in `docs/` must reflect decisions **actually discussed and agreed on with the project
owner**. They are not a place to forward-design the system from first principles or extrapolate
"reasonable defaults" from a starting point.

**Rules:**

1. **Only capture what was discussed and agreed.** If the conversation establishes a principle, do not
   extrapolate it into specifics that were not raised — condition names, effect keys, duration units,
   API shapes, setting names.
2. **Flag open questions explicitly.** Write `[TBD — needs discussion: <what is open>]` so a future
   session picks the topic up deliberately rather than inheriting an unagreed assumption.
3. **Smaller is better.** Three discussed points captured faithfully beat three discussed points plus
   seven invented ones. Resist filling out sections "for completeness".

**The tempting source of unasked-for answers is FCM's own implementation.** `design/effects-system.md`
has a working shape for every question this library will face — three layers, a registry, a sentinel,
a convenience method per effect, on-apply callbacks — all ready to be lifted. A shape lifted from it
is an invention unless it has been discussed here. The extraction is a design exercise, not a copy.

## Repository layout

```
evennia-effects-conditions/
├── CLAUDE.md                          # this file
├── README.md
├── LICENSE                            # BSD 3-Clause
├── pyproject.toml
├── runtests.py                        # standalone test runner; no gamedir required
├── .gitignore
├── examples/                          # a real Evennia gamedir, for proving it outside the suite
│   ├── requirements.txt               # evennia, sqlean on macOS, both local installs editable
│   ├── README.md                      # setup, and what the settings file carries
│   └── demo/                          # stock gamedir with the app installed; venv/ beside it
├── docs/                              # design wiki (humans + LLMs)
│   ├── INDEX.md
│   ├── installing.md
│   ├── progress.md
│   ├── test-plan.md
│   ├── interoperability.md
│   └── archive/                       # historical context, not authoritative
├── src/
│   └── evennia_effects_conditions/    # library code (src layout)
│       ├── __init__.py                # version + lazy public re-exports
│       ├── specs.py                   # ConditionSpec/EffectSpec + the member-less base enums
│       ├── config.py                  # all constants, accessors, check_settings()
│       ├── apps.py                    # AppConfig; ready() runs the boot check
│       ├── mixins.py                  # ConditionsMixin + EffectsMixin
│       ├── payloads.py                # bucket_effects() — sorting a store's payloads by type
│       ├── scripts.py                 # EffectsTimerScript (the wall clock)
│       ├── log.py                     # binds effects_conditions_log via evennia-logging-extension
│       └── tests.py                   # unit tests, run via runtests.py
└── tests/                             # standalone test infrastructure
    ├── __init__.py
    ├── test_settings.py
    ├── spec_stubs.py                  # the consumer-shaped catalogue the suite's settings name
    ├── raising_spec_module.py         # import-failure fixture (CF-06)
    ├── game_typeclasses.py            # the mixins on recording DefaultObject stubs
    └── urls.py
```

No `contrib/` — nothing opt-in exists, and the standards forbid scaffolding one empty.

`examples/demo/` is a stock gamedir with the app installed and the macOS SQLite swap in its settings.
There is no behaviour to exercise yet, so it has never been started. **Ask before starting it** — more
than one game may be running from this machine.

Two venvs, both gitignored: `venv/` at the repo root for the library's own tests, and
`examples/venv/` for the demo gamedir. Every library here keeps them separate.

## Tools and environment

- Python 3.10+ (pinned via `pyproject.toml`).
- Runtime dependencies: Evennia and `evennia-logging-extension`.
- **Tests use Django's test runner** via `python runtests.py`, which bootstraps Django then calls
  `evennia._init()`, as the siblings do. Not pytest, and no gamedir required.
- Development uses a dedicated venv at `venv/` (gitignored), independent of any consumer game.

## Sibling libraries to reference

- **[../evennia-environment/](../evennia-environment/)** — the closest reference shape for a library
  at this stage: scaffolded, its vocabulary declared by the consumer, its design being agreed case by
  case. Also the sibling with the nearest vocabulary clash — it has its own `Effect`, meaning a value
  a terrain contributes to a room, which is a different thing from an effect on an actor.
- **[../evennia-equipment/](../evennia-equipment/)** — the reference for consumer-declared
  vocabulary: an enum in the consumer's own module, a setting pointing at it, the library validating
  both sides against that one list. Also a likely first caller — FCM's version applies effects from
  worn items.
- **[../evennia-survival/](../evennia-survival/)** — the reference for a library that hands a
  decision back to the consumer on a clock rather than making it, which is the shape the lifecycle
  question keeps arriving at.
