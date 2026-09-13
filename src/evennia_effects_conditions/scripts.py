# SPDX-License-Identifier: BSD-3-Clause
"""The one-shot wall-clock timer behind the wall-clock lifecycle.

Created by ``EffectsMixin`` when an effect applies on the wall-clock
lifecycle with a duration — see ``docs/design.md`` § Two clocks and a blank.
Fires once after the duration and removes the effect through the normal
removal path, so expiry reverses everything and sends the end messages. No
ticking: one deferred callback per timed effect.
"""

# DefaultScript is Evennia's persistent timer mechanism — it survives a
# reboot and re-fires on schedule, which is what makes a wall-clock effect
# outlive a restart.
from evennia import DefaultScript

# AttributeProperty persists the two values the timer carries, set by
# assignment per the standards.
from evennia.typeclasses.attributes import AttributeProperty


class EffectsTimerScript(DefaultScript):
    """One-shot timer that removes a named effect when it fires."""

    # Key of the named effect to remove on expiry. Set by the mixin before
    # start(); no rule to validate — any declared key is legal, and the
    # catalogue check lives at apply time, not here.
    effect_key = AttributeProperty(default=None)

    # When the clock started, for get_effect_remaining_seconds(). Written
    # once by the mixin; deliberately unconstrained — it is a time.time()
    # stamp, and any float is one.
    start_time = AttributeProperty(default=None)

    def at_script_creation(self):
        self.desc = "Wall-clock effect timer"
        self.interval = 60  # replaced with the real duration before start()
        self.start_delay = True
        self.persistent = True
        self.repeats = 1  # fire once after the duration

    def at_repeat(self):
        """The duration elapsed — remove the effect through the normal path."""
        holder = self.obj
        if self.effect_key and hasattr(holder, "remove_named_effect"):
            holder.remove_named_effect(self.effect_key)
