# SPDX-License-Identifier: BSD-3-Clause
"""The mixins a game adds to its typeclasses.

``ConditionsMixin`` holds the ref-counted condition store and its transition
messaging. ``EffectsMixin`` (which subclasses it) will add the named-effect
records and their lifecycle — see ``docs/design.md``.
"""

# AttributeProperty is how the stores persist as Evennia Attributes while
# reading as plain properties; the library sets them by assignment throughout.
from evennia.typeclasses.attributes import AttributeProperty


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
