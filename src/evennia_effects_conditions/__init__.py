# SPDX-License-Identifier: BSD-3-Clause
"""evennia-effects-conditions: conditions and timed effects for Evennia actors.

The public surface, resolved lazily — importing the package runs while Django
is still building its app registry, so the mixins (which touch Evennia's
attribute machinery) must not be imported at package scope.

See docs/INDEX.md for the design wiki and docs/test-plan.md for the cases the
library commits to.
"""

__version__ = "0.0.1"


def __getattr__(name):
    # Public name → defining module, resolved on first attribute access.
    exports = {
        "Condition": "evennia_effects_conditions.specs",
        "ConditionSpec": "evennia_effects_conditions.specs",
        "EffectSpec": "evennia_effects_conditions.specs",
        "NamedEffect": "evennia_effects_conditions.specs",
        "ConditionsMixin": "evennia_effects_conditions.mixins",
        "EffectsMixin": "evennia_effects_conditions.mixins",
        "EffectsTimerScript": "evennia_effects_conditions.scripts",
        "WALL_CLOCK": "evennia_effects_conditions.config",
        "UNSET": "evennia_effects_conditions.config",
        "bucket_effects": "evennia_effects_conditions.payloads",
        "UntypedEffectError": "evennia_effects_conditions.payloads",
    }
    if name in exports:
        from importlib import import_module

        return getattr(import_module(exports[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
