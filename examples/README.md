# Examples

A real Evennia gamedir, for proving the library outside the unit suite. `runtests.py` covers the
library's logic in isolation; this is where it meets a real database, a real boot and a real set of
objects.

**There is nothing to prove yet.** The library is scaffolded and has no behaviour, so `demo/` is a
stock gamedir with the app installed and the macOS SQLite workaround in place. It exists now so the
first surface that lands has somewhere to be exercised.

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

## What is in the settings file

Two blocks, both in `demo/server/conf/settings.py`:

- **The macOS SQLite swap**, directly under `from evennia.settings_default import *`. Apple's
  `libsqlite3.dylib` initialises through libdispatch, which does not survive the fork `evennia start`
  uses to daemonise — so the child deadlocks on its first SQLite call, silently. `sqlean.py` ships a
  statically-linked SQLite, so Apple's is never loaded. It has to run before anything opens a
  database, which is why it sits where it does.
- **`INSTALLED_APPS += ["evennia_effects_conditions"]`**, so that the first boot check added to the
  library runs here without a settings edit.
