# Test plan

Every test case the library commits to covering, and the test function that covers it. The library is
built test-first: cases are agreed here, tests are written against them, then the implementation is
written to pass. The **Test function** column is the auditable trail — it is filled in as each test is
written, so an empty cell means the case is agreed but not yet covered.

Case IDs are stable and referenceable. Do not renumber; retire an ID rather than reuse it. Every test
function carries its case ID as its docstring, so the trail reads in both directions.

All test functions live in `src/evennia_effects_conditions/tests.py`.

Cases land here as each surface is agreed, and no code is written before they do. The architecture
is agreed in [design.md](design.md); cases arrive surface by surface as each is built, so the only
cases below are for surfaces whose behaviour has been settled to that level of detail.

Behaviour is agreed here first, before any test or code — see
[test-first-process.md](../../../design/test-first-process.md).

| Prefix | Covers |
|---|---|
| `SC` | The scaffold — the package installs and the runner runs |
| `SP` | The spec dataclasses and the two base enums a consumer subclasses |
| `CF` | The settings and the boot check |
| `CN` | The conditions mixin — ref counting, transition messaging, the broadcast seam |

## Fixtures

| Fixture | Purpose |
|---|---|
| `tests/spec_stubs.py` | The consumer-shaped enums the suite's settings point at. Imports nothing but `evennia_effects_conditions.specs`, because `ready()` resolves it during `django.setup()`. Grows variant stubs as cases need them |
| `tests/raising_spec_module.py` | A consumer module that raises on import — the negative fixture for `CF-06`, kept in its own file so importing the good stubs never trips it |
| `tests/game_typeclasses.py` | The mixins on plain `DefaultObject`s — deliberately not a character, pinning that the library asks nothing of its holder's class. `ConditionsObjectStub` records its own `msg()` and `effects_broadcast()` calls so message cases read what arrived. Imported inside test bodies, never named in settings |

The SP cases use no fixtures — they declare consumer-shaped enums inline, pure stdlib.

## SC — the scaffold

Not behaviour of the library, but a check that there is a library to test. It fails when the editable
install is missing, when the test settings do not name the app, or when the runner cannot find the
test module — each of which otherwise looks like "no tests ran".

| ID | Case | Test function |
|---|---|---|
| SC-01 | The package imports and reports its version | `test_sc_01_package_imports_and_reports_its_version` |

## SP — specs and the base enums

The declaration surface from [design.md](design.md) § The catalogue. A consumer subclasses the two
member-less base enums, every member's value a frozen spec. The base's `__new__` accepts exactly
the right spec class, so a malformed member fails at the `class` statement rather than surviving
until something reads it. The member's `_value_` is the spec's `key` string — the guarantee that
`MyEffects("stunned")` resolves, which is what lets game code pass raw strings everywhere.

`ConditionSpec` and `EffectSpec` are two independent dataclasses, deliberately not related by
inheritance: each base enum checks its own spec class with `isinstance`, and inheritance would make
one base silently accept the other's spec.

These cases are pure stdlib — no Evennia, no Django, no fixtures. Consumer-shaped enums are
declared inline in the tests.

| ID | Case | Test function |
|---|---|---|
| SP-01 | A member carries its spec (`member.spec`) and its value is the spec's key string | `test_sp_01_member_carries_its_spec_and_its_value_is_the_key` |
| SP-02 | Enum-by-value lookup with the raw key string resolves to the member | `test_sp_02_lookup_by_raw_key_string_resolves_to_the_member` |
| SP-03 | A `NamedEffect` member declared with anything but an `EffectSpec` — including a `ConditionSpec` — is refused at class creation | `test_sp_03_named_effect_member_refuses_anything_but_an_effect_spec` |
| SP-04 | A `Condition` member declared with anything but a `ConditionSpec` — including an `EffectSpec` — is refused at class creation | `test_sp_04_condition_member_refuses_anything_but_a_condition_spec` |
| SP-05 | Specs are frozen — assigning any field after construction raises | `test_sp_05_specs_are_frozen` |
| SP-06 | A spec's `extras` mapping is read-only on the spec | `test_sp_06_extras_mapping_is_read_only_on_the_spec` |
| SP-07 | A spec declares with only a key — every other field defaults (messages `None`, callables `None`, `lifecycle`/`condition` `None`, `extras` empty) | `test_sp_07_key_only_declaration_defaults_every_other_field` |
| SP-08 | The two base enums themselves have no members | `test_sp_08_the_base_enums_have_no_members` |
| SP-09 | Two members of one enum may not share a key — refused at the `class` statement, where Python would otherwise fold them into a silent alias | `test_sp_09_two_members_sharing_a_key_are_refused_at_declaration` |

## CF — the settings and the boot check

Three settings, per [design.md](design.md) § The catalogue: `EFFECTS_CONDITION_ENUM` and
`EFFECTS_EFFECT_ENUM` name the consumer's two enum subclasses and are required — neither has a safe
default, so both are checked in `check_settings()`, called from `AppConfig.ready()`, and the game
does not start without them. `EFFECTS_LIFECYCLES` names the countdown lifecycles and defaults to
`()`; absence is never a problem, but a declared value is still validated, and the cross-checks
read it either way.

Every problem across all three settings is collected and raised as one `ImproperlyConfigured`, the
same text logged at ERROR first — a consumer with three things wrong works through a list, not a
raise-fix-raise loop. A check whose ground itself failed — a member audit on an enum that did not
load, a cross-check against a refused lifecycle declaration — is skipped rather than run against a
stand-in, so one mistake reports as one problem and not as itself plus its downstream noise.

**No aliased-member check.** The plan expected boot to catch two members folding into one, but
SP-09 refuses a duplicate key at the `class` statement, so a consumer enum that resolves at all
cannot contain an alias. Boot checks what declaration cannot see: the set against the settings, and
the sets against each other.

**No cross-enum key-uniqueness check.** The same key in both enums is the legitimate dual-system
case — see [design.md](design.md) § The catalogue.

| ID | Case | Test function |
|---|---|---|
| CF-01 | A valid configuration — both enums resolving, lifecycles declared — raises nothing | `test_cf_01_a_valid_configuration_raises_nothing` |
| CF-02 | `EFFECTS_CONDITION_ENUM` unset is refused, the problem naming the setting | `test_cf_02_condition_enum_unset_is_refused_naming_the_setting` |
| CF-03 | `EFFECTS_EFFECT_ENUM` unset is refused, the problem naming the setting | `test_cf_03_effect_enum_unset_is_refused_naming_the_setting` |
| CF-04 | Both unset produce one raise carrying both problems | `test_cf_04_both_unset_produce_one_raise_carrying_both` |
| CF-05 | A dotted path that does not resolve is refused, the original error chained as cause | `test_cf_05_an_unresolvable_path_is_refused_with_the_cause_chained` |
| CF-06 | A consumer module that raises on import is refused, that error chained as cause | `test_cf_06_a_raising_consumer_module_is_refused_with_that_error_chained` |
| CF-07 | A path resolving to something that is not a class is refused | `test_cf_07_a_path_resolving_to_a_non_class_is_refused` |
| CF-08 | A class that does not subclass the right base is refused | `test_cf_08_a_class_not_subclassing_the_right_base_is_refused` |
| CF-09 | The library's own base class is refused | `test_cf_09_the_library_base_itself_is_refused` |
| CF-10 | A member whose message field is neither `str` nor `None` is refused, naming member and field | `test_cf_10_a_non_string_message_field_is_refused_naming_member_and_field` |
| CF-11 | A member whose `on_apply`/`on_remove`/`escape_hook` is not callable is refused | `test_cf_11_a_non_callable_hook_is_refused` |
| CF-12 | A member whose `companion_script_key` is an empty string is refused | `test_cf_12_an_empty_companion_script_key_is_refused` |
| CF-13 | An empty consumer enum is allowed — each half of the system stands alone | `test_cf_13_an_empty_consumer_enum_is_allowed` |
| CF-14 | `EFFECTS_LIFECYCLES` as a bare string is refused (a string is a sequence of letters) | `test_cf_14_lifecycles_as_a_bare_string_is_refused` |
| CF-15 | A lifecycle entry that is not a non-empty string is refused | `test_cf_15_a_non_string_or_empty_lifecycle_entry_is_refused` |
| CF-16 | Duplicate lifecycle names are refused | `test_cf_16_duplicate_lifecycle_names_are_refused` |
| CF-17 | The reserved wall-clock name in `EFFECTS_LIFECYCLES` is refused | `test_cf_17_the_reserved_wall_clock_name_is_refused` |
| CF-18 | An effect whose `condition` names no declared condition is refused, naming both | `test_cf_18_an_effect_naming_an_undeclared_condition_is_refused` |
| CF-19 | An effect whose `lifecycle` is neither declared nor the wall clock is refused, naming both | `test_cf_19_an_effect_naming_an_undeclared_lifecycle_is_refused` |
| CF-20 | An effect on the wall-clock lifecycle passes without declaring anything | `test_cf_20_the_wall_clock_lifecycle_needs_no_declaration` |
| CF-21 | The refusal is logged to disk at ERROR carrying the same text as the exception — read back from the file, never mocked | `test_cf_21_the_refusal_is_logged_at_error_with_the_same_text` |
| CF-22 | The accessors return the resolved classes and the declared lifecycles; lifecycles default to `()` | `test_cf_22_the_accessors_return_the_resolved_values` |

## CN — the conditions mixin

The ref-counted flag store from [design.md](design.md) § The shape. Multiple sources can make the
same thing true of an actor; the flag clears only when the last one lets go. `add_condition()`
reports the 0→1 transition, `remove_condition()` the →0 transition, and messages are delivered
only on those transitions — an increment or decrement in between is silent. Both accept a member
or a raw key string.

Messaging follows [design.md](design.md) § Messages: the spec's text, first person delivered by
the library (`holder.msg`), third person through the one `effects_broadcast(template)` seam. The
default broadcast formats `{name}` with the holder's key and sends to the holder's location
excluding the holder; an override receives the template unformatted so a game can render the name
per observer.

**Divergence from the extracted system, for sign-off with these cases:** FCM's mixin ref-counts
any string it is handed. Here a key the catalogue does not declare is refused with `ValueError` —
the catalogue is declared and boot-validated, so an unknown key at runtime is a typo, and
ref-counting it silently would hide the typo in a flag nothing can ever read back by its right
name.

| ID | Case | Test function |
|---|---|---|
| CN-01 | Adding on 0→1 returns True; the flag reads back active with count 1; member and raw string are interchangeable | `test_cn_01_first_add_reports_the_transition_and_counts_one` |
| CN-02 | A second add returns False and increments to 2 — still active, no re-announcement | `test_cn_02_a_second_add_increments_silently` |
| CN-03 | Remove decrements; only the →0 remove returns True; removing an absent condition returns False and the count stays 0 | `test_cn_03_only_the_last_remove_reports_and_absent_removes_are_false` |
| CN-04 | An unheld condition reads back inactive with count 0 | `test_cn_04_an_unheld_condition_reads_back_inactive` |
| CN-05 | The 0→1 add delivers the spec's start messages — first person to the holder, third person through the broadcast seam; a 1→2 add delivers nothing | `test_cn_05_the_first_add_delivers_start_messages_the_second_nothing` |
| CN-06 | The →0 remove delivers the end messages; a 2→1 remove delivers nothing | `test_cn_06_the_last_remove_delivers_end_messages_earlier_ones_nothing` |
| CN-07 | A missing message field falls back to the generated default; an empty string is deliberately silent | `test_cn_07_missing_messages_fall_back_and_empty_strings_are_silent` |
| CN-08 | The default broadcast sends the formatted text to the holder's location excluding the holder, and no-ops without a location | `test_cn_08_the_default_broadcast_reaches_the_room_not_the_holder` |
| CN-09 | An `effects_broadcast` override receives the template unformatted, `{name}` intact | `test_cn_09_a_broadcast_override_receives_the_template_unformatted` |
| CN-10 | A key the catalogue does not declare is refused with `ValueError`, add and remove alike | `test_cn_10_an_undeclared_key_is_refused_add_and_remove_alike` |
| CN-11 | The store is an Evennia Attribute on the holder, written by assignment — it survives a fresh load of the object | `test_cn_11_the_store_is_a_persisted_attribute_on_the_holder` |

## Open decisions

Deliberately without cases. A case is a commitment, so nothing becomes one until it has been
decided.

- **[TBD — needs discussion: does the escape hook fire for `duration=None` records?]** The
  extracted system only ran its save inside the numeric-duration branch, so a permanent hold was
  never escapable. A per-step-escapable permanent effect is a plausible want; the port keeps the
  extracted behaviour until decided.
- **[TBD — needs discussion: does a `contrib/` ever exist?]** Candidates would be display commands
  (`effects`, `conditions`) and a reference `effects_broadcast` override. Nothing is scaffolded
  until something is decided.

Not open questions, but out of scope by ruling — see [design.md](design.md) § Out of scope:
interpreting effect payloads, convenience wrappers, policy sets, companion scripts, tables.
