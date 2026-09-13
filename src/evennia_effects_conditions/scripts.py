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


class EffectsTimerScript(DefaultScript):
    """One-shot timer that removes a named effect when it fires.

    Attributes (set via db before start):
        effect_key (str): key of the named effect to remove on expiry.
        start_time (float): when the clock started, for remaining-seconds.
    """

    def at_script_creation(self):
        self.desc = "Wall-clock effect timer"
        self.interval = 60  # replaced with the real duration before start()
        self.start_delay = True
        self.persistent = True
        self.repeats = 1  # fire once after the duration

    def at_repeat(self):
        """The duration elapsed — remove the effect through the normal path."""
        holder = self.obj
        effect_key = self.db.effect_key
        if effect_key and hasattr(holder, "remove_named_effect"):
            holder.remove_named_effect(effect_key)
