"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from evennia.objects.objects import DefaultCharacter

# The one line the library asks of a typeclass. EffectsMixin carries the
# full system, conditions included; the hooks' defaults are enough for a
# demo with no stats and no concealment.
from evennia_effects_conditions.mixins import EffectsMixin

from .objects import ObjectParent


class Character(EffectsMixin, ObjectParent, DefaultCharacter):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.

    """

    pass
