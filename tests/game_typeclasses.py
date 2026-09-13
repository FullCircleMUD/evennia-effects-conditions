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

from evennia_effects_conditions.mixins import ConditionsMixin


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
