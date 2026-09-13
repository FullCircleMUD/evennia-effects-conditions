# Installing

What a game has to do to run this library. Written as each requirement is decided rather than
reconstructed afterwards, so it describes what exists.

**The library is scaffolded and does nothing yet**, so the list below stops after the app is
installed. The steps that declare the vocabulary, mix in the typeclasses and start whatever needs
starting land as each is agreed in [test-plan.md](test-plan.md).

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

## Required settings

None yet. The library reads no settings, because it does nothing yet.

## Optional settings

None yet.

## What is not checked for you

- **That the library is in `INSTALLED_APPS`.** Leave it out and `AppConfig.ready()` never runs, so
  nothing validates anything. There is nothing to validate today, so nothing is lost — but the same
  omission will silently skip every check added from here.
- **That a library import in your settings file sits below `from evennia.settings_default import *`.**
  `LOG_DIR` is set by that import, and a library imported above it is refused at boot. Where your game
  overrides `LOG_DIR`, the override goes directly under that import.

## Watching it

`effects-conditions.log`, beside `server.log` in your `LOG_DIR`. Nothing writes to it yet, so the file
does not appear. What the library should log is decided alongside the first surface that has anything
worth reporting.
