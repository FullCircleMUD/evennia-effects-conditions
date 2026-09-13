# SPDX-License-Identifier: BSD-3-Clause
"""Consumer-shaped catalogue stubs the suite's settings point at.

Imports nothing but the library itself — ``AppConfig.ready()`` resolves this
module during ``django.setup()``, so anything heavier would drag it into every
boot. The good enums model a small real catalogue; the bad ones each carry
exactly one problem, named for the case that needs it. A module that fails on
import lives separately in ``raising_spec_module.py`` so importing this one
never trips it.
"""

from evennia_effects_conditions.config import WALL_CLOCK
from evennia_effects_conditions.specs import (
    Condition,
    ConditionSpec,
    EffectSpec,
    NamedEffect,
)

#: What the suite's EFFECTS_LIFECYCLES declares (mirrored in test_settings.py).
LIFECYCLES = ("combat_rounds", "fair_dances")


class GoodConditions(Condition):
    """A small valid condition catalogue."""

    HIDDEN = ConditionSpec(
        "hidden",
        start_first="You blend into the shadows.",
        start_third="{name} melts into the shadows.",
        end_first="You step out of the shadows.",
        end_third="{name} steps out of the shadows.",
    )
    # Bare minimum — every message falls back to the generated default.
    DAZZLED = ConditionSpec("dazzled")
    # Every message an empty string — deliberately silent (CN-07).
    MUTED = ConditionSpec(
        "muted", start_first="", start_third="", end_first="", end_third="",
    )


class GoodEffects(NamedEffect):
    """A small valid effect catalogue, one member per lifecycle shape."""

    # Countdown lifecycle.
    STUNNED = EffectSpec(
        "stunned",
        lifecycle="combat_rounds",
        start_first="You are stunned!",
        end_first="You shake off the stun.",
    )
    # Wall clock, granting a condition.
    INVISIBLE = EffectSpec(
        "invisible",
        condition="hidden",
        lifecycle=WALL_CLOCK,
    )
    # Unmanaged — something external ends it.
    POISONED = EffectSpec("poisoned")


class EmptyConditions(Condition):
    """CF-13 — an empty catalogue is a valid catalogue."""


class EmptyEffects(NamedEffect):
    """CF-13 — an empty catalogue is a valid catalogue."""


class BadMessageConditions(Condition):
    """CF-10 — a message field that is neither str nor None."""

    BROKEN = ConditionSpec("broken", end_third=3.5)


class BadMessageEffects(NamedEffect):
    """CF-10 — a message field that is neither str nor None."""

    BROKEN = EffectSpec("broken", start_first=42)


class BadCallableEffects(NamedEffect):
    """CF-11 — a hook that is not callable."""

    BROKEN = EffectSpec("broken", on_apply="not-callable")


class BadCompanionEffects(NamedEffect):
    """CF-12 — an empty companion script key."""

    BROKEN = EffectSpec("broken", companion_script_key="")


class UndeclaredConditionEffects(NamedEffect):
    """CF-18 — an effect naming a condition no catalogue declares."""

    BROKEN = EffectSpec("broken", condition="no_such_condition")


class UndeclaredLifecycleEffects(NamedEffect):
    """CF-19 — an effect naming a lifecycle the settings do not declare."""

    BROKEN = EffectSpec("broken", lifecycle="no_such_lifecycle")


#: CF-07 — a dotted path can resolve to something that is not a class.
NOT_A_CLASS = "just a string"
