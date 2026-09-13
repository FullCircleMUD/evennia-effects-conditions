# SPDX-License-Identifier: BSD-3-Clause
"""The demo game's effects catalogue.

**None of this is the library's.** Every condition, effect, message and
lifecycle name here is this game's own vocabulary — the library ships no
members, and this module is what EFFECTS_CONDITION_ENUM / EFFECTS_EFFECT_ENUM
point at. Living under world/ is one way of keeping it tidy and not something
the library asks for.
"""

from evennia_effects_conditions.config import WALL_CLOCK
from evennia_effects_conditions.specs import (
    Condition,
    ConditionSpec,
    EffectSpec,
    NamedEffect,
)


class DemoConditions(Condition):
    GLOWING = ConditionSpec(
        "glowing",
        start_first="You begin to glow softly.",
        start_third="{name} begins to glow softly.",
        end_first="Your glow fades.",
        end_third="The glow around {name} fades.",
    )


class DemoEffects(NamedEffect):
    # A countdown effect — stepped by advance_effects("combat_rounds").
    STUNNED = EffectSpec(
        "stunned",
        lifecycle="combat_rounds",
        start_first="You are stunned!",
        start_third="{name} reels, stunned.",
        end_first="You shake off the stun.",
        end_third="{name} shakes off the stun.",
    )
    # A wall-clock effect with a condition — the library times it itself.
    BLESSED = EffectSpec(
        "blessed",
        condition="glowing",
        lifecycle=WALL_CLOCK,
        start_first="A blessing settles over you.",
        start_third="A blessing settles over {name}.",
        end_first="The blessing wears off.",
        end_third="The blessing on {name} wears off.",
    )
