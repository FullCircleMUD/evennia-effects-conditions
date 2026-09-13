# SPDX-License-Identifier: BSD-3-Clause
"""The Django app, and the one thing it does at boot.

``ready()`` runs the settings check, so a consumer with an unusable catalogue
is refused at start with every problem listed, rather than failing later at
the first apply. See ``config.check_settings()``.
"""

from django.apps import AppConfig


class EffectsConditionsConfig(AppConfig):
    """Refuses the boot when the consumer's catalogue settings are unusable."""

    name = "evennia_effects_conditions"
    label = "evennia_effects_conditions"
    verbose_name = "Evennia Effects Conditions"

    def ready(self):
        from evennia_effects_conditions.config import check_settings

        check_settings()
