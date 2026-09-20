# SPDX-License-Identifier: BSD-3-Clause
"""Working with the payloads on an effect record.

The `effects` list is the consumer's, stored verbatim and never interpreted
here. What this module adds is one structural assumption — that a payload is a
mapping carrying a ``type`` — and one service built on it: grouping a store's
payloads by that type so a consumer with several things to rebuild walks the
store once rather than once per thing.

Grouping by a key is not interpreting. Nothing here knows what any type
*means*, and every function behaves identically if each type string is a
random UUID.
"""


class UntypedEffectError(ValueError):
    """A stored payload carries nothing saying what it is.

    Deliberately fatal. A payload with no type cannot be acted on by any
    consumer — there is no reading of it that recovers anything — so skipping
    it would leave an effect that is applied, visible in the store, and
    silently inert. That is the failure that reaches a player doing
    arithmetic, months later, with nothing in a log to point at.

    Payloads are authored in code and seed data and never built at runtime, so
    one of these is a bug in the consumer's own source rather than input to
    tolerate.

    ``ValueError`` because the payload's shape is what is wrong with it.
    """


def bucket_effects(records):
    """Group every payload in an effect store by its type.

    ::

        bucket_effects(actor.active_effects)
        # {"stat_bonus": [{...}, {...}], "size_shift": [{...}]}

    Args:
        records: an effect store — ``{key: {"effects": [...], ...}}`` — or
            ``None``, which is what an actor holds before anything is applied.

    Returns:
        dict: ``{type: [payload, ...]}``. A plain dict, so a type nothing
            carried is absent rather than created on read — several readers
            share one of these during a dispatch, and a ``defaultdict`` would
            have each miss mutate it while the others are still reading.

    Raises:
        UntypedEffectError: if a payload is not a mapping, or carries no
            ``type``. The record's key is in the message: knowing a payload is
            malformed without knowing which of twenty records holds it is
            barely better than knowing nothing.

    One pass over the payloads. A consumer rebuilding three independent things
    from one change calls this once and each part reads its own kinds with
    ``buckets.get(kind, ())``, rather than each walking the whole store and
    skipping what it does not own.

    Payloads are not copied — a bucket holds the stored objects. A caller that
    mutates one is mutating the record, and avoiding that is the caller's
    business; copying every payload on every rebuild to defend against it
    would cost more than it saves.

    A record with no ``effects``, or an empty list, contributes nothing. That
    is the ordinary shape of a condition with no payload, not an error.
    """
    buckets = {}

    for key, record in (records or {}).items():
        for effect in record.get("effects") or ():
            try:
                kind = effect.get("type")
            except AttributeError:
                raise UntypedEffectError(
                    f"record {key!r} carries a payload that is not a mapping: "
                    f"{effect!r}"
                ) from None

            if not kind:
                raise UntypedEffectError(
                    f"record {key!r} carries a payload with no type: "
                    f"{effect!r}"
                )

            buckets.setdefault(kind, []).append(effect)

    return buckets
