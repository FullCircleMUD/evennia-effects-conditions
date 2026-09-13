# SPDX-License-Identifier: BSD-3-Clause
"""The mixins on plain Evennia objects, for the mixin cases.

Deliberately ``DefaultObject`` and not a character — the library asks nothing
of its holder's class, and a stub that proved the mixin on a character would
leave that unpinned.

Imported inside test bodies, never named in settings: these classes exist for
the suite alone.
"""

# The mixin cases need a real Evennia object so AttributeProperty persistence
# is exercised against the actual attribute machinery, not a fake.
from evennia.objects.objects import DefaultObject

from evennia_effects_conditions.mixins import ConditionsMixin, EffectsMixin


class ConditionsObjectStub(ConditionsMixin, DefaultObject):
    """A holder that records what reaches it.

    ``msg()`` appends to ``received`` instead of delivering to sessions —
    there are none in the suite — so a case reads exactly what the holder
    was told.
    """

    @property
    def received(self):
        if self.ndb.received is None:
            self.ndb.received = []
        return self.ndb.received

    def msg(self, text=None, **kwargs):
        # msg_contents delivers text as a (message, kwargs) tuple; direct
        # msg() calls pass the plain string. Record the string either way.
        if isinstance(text, tuple):
            text = text[0]
        self.received.append(text)


class RecordingBroadcastStub(ConditionsObjectStub):
    """A holder whose broadcast seam records instead of delivering.

    The override deliberately does not call ``super()`` — its whole job is
    to capture what the seam receives (CN-09), not to deliver it.
    """

    @property
    def broadcasts(self):
        if self.ndb.broadcasts is None:
            self.ndb.broadcasts = []
        return self.ndb.broadcasts

    def effects_broadcast(self, template):
        self.broadcasts.append(template)


class EffectsObjectStub(EffectsMixin, DefaultObject):
    """An effects holder that records everything that reaches it.

    ``msg()`` and ``effects_broadcast()`` record as in the condition stubs
    (the broadcast override deliberately does not call ``super()`` — it
    captures, not delivers). ``at_effects_changed()`` records a snapshot of
    ``active_effects`` as seen at call time, which is what EF-07 reads to
    prove the hook fires after the store is readable; it then calls up.
    """

    @property
    def received(self):
        if self.ndb.received is None:
            self.ndb.received = []
        return self.ndb.received

    @property
    def broadcasts(self):
        if self.ndb.broadcasts is None:
            self.ndb.broadcasts = []
        return self.ndb.broadcasts

    @property
    def hook_calls(self):
        if self.ndb.hook_calls is None:
            self.ndb.hook_calls = []
        return self.ndb.hook_calls

    def msg(self, text=None, **kwargs):
        if isinstance(text, tuple):
            text = text[0]
        self.received.append(text)

    def effects_broadcast(self, template):
        self.broadcasts.append(template)

    def at_effects_changed(self):
        self.hook_calls.append({key: dict(rec) for key, rec in self.active_effects.items()})
        super().at_effects_changed()


class RaisingHookStub(EffectsObjectStub):
    """A holder whose recalculate hook raises — the EF-08 unwind fixture.

    Deliberately does not call ``super()``: its whole job is to be the
    consumer bug the library must unwind around.
    """

    def at_effects_changed(self):
        raise RuntimeError("consumer hook bug")
