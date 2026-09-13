# Examples

A real Evennia gamedir, for proving the library outside the unit suite. `runtests.py` covers the
library's logic in isolation; this is where it meets a real database, a real boot and a real set of
objects.

`demo/` is a stock gamedir wired as a real consumer: its own catalogue in `world/effects.py`, the
three `EFFECTS_` settings, and `EffectsMixin` on its Character. Validated live — see
[docs/progress.md](../docs/progress.md) — a wall-clock effect expiring on its own timer, a countdown
stepped by `advance_effects()`, and a broken setting refusing the boot with the refusal in
`effects-conditions.log`.

## Setup

```
cd examples
python -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd demo
evennia migrate
```

`requirements.txt` installs Evennia, `sqlean.py` on macOS, and both this library and
`evennia-logging-extension` editable from their checkouts — so an edit under `../src/` takes effect on
the demo's next restart.

`venv/` is gitignored, as is the repo's own `venv/`. The two are separate, and every library here
keeps them that way.

## Running it

```
cd demo
evennia start
```

**Ask before starting it.** More than one game may be running from this machine, and two on the same
ports fail in ways that look like a library fault.

**A fresh database needs its superuser created outside the launcher.** Evennia's `evennia start`
prompts for one interactively, and in a non-TTY session the skipped prompt sends the launcher's
`check_database()` into infinite recursion — a `RecursionError` from deep inside a Django query,
nothing pointing at the real cause. Create it directly first:

```
DJANGO_SETTINGS_MODULE=server.conf.settings DJANGO_SUPERUSER_PASSWORD=p \
    ../venv/bin/python -m django createsuperuser --noinput --username root --email root@test.local
```

(Local demo credentials only, never anything deployed.)

## What is in the settings file

Two blocks, both in `demo/server/conf/settings.py`:

- **The macOS SQLite swap**, directly under `from evennia.settings_default import *`. Apple's
  `libsqlite3.dylib` initialises through libdispatch, which does not survive the fork `evennia start`
  uses to daemonise — so the child deadlocks on its first SQLite call, silently. `sqlean.py` ships a
  statically-linked SQLite, so Apple's is never loaded. It has to run before anything opens a
  database, which is why it sits where it does.
- **The library block** — `INSTALLED_APPS += ["evennia_effects_conditions"]` plus the two required
  catalogue settings and one declared countdown lifecycle, pointing at `world/effects.py`. That
  module is the demo game's own vocabulary, none of it the library's.
