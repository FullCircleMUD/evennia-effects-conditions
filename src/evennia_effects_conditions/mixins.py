# SPDX-License-Identifier: BSD-3-Clause
"""The mixins a game adds to its typeclasses.

``ConditionsMixin`` holds the ref-counted condition store and its transition
messaging. ``EffectsMixin`` (which subclasses it) will add the named-effect
records and their lifecycle — see ``docs/design.md``.
"""

# AttributeProperty is how the stores persist as Evennia Attributes while
# reading as plain properties; the library sets them by assignment throughout.
from evennia.typeclasses.attributes import AttributeProperty

import time

from evennia_effects_conditions.config import (
    EXTEND,
    ON_ACTIVE_CHOICES,
    REFUSE,
    RESET,
    TIMER_SCRIPT_PREFIX,
    UNSET,
    WALL_CLOCK,
)


class ConditionsMixin:
    """Ref-counted condition flags on a holder.

    More than one source can make the same thing true of an actor; the flag
    only clears when the last source lets go. ``add_condition`` reports the
    0→1 transition and ``remove_condition`` the →0 transition, and spec
    messages are delivered only on those transitions.

    Every method accepts a catalogue member or its raw key string. A key the
    catalogue does not declare is refused with ``ValueError`` — the catalogue
    is boot-validated, so an unknown key at runtime is a typo, and counting
    it silently would hide the typo in a flag nothing reads back.
    """

    # Ref-counted condition flags: {"hidden": 1, "darkvision": 2}
    conditions = AttributeProperty(default={})

    # ── resolution ─────────────────────────────────────────────────── #

    def _condition_spec(self, condition):
        """Resolve member-or-string to ``(key, spec)``, refusing unknowns."""
        from evennia_effects_conditions.config import get_condition_enum

        enum_cls = get_condition_enum()
        if isinstance(condition, enum_cls):
            return condition.value, condition.spec
        try:
            member = enum_cls(condition)
        except ValueError:
            raise ValueError(
                f"unknown condition {condition!r} — not declared by "
                f"{enum_cls.__module__}.{enum_cls.__qualname__}"
            ) from None
        return member.value, member.spec

    # ── the counter ────────────────────────────────────────────────── #

    def has_condition(self, condition):
        """Return True if the condition is active (ref count > 0)."""
        key, _ = self._condition_spec(condition)
        return self.conditions.get(key, 0) > 0

    def get_condition_count(self, condition):
        """Return the raw ref count for the condition."""
        key, _ = self._condition_spec(condition)
        return self.conditions.get(key, 0)

    def _add_condition_raw(self, key):
        """Increment the count for a resolved key. True on the 0→1 transition.

        Silent — the named-effect layer uses this so a record's own messages
        speak instead of the condition's.
        """
        counts = dict(self.conditions)
        old_count = counts.get(key, 0)
        counts[key] = old_count + 1
        self.conditions = counts
        return old_count == 0

    def _remove_condition_raw(self, key):
        """Decrement the count for a resolved key. True on the →0 transition.

        Silent, and a no-op at zero — removing what is not held reports
        False rather than going negative.
        """
        counts = dict(self.conditions)
        old_count = counts.get(key, 0)
        if old_count <= 0:
            return False
        if old_count == 1:
            counts.pop(key, None)
        else:
            counts[key] = old_count - 1
        self.conditions = counts
        return old_count == 1

    def add_condition(self, condition):
        """Add one grant of a condition. True if it newly became active.

        The 0→1 transition delivers the spec's start messages; any other
        add is a silent increment.
        """
        key, spec = self._condition_spec(condition)
        newly_active = self._add_condition_raw(key)
        if newly_active:
            self._deliver_transition_messages(
                key,
                first=spec.start_first,
                third=spec.start_third,
                fallback_first=f"You are now affected by {key}.",
                fallback_third=f"{{name}} is now affected by {key}.",
            )
        return newly_active

    def remove_condition(self, condition):
        """Remove one grant of a condition. True if it fully cleared.

        The →0 transition delivers the spec's end messages; any other
        remove is a silent decrement.
        """
        key, spec = self._condition_spec(condition)
        fully_cleared = self._remove_condition_raw(key)
        if fully_cleared:
            self._deliver_transition_messages(
                key,
                first=spec.end_first,
                third=spec.end_third,
                fallback_first=f"You are no longer affected by {key}.",
                fallback_third=f"{{name}} is no longer affected by {key}.",
            )
        return fully_cleared

    # ── messaging ──────────────────────────────────────────────────── #

    def _deliver_transition_messages(
        self, key, first, third, fallback_first, fallback_third
    ):
        """Deliver one transition's messages under the two-rule convention.

        A ``None`` field falls back to the generated generic; an empty
        string is deliberately silent. First person goes to the holder
        directly; third person goes through the ``effects_broadcast`` seam.
        """
        if first is None:
            first = fallback_first
        if first:
            self.msg(first)
        if third is None:
            third = fallback_third
        if third:
            self.effects_broadcast(third)

    def effects_broadcast(self, template):
        """Deliver a third-person line to whoever should see it.

        THE consumer override point for message filtering — see
        ``docs/design.md`` § Messages. The template arrives unformatted,
        ``{name}`` intact, so an override can render the holder's name per
        observer.

        This default is naive: format with the holder's key and send to
        the holder's location, excluding the holder. It knows nothing of
        concealment — a game with visibility rules overrides this one
        method with its own filtering and needs to touch nothing else.
        No-ops without a location.
        """
        location = getattr(self, "location", None)
        if not location:
            return
        location.msg_contents(template.format(name=self.key), exclude=[self])


class EffectsMixin(ConditionsMixin):
    """Named-effect records on a holder — see ``docs/design.md``.

    Tracked, anti-stacking effects that compose a condition flag, an opaque
    ``effects`` payload, messages, and a lifecycle. The library owns when
    things apply, stack and reverse; the consumer's ``at_effects_changed()``
    override owns what the payloads mean.
    """

    # Named effect records: {"blessed": {...}} — see docs/design.md § The record.
    active_effects = AttributeProperty(default={})

    #: The spec fields that carry message text, in record-key order.
    _MESSAGE_KEYS = ("start_first", "start_third", "end_first", "end_third")

    # ── resolution ─────────────────────────────────────────────────── #

    def _effect_spec(self, key):
        """Resolve member-or-string to ``(key, spec)``, refusing unknowns."""
        from evennia_effects_conditions.config import get_effect_enum

        enum_cls = get_effect_enum()
        if isinstance(key, enum_cls):
            return key.value, key.spec
        try:
            member = enum_cls(key)
        except ValueError:
            raise ValueError(
                f"unknown named effect {key!r} — not declared by "
                f"{enum_cls.__module__}.{enum_cls.__qualname__}"
            ) from None
        return member.value, member.spec

    # ── apply and remove ───────────────────────────────────────────── #

    def apply_named_effect(self, key, source=None, effects=None,
                           condition=UNSET, duration=None, lifecycle=UNSET,
                           messages=None, extras=None, on_active=REFUSE,
                           max_duration=None):
        """Apply a named effect. True if applied, False if already active.

        ``condition`` and ``lifecycle`` default to the ``UNSET`` sentinel:
        an omitted argument means "whatever the spec says", an explicit
        ``None`` suppresses the spec's value, and an explicit value
        overrides it.

        Sequencing: the record and condition ref persist first, then
        ``at_effects_changed()`` runs — unwound completely if it raises —
        then messages, the lifecycle start, and ``on_apply`` last.

        Args:
            key: catalogue member or key string.
            source: whatever caused this; handed to ``on_apply``, not stored.
            effects: opaque payload list, stored verbatim, never interpreted.
            duration: int, or None for no expiry of its own.
            messages: per-application overrides, merged over the spec's.
            extras: per-application values, merged over the spec's.
            on_active: what to do when the effect is already active —
                ``REFUSE`` (the default), ``RESET`` or ``EXTEND``. Neither
                readjustment is an apply: the effect never stopped, so no
                messages are delivered, ``on_apply`` does not fire, and the
                condition ref is left where it is.
            max_duration: a ceiling for ``EXTEND``. Ignored by the others,
                whose result is bounded by what they apply.
        """
        key_str, spec = self._effect_spec(key)

        if on_active not in ON_ACTIVE_CHOICES:
            raise ValueError(
                f"on_active must be one of {ON_ACTIVE_CHOICES}, "
                f"got {on_active!r}."
            )

        standing = (self.active_effects or {}).get(key_str)
        if standing is not None:
            if on_active == REFUSE:
                return False
            return self._readjust_effect(
                key_str, standing, duration, on_active, max_duration, extras
            )

        # Auto-fill from the spec where the caller did not decide.
        if condition is UNSET:
            condition_key = spec.condition
        elif condition is None:
            condition_key = None
        else:
            condition_key, _ = self._condition_spec(condition)
        if lifecycle is UNSET:
            lifecycle = spec.lifecycle

        resolved_messages = {
            field: getattr(spec, field) for field in self._MESSAGE_KEYS
        }
        if messages:
            resolved_messages.update(messages)

        record = {
            "condition": condition_key,
            "effects": list(effects) if effects else [],
            "duration": duration,
            "lifecycle": lifecycle,
            "messages": resolved_messages,
            "extras": {**dict(spec.extras), **(dict(extras) if extras else {})},
        }

        # Persist first — the hook rebuilds from active_effects, so it has
        # to be able to see the record it is reacting to.
        records = dict(self.active_effects)
        records[key_str] = record
        self.active_effects = records
        if condition_key:
            self._add_condition_raw(condition_key)

        if record["effects"]:
            try:
                self.at_effects_changed()
            except Exception:
                # The consumer's hook is their bug and propagates untouched;
                # the library's job is only to not be left half-applied.
                records = dict(self.active_effects)
                records.pop(key_str, None)
                self.active_effects = records
                if condition_key:
                    self._remove_condition_raw(condition_key)
                raise

        self._deliver_transition_messages(
            key_str,
            first=resolved_messages["start_first"],
            third=resolved_messages["start_third"],
            fallback_first=f"You are now affected by {key_str}.",
            fallback_third=f"{{name}} is now affected by {key_str}.",
        )

        # The wall clock is the one lifecycle the library drives itself.
        # No duration, no timer — permanent until removed.
        if lifecycle == WALL_CLOCK and duration:
            self._start_effect_timer(key_str, duration)

        if spec.on_apply:
            spec.on_apply(self, source, duration)
        return True

    def _readjust_effect(self, key, record, duration, on_active,
                         max_duration, extras):
        """Reset or extend a record that is already active. Always True.

        Not an apply — the effect never stopped. No start messages, no
        ``on_apply``, and the condition ref stays where it is because it was
        never released. Only the clock moves, and ``extras`` merge so a
        stronger source updates the DC or the damage it set.

        Against a permanent record, whose remaining duration is ``None``:
        RESET gives it the applied duration, and EXTEND leaves it permanent,
        there being nothing to add to. Applying ``duration=None`` with RESET
        makes a timed record permanent and stops its timer.
        """
        remaining = record.get("duration")

        if on_active == RESET:
            new_duration = duration
        elif remaining is None or duration is None:
            # Nothing to add to, or nothing to add.
            new_duration = remaining
        else:
            new_duration = remaining + duration
            if max_duration is not None:
                new_duration = min(new_duration, max_duration)

        updated = dict(record)
        updated["duration"] = new_duration
        if extras:
            updated["extras"] = {
                **dict(record.get("extras") or {}),
                **dict(extras),
            }

        records = dict(self.active_effects)
        records[key] = updated
        self.active_effects = records

        # The record's duration and its timer's interval are one fact; a
        # reschedule that misses leaves get_effect_remaining_seconds()
        # answering for a clock nothing else believes.
        if record.get("lifecycle") == WALL_CLOCK:
            self._stop_effect_timer(key)
            if new_duration is not None:
                self._start_effect_timer(key, new_duration)

        return True

    def remove_named_effect(self, key):
        """Remove a named effect, reversing everything it set up.

        True if removed, False if it was not active. Drops the record,
        decrements the condition ref, delivers the record's end messages,
        fires ``at_effects_changed()`` where a payload existed, and hands
        ``on_remove`` the removed record last.
        """
        key_str, spec = self._effect_spec(key)
        records = dict(self.active_effects)
        record = records.pop(key_str, None)
        if record is None:
            return False
        self.active_effects = records

        condition_key = record.get("condition")
        if condition_key:
            self._remove_condition_raw(condition_key)

        messages = record.get("messages", {})
        self._deliver_transition_messages(
            key_str,
            first=messages.get("end_first"),
            third=messages.get("end_third"),
            fallback_first=f"You are no longer affected by {key_str}.",
            fallback_third=f"{{name}} is no longer affected by {key_str}.",
        )

        if record.get("lifecycle") == WALL_CLOCK:
            self._stop_effect_timer(key_str)

        if record.get("effects"):
            self.at_effects_changed()

        if spec.on_remove:
            spec.on_remove(self, dict(record))
        return True

    # ── queries ────────────────────────────────────────────────────── #

    def has_effect(self, key):
        """Return True if the named effect is active."""
        key_str, _ = self._effect_spec(key)
        return key_str in (self.active_effects or {})

    def get_named_effect(self, key):
        """Return the record for a named effect, or None if not active."""
        key_str, _ = self._effect_spec(key)
        return (self.active_effects or {}).get(key_str)

    def first_active_effect(self, keys):
        """Return the first active key in iteration order, or None.

        The generic form of "is this actor incapacitated / movement-blocked
        / …" — the consumer keeps its policy sets and asks with them.
        """
        for key in keys:
            key_str, _ = self._effect_spec(key)
            if key_str in (self.active_effects or {}):
                return key_str
        return None

    # ── lifecycles ─────────────────────────────────────────────────── #

    def _check_countdown_lifecycle(self, lifecycle):
        """Refuse the wall clock and undeclared names.

        The wall clock already has a driver — two clocks may not move one
        record — and an undeclared name is a typo by the same argument as
        an undeclared condition key: stepping it would silently step
        nothing, forever.
        """
        from evennia_effects_conditions.config import get_lifecycles

        if lifecycle == WALL_CLOCK:
            raise ValueError(
                f"{WALL_CLOCK!r} is the library-driven wall clock — it "
                f"cannot be advanced or cleared as a countdown"
            )
        if lifecycle not in get_lifecycles():
            raise ValueError(
                f"unknown lifecycle {lifecycle!r} — not declared in "
                f"EFFECTS_LIFECYCLES"
            )

    def advance_effects(self, lifecycle):
        """Step every record on one countdown lifecycle.

        The consumer calls this where its own event happens — a combat
        round, a dance, whatever the name means. Per record on the
        lifecycle: the spec's tick hook runs first and may end it at its
        full remaining duration; otherwise the duration decrements, and zero
        expires it through the normal removal path. ``duration=None`` records are
        never touched — they last until ``clear_effects()``.

        Returns:
            list — the keys that ended on this step, tick and expiry
            alike, in record order.
        """
        self._check_countdown_lifecycle(lifecycle)
        ended = []
        decrements = {}
        for key, record in dict(self.active_effects).items():
            if record.get("lifecycle") != lifecycle:
                continue
            spec = self._effect_spec(key)[1]
            if spec.on_tick and spec.on_tick(self, record):
                ended.append(key)
                continue
            if record.get("duration") is None:
                # Ticked, and there is nothing to count down. A permanent is
                # a record nothing wears down, not one nothing happens to.
                continue
            remaining = record["duration"] - 1
            if remaining <= 0:
                ended.append(key)
            else:
                decrements[key] = remaining
        if decrements:
            records = dict(self.active_effects)
            for key, remaining in decrements.items():
                # Copy the record rather than mutating the stored dict.
                updated = dict(records[key])
                updated["duration"] = remaining
                records[key] = updated
            self.active_effects = records
        for key in ended:
            self.remove_named_effect(key)
        return ended

    def clear_effects(self, lifecycle):
        """Remove every record on one countdown lifecycle, with messages.

        How "the thing this lifecycle belongs to ended" generalises —
        combat over, the fair packed up. Catches the ``duration=None``
        records that ``advance_effects()`` never touches.

        Returns:
            list — the keys removed, in record order.
        """
        self._check_countdown_lifecycle(lifecycle)
        cleared = [
            key
            for key, record in dict(self.active_effects).items()
            if record.get("lifecycle") == lifecycle
        ]
        for key in cleared:
            self.remove_named_effect(key)
        return cleared

    def get_effect_remaining_seconds(self, key):
        """Seconds left on a wall-clock effect, or None.

        None for absent effects and for every other lifecycle — a
        countdown's remaining steps are in the record's ``duration``.
        """
        key_str, _ = self._effect_spec(key)
        record = (self.active_effects or {}).get(key_str)
        if (
            not record
            or record.get("lifecycle") != WALL_CLOCK
            or record.get("duration") is None
        ):
            return None
        scripts = self.scripts.get(TIMER_SCRIPT_PREFIX + key_str)
        if not scripts:
            return None
        start_time = scripts[0].start_time
        if start_time is None:
            return None
        return max(0, record["duration"] - (time.time() - start_time))

    def _start_effect_timer(self, key, duration_seconds):
        """Create the one-shot wall-clock timer for an applied effect."""
        # create_script is how a persistent timer entity comes into being —
        # the one piece of the wall clock only the engine can provide.
        from evennia.utils.create import create_script

        from evennia_effects_conditions.scripts import EffectsTimerScript

        script = create_script(
            EffectsTimerScript,
            obj=self,
            key=TIMER_SCRIPT_PREFIX + key,
            autostart=False,
        )
        script.effect_key = key
        script.start_time = time.time()
        script.interval = duration_seconds
        script.start()

    def _stop_effect_timer(self, key):
        """Delete the timer script for an effect, if one is running."""
        scripts = self.scripts.get(TIMER_SCRIPT_PREFIX + key)
        if scripts:
            scripts[0].delete()

    # ── the break verbs and the full strip ─────────────────────────── #

    def break_effect(self, key):
        """Force-remove a named effect. True if it was active.

        The verb behind "attacking shatters your invisibility": **zeroes**
        the condition's ref count — concealment ends, whoever granted it —
        drops the record, stops the timer, fires ``at_effects_changed()``
        where a payload existed, and sends nothing. The caller knows what
        just happened and says so itself.

        Activity is condition-first, as the extracted system had it: an
        effect whose condition is active is breakable with or without a
        record, and a record whose condition was independently zeroed
        reports False and stays — a live consequence of the
        no-reconciliation limit (docs/design.md § Stated limits).

        ``on_remove`` does not fire — the removal callback belongs to the
        normal removal path; break and ``clear_all_effects()`` are forced
        strips.
        """
        key_str, spec = self._effect_spec(key)
        record = (self.active_effects or {}).get(key_str)
        condition_key = record.get("condition") if record else spec.condition

        if condition_key:
            if self.conditions.get(condition_key, 0) <= 0:
                return False
        elif record is None:
            return False

        if condition_key:
            counts = dict(self.conditions)
            counts.pop(condition_key, None)
            self.conditions = counts

        had_payload = False
        if record is not None:
            had_payload = bool(record.get("effects"))
            records = dict(self.active_effects)
            records.pop(key_str, None)
            self.active_effects = records

        self._stop_effect_timer(key_str)
        if had_payload:
            self.at_effects_changed()
        return True

    def break_effects(self, keys, excluded=()):
        """Break a caller-supplied set of keys. Returns what actually broke.

        The plural for "this action ends these" — which keys an action ends
        is game policy, held in the consumer's repo and passed in here, so
        one tuple there reaches every call site. Per key, in order: skipped
        if excluded or inactive; broken via ``break_effect`` where the key
        is a declared effect; a key that is only a bare condition has its
        refs zeroed silently instead. Keys and exclusions accept members of
        either catalogue or raw strings; a key declared in neither is
        refused.

        Silent, like ``break_effect`` — callers message and grant
        consequences off the returned list, not off state that is now gone.
        """
        # Enum here is any catalogue member's common base — the set may mix
        # condition members, effect members and raw strings.
        from enum import Enum

        def as_key(value):
            return value.value if isinstance(value, Enum) else value

        excluded_keys = {as_key(entry) for entry in excluded}
        broken = []
        for key in keys:
            key_str = as_key(key)
            if key_str in excluded_keys:
                continue
            try:
                self._effect_spec(key_str)
                is_effect = True
            except ValueError:
                is_effect = False
            if is_effect and self.break_effect(key_str):
                broken.append(key_str)
                continue
            try:
                condition_key, _ = self._condition_spec(key_str)
            except ValueError:
                if is_effect:
                    continue  # a declared effect that was simply inactive
                raise ValueError(
                    f"unknown key {key_str!r} — declared as neither an "
                    f"effect nor a condition"
                ) from None
            if self.conditions.get(condition_key, 0) > 0:
                counts = dict(self.conditions)
                counts.pop(condition_key, None)
                self.conditions = counts
                broken.append(key_str)
        return broken

    def clear_all_effects(self):
        """Strip every record silently. Returns the keys stripped.

        For death-shaped moments, where a bigger announcement carries the
        context. Record-contributed condition refs decrement — bare grants
        (a racial sense, a stance someone took by hand) survive. Wall-clock
        timers and spec-declared companion scripts stop; this is the only
        place companion scripts are touched (docs/design.md § Ending things
        early). One ``at_effects_changed()`` for the whole strip, and no
        ``on_remove`` calls — a forced strip, like ``break_effect``.
        """
        records = dict(self.active_effects)
        if not records:
            return []

        had_payload = False
        for key, record in records.items():
            condition_key = record.get("condition")
            if condition_key:
                self._remove_condition_raw(condition_key)
            if record.get("effects"):
                had_payload = True
            self._stop_effect_timer(key)
            spec = self._effect_spec(key)[1]
            if spec.companion_script_key:
                companions = self.scripts.get(spec.companion_script_key)
                if companions:
                    companions[0].delete()

        self.active_effects = {}
        if had_payload:
            self.at_effects_changed()
        return list(records)

    # ── the consumer seam ──────────────────────────────────────────── #

    def at_effects_changed(self):
        """React to a change in the effect records. No-op by default.

        THE consumer override point for stats — see ``docs/design.md``
        § Stats. Called after any change to any record's ``effects``
        payload, with the changed store already readable. An override
        rebuilds whatever it means by stats from ``active_effects`` — a
        full re-derive on every call, never an increment.
        """
