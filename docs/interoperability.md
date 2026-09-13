# Interoperability

This library against every sibling library in `libraries/`, including itself. A reader deciding
whether two of our libraries can be co-installed gets a definite statement from either side rather
than inferring from silence.

Each section names the relationship — **hard dependency**, **optional integration**, **indirect
dependency**, or **no coupling** — followed either by the constraints that apply or by an explicit
clearance stating *why* it is clear in terms of what this library does. "No known issues" is not a
clearance.

**The library is scaffolded and implements nothing**, so every clearance below rests on that rather
than on a design decision. They are provisional in the strongest sense: re-read every one of them as
each surface lands.

**A recurring theme, stated once.** Most siblings here are ones a consumer would plausibly *compose*
with this library — a spell that stuns, a mob that resists poison, a weather effect that slows. A
consumer calling both from its own code is not a coupling: it needs no import in either direction and
constrains neither library. Where that is the whole of the relationship, the section says so.

## evennia-ai-memory

**No coupling.** Neither library imports the other. ai-memory owns tables on an alias of its own and
returns structured data for a prompt; this library issues no ORM writes today and whether it owns a
table at all is open. An NPC that remembers being poisoned is the consumer composing the two.

## evennia-archive

**No coupling.** Neither library imports the other. If the active effect list ends up as Attributes on
the actor — which is what FCM's version does, and what the open decision leans toward — it travels
with an archived copy as bytes and comes back with it, timers and all. **That is the one thing to
re-read when the lifecycle is settled**: an effect counting down against a timer that did not survive
the archive is a state this library would have to answer for.

## evennia-calendar

**No coupling.** Neither library imports the other. The calendar reports game time, seasons and phases
of day; nothing about a condition on an actor is a calendar question. A duration measured in game days
rather than real seconds would be the first reason for that to change, and nothing has raised it.

## evennia-database-cascade

**No coupling.** Neither library imports the other. This library owns no models and declares no alias
or router. If it ever gains data of its own, the cascade is how that data gets an alias — see the
cascade's own [installing.md](../../evennia-database-cascade/docs/installing.md).

## evennia-effects-conditions

This library.

## evennia-environment

**No coupling.** Neither library imports the other. **The name clash is the thing to know:**
environment has its own `Effect`, meaning a value a terrain or the weather contributes to a room —
`movement_cost`, `visibility`. That is a property of a place. An effect here is something applied to
an actor for a while. A game running both will hold two meanings of the word, so neither library
should be read as the other's.

A blizzard that blinds is the consumer reading environment's visibility value and calling this
library — composition in their code, no import either way.

## evennia-equipment

**No coupling.** Neither library imports the other, and this library declares no dependency on it.
A worn item that grants an effect is the consumer calling both from its own `at_wear` hook.

## evennia-llm-service

**No coupling.** Neither library imports the other. llm-service is a provider client and a template
loader; it holds no game objects and reads no Attributes. A prompt that mentions an NPC is frightened
is the consumer reading a condition and writing it into its own template.

## evennia-logging-extension

**Hard dependency.** `log.py` binds `effects_conditions_log` through its `make_logger`, and every line
the library emits goes through that binding to `effects-conditions.log`. `pyproject.toml` declares it.
Nothing flows the other way. Nothing calls the binding yet, so the file does not appear.

## evennia-message-bus

**No coupling.** Neither library imports the other. The bus carries messages between instances; a
condition on an actor is local state, and an actor moving between instances travels through the
archive rather than as a message.

## evennia-mob-spawner

**No coupling.** Neither library imports the other. Whether a spawned mob can carry conditions is the
consumer's typeclass decision, invisible to both libraries. Despawning deletes the object, so whatever
this library was holding against it goes with it.

## evennia-portal-multiplex

**No coupling.** Neither library imports the other. Multiplex hands a player's session between Servers
without changing it; nothing about a condition is session state.

## evennia-scaling

**No coupling.** Neither library imports the other. **One thing to re-read when the lifecycle is
settled**: instances are independent, so a wall-clock timer running on one instance is not running on
another. What happens to a thirty-second buff on a character that crosses mid-count is the same
question archive's section raises, from the other side.

## evennia-shards

**No coupling.** Neither library imports the other. The topology to watch is the same one every
clock-driven library has under shards — several server processes over one database, each running its
own timers. It does not bite until this library has a timer, which is open.

## evennia-survival

**No coupling.** Neither library imports the other, and neither needs to. Survival hands both meters
to the consumer on a clock and lets them decide what hunger does; a game that wants starving to apply
a condition calls this library from inside its own `at_regeneration_tick`. That is composition, and it
is the shape both libraries are built for.

## evennia-targeting

**No coupling.** Neither library imports the other, and this library declares no dependency on it, so
it carries no `targeting.py` — see
[library-standards.md](../../../design/library-standards.md) § Targeting callables for the rule that
would apply if it ever did.

## evennia-world-builder

**No coupling.** Neither library imports the other. World content stays out of this library: a room
that poisons whoever stands in it is the consumer's fixture calling this library's API, and an object
world-builder creates goes through the normal typeclass path like any other.

## evennia-yaml-reader

**No coupling.** Neither library imports the other. yaml-reader depends only on `pyyaml`, has no
Evennia dependency and touches no database. If a consumer's condition vocabulary ever comes from YAML,
that is the consumer reading the file and handing the result over.

## fcm-subscriptions

**No coupling.** Neither library imports the other. Subscriptions decides whether an account has paid
for access; conditions are per-actor game state and have nothing to do with access.

## fcm-telemetry-spawn

**No coupling.** Neither library imports the other. telemetry-spawn measures the item and resource
economy; an effect on an actor is not an item and is worth nothing.

## fcm-xrpl

**No coupling.** Neither library imports the other. fcm-xrpl puts item and currency ownership on the
ledger; a condition is transient state on an actor, owned by nobody — there is nothing here to mint,
hold or transfer. An item that *grants* an effect is the item on the ledger, not the effect.
