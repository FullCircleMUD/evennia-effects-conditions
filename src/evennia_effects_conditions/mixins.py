# SPDX-License-Identifier: BSD-3-Clause
"""The mixins a game adds to its typeclasses.

``ConditionsMixin`` holds the ref-counted condition store and its transition
messaging. ``EffectsMixin`` (which subclasses it) will add the named-effect
records and their lifecycle — see ``docs/design.md``.
"""

# AttributeProperty is how the stores persist as Evennia Attributes while
# reading as plain properties; the library sets them by assignment throughout.
from evennia.typeclasses.attributes import AttributeProperty

from evennia_effects_conditions.config import UNSET


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
                           messages=None, extras=None):
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
        """
        key_str, spec = self._effect_spec(key)
        if key_str in (self.active_effects or {}):
            return False

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

        if spec.on_apply:
            spec.on_apply(self, source, duration)
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

    # ── the consumer seam ──────────────────────────────────────────── #

    def at_effects_changed(self):
        """React to a change in the effect records. No-op by default.

        THE consumer override point for stats — see ``docs/design.md``
        § Stats. Called after any change to any record's ``effects``
        payload, with the changed store already readable. An override
        rebuilds whatever it means by stats from ``active_effects`` — a
        full re-derive on every call, never an increment.
        """
