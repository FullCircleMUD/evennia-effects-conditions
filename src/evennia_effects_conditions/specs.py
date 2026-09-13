# SPDX-License-Identifier: BSD-3-Clause
"""The declaration surface a consumer subclasses to declare its catalogue.

The library ships two frozen dataclasses — ``ConditionSpec`` and ``EffectSpec``
— and two member-less base enums, ``Condition`` and ``NamedEffect``. A consumer
declares one subclass of each, every member carrying a spec as its value::

    class MyConditions(Condition):
        HIDDEN = ConditionSpec("hidden", start_first="You blend into the shadows.")

    class MyEffects(NamedEffect):
        STUNNED = EffectSpec("stunned", lifecycle="combat_rounds")

Each base's ``__new__`` accepts exactly its own spec class and nothing else, so
a malformed member fails at the ``class`` statement rather than surviving until
something reads it. The member's ``_value_`` is the spec's ``key`` string,
which is what keeps ``MyEffects("stunned")`` resolving — game code passes raw
strings everywhere, and most consumer modules never import the enum at all.

The two spec classes are deliberately **not** related by inheritance: each base
checks its own class with ``isinstance``, and inheritance would make one base
silently accept the other's spec.

Whether a declared *set* is workable — every referenced condition and lifecycle
declared — is checked at boot, not here. A member cannot judge the company it
was declared in. What declaration does refuse is two members sharing a key:
Python's enum machinery would otherwise fold them into an alias, silently
dropping the second spec.

This module imports nothing but the stdlib, because the consumer's declaration
modules resolve during ``django.setup()``.
"""

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional


@dataclass(frozen=True)
class ConditionSpec:
    """What a consumer declares about one condition."""

    key: str
    start_first: Optional[str] = None
    start_third: Optional[str] = None
    end_first: Optional[str] = None
    end_third: Optional[str] = None
    extras: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Copy-then-wrap: the consumer's dict is snapshotted so later mutation
        # of what they passed cannot change the spec, and the proxy refuses
        # writes through the spec itself. object.__setattr__ because the
        # dataclass is frozen.
        object.__setattr__(self, "extras", MappingProxyType(dict(self.extras)))


@dataclass(frozen=True)
class EffectSpec:
    """What a consumer declares about one named effect."""

    key: str
    start_first: Optional[str] = None
    start_third: Optional[str] = None
    end_first: Optional[str] = None
    end_third: Optional[str] = None
    condition: Optional[str] = None
    lifecycle: Optional[str] = None
    on_apply: Optional[Callable] = None
    on_remove: Optional[Callable] = None
    escape_hook: Optional[Callable] = None
    companion_script_key: Optional[str] = None
    extras: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Same copy-then-wrap as ConditionSpec — see there.
        object.__setattr__(self, "extras", MappingProxyType(dict(self.extras)))


def _spec_member(cls, spec, spec_class):
    """Build one enum member from a spec, refusing what declaration can see.

    Two refusals, both at the ``class`` statement:

    - A value that is not exactly this base's spec class. ``isinstance`` is
      enough because the two spec classes are unrelated by design.
    - A key already used by an earlier member. Left alone, Python's enum
      machinery would fold the second member into an alias of the first —
      silently dropping its spec — because ``_value_`` is the key string.
      Earlier members are already registered in ``_value2member_map_`` when a
      later member's ``__new__`` runs, which is what makes the check possible.
    """
    if not isinstance(spec, spec_class):
        raise TypeError(
            f"{cls.__name__} members must be declared with a "
            f"{spec_class.__name__}, got {spec!r}"
        )
    if spec.key in cls._value2member_map_:
        raise ValueError(
            f"{cls.__name__} already has a member with key {spec.key!r} — "
            f"two members may not share a key"
        )
    member = object.__new__(cls)
    member._value_ = spec.key
    member.spec = spec
    return member


class Condition(Enum):
    """Base for a consumer's condition catalogue. Ships no members."""

    def __new__(cls, spec):
        return _spec_member(cls, spec, ConditionSpec)


class NamedEffect(Enum):
    """Base for a consumer's named-effect catalogue. Ships no members."""

    def __new__(cls, spec):
        return _spec_member(cls, spec, EffectSpec)
