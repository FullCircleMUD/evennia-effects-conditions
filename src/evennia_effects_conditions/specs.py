# SPDX-License-Identifier: BSD-3-Clause
"""The declaration surface a consumer subclasses to declare its catalogue.

The library ships three frozen dataclasses — ``ConditionSpec``, ``EffectSpec``
and ``PayloadSpec`` — and three member-less base enums, ``Condition``,
``NamedEffect`` and ``PayloadType``. A consumer declares one subclass of each,
every member carrying a spec as its value::

    class MyConditions(Condition):
        HIDDEN = ConditionSpec("hidden", start_first="You blend into the shadows.")

    class MyEffects(NamedEffect):
        STUNNED = EffectSpec("stunned", lifecycle="combat_rounds")

    class MyPayloads(PayloadType):
        STAT_BONUS = PayloadSpec("stat_bonus", fields=("stat", "value"))

Each base's ``__new__`` accepts exactly its own spec class and nothing else, so
a malformed member fails at the ``class`` statement rather than surviving until
something reads it. The member's ``_value_`` is the spec's ``key`` string,
which is what keeps ``MyEffects("stunned")`` resolving — game code passes raw
strings everywhere, and most consumer modules never import the enum at all.

The spec classes are deliberately **not** related by inheritance: each base
checks its own class with ``isinstance``, and inheritance would make one base
silently accept another's spec.

Whether a declared *set* is workable — every referenced condition and lifecycle
declared — is checked at boot, not here. A member cannot judge the company it
was declared in. What declaration does refuse is two members sharing a key:
Python's enum machinery would otherwise fold them into an alias, silently
dropping the second spec.

This module imports nothing but the stdlib and ``payloads``, which imports
nothing, because the consumer's declaration modules resolve during
``django.setup()``.
"""

from collections import abc
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional, Sequence

from evennia_effects_conditions.payloads import InvalidPayloadError


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
    on_pre_apply_new: Optional[Callable] = None
    on_apply: Optional[Callable] = None
    on_remove: Optional[Callable] = None
    on_tick: Optional[Callable] = None
    companion_script_key: Optional[str] = None
    extras: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Same copy-then-wrap as ConditionSpec — see there.
        object.__setattr__(self, "extras", MappingProxyType(dict(self.extras)))


@dataclass(frozen=True)
class PayloadSpec:
    """What a consumer declares about one payload type.

    Attributes:
        key: the string a payload of this type carries under ``type``.
        fields: every other key such a payload carries — all required, none
            optional.
        at_validate: the consumer's own check, called as
            ``at_validate(payload)`` once the shape check passes. It refuses
            by raising; its return value is ignored.
    """

    key: str
    fields: Sequence[str]
    at_validate: Optional[Callable] = None

    def __post_init__(self):
        # Snapshotted so later mutation of what the consumer passed cannot
        # change the spec. object.__setattr__ because the dataclass is frozen.
        object.__setattr__(self, "fields", tuple(self.fields))

    def validate(self, payload):
        """Check one payload against this spec.

        The shape first — a mapping, whose ``type`` is this spec's key and
        whose other keys are exactly ``fields`` — then ``at_validate``, if one
        was declared. Values are not the library's to judge; that is what
        ``at_validate`` is for.

        Any mapping passes the mapping check, not just a dict: a payload read
        back from an Attribute is a mapping that is not a dict.

        Raises:
            InvalidPayloadError: the shape does not match, naming what is
                wrong.
            Whatever ``at_validate`` raises, unchanged.
        """
        if not isinstance(payload, abc.Mapping):
            raise InvalidPayloadError(
                f"a {self.key!r} payload must be a mapping, got {payload!r}"
            )

        if payload.get("type") != self.key:
            raise InvalidPayloadError(
                f"payload {payload!r} is not a {self.key!r} payload — its "
                f"type is {payload.get('type')!r}"
            )

        declared = set(self.fields)
        present = set(payload) - {"type"}

        missing = [name for name in self.fields if name not in present]
        if missing:
            raise InvalidPayloadError(
                f"{self.key!r} payload {payload!r} is missing "
                f"{', '.join(repr(name) for name in missing)}"
            )

        undeclared = sorted(present - declared)
        if undeclared:
            raise InvalidPayloadError(
                f"{self.key!r} payload {payload!r} carries undeclared "
                f"{', '.join(repr(name) for name in undeclared)} — declared "
                f"fields are {', '.join(repr(name) for name in self.fields)}"
            )

        if self.at_validate:
            self.at_validate(payload)


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


class PayloadType(Enum):
    """Base for a consumer's payload-type catalogue. Ships no members."""

    def __new__(cls, spec):
        return _spec_member(cls, spec, PayloadSpec)
