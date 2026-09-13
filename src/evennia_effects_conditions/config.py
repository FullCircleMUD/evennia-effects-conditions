# SPDX-License-Identifier: BSD-3-Clause
"""The settings this library reads, and the boot check that refuses bad ones.

Two settings name the consumer's catalogue enums — see
``library-standards.md`` § Consumer-authored config, and ``specs.py`` for what
a catalogue is. Neither has a safe default, so both are validated once at boot
and the instance does not start without them::

    EFFECTS_CONDITION_ENUM = "world.effects.MyConditions"
    EFFECTS_EFFECT_ENUM = "world.effects.MyEffects"

The third names the countdown lifecycles the game will step — see
``docs/design.md`` § Two clocks and a blank. It defaults to none declared:
absence is never a problem, but a declared value is still validated, and the
cross-checks read it either way::

    EFFECTS_LIFECYCLES = ("combat_rounds",)

Every problem across all three is collected and raised together: a consumer
installing this has more than one thing to get right, and stopping at the
first turns that into fix-restart-fix-restart, once per mistake. A check
whose ground itself failed — a member audit on an enum that did not load, a
lifecycle cross-check against a declaration that was refused — is skipped
rather than run against a stand-in, so one mistake reports as one problem
and not as itself plus the noise it would cause downstream.
"""

from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from evennia_effects_conditions.specs import Condition, NamedEffect

SETTING_CONDITION_ENUM = "EFFECTS_CONDITION_ENUM"
SETTING_EFFECT_ENUM = "EFFECTS_EFFECT_ENUM"
SETTING_LIFECYCLES = "EFFECTS_LIFECYCLES"

#: What an undeclared EFFECTS_LIFECYCLES means: no countdown lifecycles. A
#: game using only the wall clock declares nothing.
DEFAULT_LIFECYCLES = ()

#: The one lifecycle the library drives itself — see docs/design.md. Reserved:
#: it may not appear in EFFECTS_LIFECYCLES, and advance_effects() refuses it.
WALL_CLOCK = "wall_clock"

#: What a wall-clock effect's timer script is keyed as, ahead of the effect
#: key: applying "invisible" creates "effect_timer_invisible" on the holder.
TIMER_SCRIPT_PREFIX = "effect_timer_"

#: What each collected problem is prefixed with in the refusal message. One
#: problem per line, so a consumer with three things wrong works through a
#: list rather than a paragraph. Named so a test can count problems without
#: pinning any wording.
PROBLEM_PREFIX = "\n  - "

#: Sentinel distinguishing "argument omitted — auto-fill from the spec" from
#: an explicit None, which suppresses the spec's value. Used by
#: ``EffectsMixin.apply_named_effect()``.
UNSET = object()

#: The spec fields that hold message text, audited as str-or-None. An empty
#: string is legal — it means deliberately silent (docs/design.md § Messages).
_MESSAGE_FIELDS = ("start_first", "start_third", "end_first", "end_third")

#: The EffectSpec fields that hold callables.
_HOOK_FIELDS = ("on_apply", "on_remove", "escape_hook")


def get_condition_enum():
    """The consumer's Condition subclass. Checked at boot."""
    from django.conf import settings

    return import_string(getattr(settings, SETTING_CONDITION_ENUM))


def get_effect_enum():
    """The consumer's NamedEffect subclass. Checked at boot."""
    from django.conf import settings

    return import_string(getattr(settings, SETTING_EFFECT_ENUM))


def get_lifecycles():
    """The declared countdown lifecycle names, as a tuple. May be empty."""
    from django.conf import settings

    return tuple(getattr(settings, SETTING_LIFECYCLES, DEFAULT_LIFECYCLES))


def check_settings():
    """Refuse to start when the declared catalogue is unusable.

    Called from ``AppConfig.ready()``. Collects every problem across all
    three settings, logs the refusal at ERROR, and raises once.
    """
    problems = []
    cause = None

    lifecycle_names, lifecycle_problems = _lifecycle_problems()
    problems.extend(lifecycle_problems)

    condition_enum, resolve_problems, resolve_cause = _resolve_enum(
        SETTING_CONDITION_ENUM, Condition
    )
    problems.extend(resolve_problems)
    cause = cause or resolve_cause

    effect_enum, resolve_problems, resolve_cause = _resolve_enum(
        SETTING_EFFECT_ENUM, NamedEffect
    )
    problems.extend(resolve_problems)
    cause = cause or resolve_cause

    if condition_enum is not None:
        problems.extend(_condition_member_problems(condition_enum))
    if effect_enum is not None:
        problems.extend(
            _effect_member_problems(
                effect_enum,
                # None = the ground failed; skip that cross-check.
                condition_keys=(
                    {member.value for member in condition_enum}
                    if condition_enum is not None
                    else None
                ),
                lifecycle_names=(
                    lifecycle_names if not lifecycle_problems else None
                ),
            )
        )

    if problems:
        message = "evennia-effects-conditions cannot start:" + "".join(
            f"{PROBLEM_PREFIX}{problem}" for problem in problems
        )
        # Lazy import, per the standards — config.py never imports the log
        # shim at module scope.
        from evennia_effects_conditions.log import effects_conditions_log

        effects_conditions_log(message, level="ERROR")
        raise ImproperlyConfigured(message) from cause


def _resolve_enum(setting_name, base):
    """Resolve one enum setting. Returns ``(enum_or_None, problems, cause)``."""
    from django.conf import settings

    example = f"'world.effects.My{base.__name__}s'"
    path = getattr(settings, setting_name, None)
    if not path:
        return None, [
            f"{setting_name} is not set. Set it to the dotted path of your "
            f"{base.__name__} subclass, e.g. {example}."
        ], None
    try:
        resolved = import_string(path)
    except Exception as exc:  # ImportError, or whatever the module raised
        return None, [
            f"{setting_name} names {path!r}, which could not be loaded."
        ], exc
    if resolved is base:
        return None, [
            f"{setting_name} names the library's own base class — declare "
            f"your own subclass and point at it, e.g. {example}."
        ], None
    if not isinstance(resolved, type) or not issubclass(resolved, base):
        return None, [
            f"{setting_name} names {path!r}, which is not a "
            f"{base.__name__} subclass."
        ], None
    return resolved, [], None


def _lifecycle_problems():
    """Validate EFFECTS_LIFECYCLES. Returns ``(names, problems)``.

    An undeclared setting is the default and never a problem; a declared
    value is held to one shape — a sequence of unique, non-empty strings,
    none of them the reserved wall-clock name.
    """
    from django.conf import settings

    value = getattr(settings, SETTING_LIFECYCLES, DEFAULT_LIFECYCLES)
    if isinstance(value, str):
        return (), [
            f"{SETTING_LIFECYCLES} is the bare string {value!r} — declare a "
            f"tuple of names; a string would be read a letter at a time."
        ]
    try:
        names = tuple(value)
    except TypeError:
        return (), [
            f"{SETTING_LIFECYCLES} is {value!r}, which is not a sequence of "
            f"names."
        ]
    problems = []
    bad = [entry for entry in names if not isinstance(entry, str) or not entry]
    if bad:
        problems.append(
            f"{SETTING_LIFECYCLES} entries must be non-empty strings; "
            f"got {bad!r}."
        )
    if len(set(names)) != len(names):
        problems.append(f"{SETTING_LIFECYCLES} declares a name twice.")
    if WALL_CLOCK in names:
        problems.append(
            f"{SETTING_LIFECYCLES} declares {WALL_CLOCK!r}, which is the "
            f"reserved wall-clock lifecycle the library drives itself."
        )
    return names, problems


def _message_field_problems(setting_name, spec):
    """Audit one spec's message fields as str-or-None."""
    problems = []
    for field_name in _MESSAGE_FIELDS:
        value = getattr(spec, field_name)
        if value is not None and not isinstance(value, str):
            problems.append(
                f"{setting_name} member {spec.key!r}: {field_name} must be a "
                f"string or None, got {value!r}."
            )
    return problems


def _condition_member_problems(enum_cls):
    """The per-member audit for the condition catalogue."""
    problems = []
    for member in enum_cls:
        problems.extend(
            _message_field_problems(SETTING_CONDITION_ENUM, member.spec)
        )
    return problems


def _effect_member_problems(enum_cls, condition_keys, lifecycle_names):
    """The per-member audit and cross-checks for the effect catalogue.

    ``condition_keys`` / ``lifecycle_names`` of ``None`` mean that ground
    itself failed and its cross-check is skipped — its own problem is
    already in the list.
    """
    problems = []
    for member in enum_cls:
        spec = member.spec
        problems.extend(_message_field_problems(SETTING_EFFECT_ENUM, spec))
        for field_name in _HOOK_FIELDS:
            value = getattr(spec, field_name)
            if value is not None and not callable(value):
                problems.append(
                    f"{SETTING_EFFECT_ENUM} member {spec.key!r}: {field_name} "
                    f"must be callable or None, got {value!r}."
                )
        companion = spec.companion_script_key
        if companion is not None and (
            not isinstance(companion, str) or not companion
        ):
            problems.append(
                f"{SETTING_EFFECT_ENUM} member {spec.key!r}: "
                f"companion_script_key must be a non-empty string or None, "
                f"got {companion!r}."
            )
        condition = spec.condition
        if condition is not None and not isinstance(condition, str):
            problems.append(
                f"{SETTING_EFFECT_ENUM} member {spec.key!r}: condition must "
                f"be a condition key string or None, got {condition!r}."
            )
        elif (
            condition is not None
            and condition_keys is not None
            and condition not in condition_keys
        ):
            problems.append(
                f"{SETTING_EFFECT_ENUM} member {spec.key!r} names condition "
                f"{condition!r}, which {SETTING_CONDITION_ENUM} does not "
                f"declare."
            )
        lifecycle = spec.lifecycle
        if lifecycle is not None and not isinstance(lifecycle, str):
            problems.append(
                f"{SETTING_EFFECT_ENUM} member {spec.key!r}: lifecycle must "
                f"be a lifecycle name string or None, got {lifecycle!r}."
            )
        elif (
            lifecycle is not None
            and lifecycle != WALL_CLOCK
            and lifecycle_names is not None
            and lifecycle not in lifecycle_names
        ):
            problems.append(
                f"{SETTING_EFFECT_ENUM} member {spec.key!r} names lifecycle "
                f"{lifecycle!r}, which {SETTING_LIFECYCLES} does not declare."
            )
    return problems
