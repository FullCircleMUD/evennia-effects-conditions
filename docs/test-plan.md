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
| `EF` | The effects mixin core — apply, remove, query, the recalculate hook |
| `LC` | Lifecycles — advancing countdowns, clearing them, the wall-clock timer |
| `BK` | The break verbs — forced, silent removal on a trigger the consumer owns |
| `CL` | `clear_all_effects()` — the silent full strip for death-shaped moments |

## Fixtures

| Fixture | Purpose |
|---|---|
| `tests/spec_stubs.py` | The consumer-shaped enums the suite's settings point at. Imports nothing but `evennia_effects_conditions.specs`, because `ready()` resolves it during `django.setup()`. Grows variant stubs as cases need them |
| `tests/raising_spec_module.py` | A consumer module that raises on import — the negative fixture for `CF-06`, kept in its own file so importing the good stubs never trips it |
| `tests/game_typeclasses.py` | The mixins on plain `DefaultObject`s — deliberately not a character, pinning that the library asks nothing of its holder's class. The stubs record their own `msg()`, `effects_broadcast()` and `at_effects_changed()` calls so cases read what arrived; `RaisingHookStub` is the EF-08 unwind fixture. Imported inside test bodies, never named in settings |

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

## EF — the effects mixin core

The named-effect records from [design.md](design.md): apply with anti-stacking, symmetric removal,
the queries, and the `at_effects_changed()` seam with its unwind guarantee. Lifecycle stepping is
`LC`; the break and clear verbs are `BK`/`CL`.

Apply sequences as: persist the record and the condition ref → `at_effects_changed()` (unwound on
a raise) → messages → lifecycle start → `on_apply`. Removal reverses: drop the record → decrement
the ref → end messages from the record → `at_effects_changed()` → `on_remove` last, handed the
removed record. The hook fires only when the record carries an `effects` payload — a pure
condition-flag effect changes nothing the consumer's rebuild could see.

An effect-granted condition moves **silently** — the record's own messages speak, not the
condition's. The ref still counts, so a condition held by an effect and a bare grant survives the
effect's removal.

**Two divergences from the extracted system, for sign-off with these cases:**

- **Per-application `messages=` merges over the spec's messages** instead of replacing the whole
  set. FCM's replacement semantics forced its SHIELD to re-supply all four strings to override one;
  merge lets a caller override the key it means and keep the rest. An empty string still silences a
  key. Record message keys are named like the spec fields (`start_first` … `end_third`).
- **An explicit `condition=` argument is validated against the catalogue** (`ValueError` on an
  undeclared key), matching CN-10 — the source accepted any string.

| ID | Case | Test function |
|---|---|---|
| EF-01 | Apply records the effect — active, record readable with the documented fields, member and raw string interchangeable | `test_ef_01_apply_records_the_effect_with_the_documented_fields` |
| EF-02 | A second apply anti-stacks: returns False and the standing record is untouched by the second call's arguments | `test_ef_02_a_second_apply_anti_stacks_and_leaves_the_record_alone` |
| EF-03 | An effect key the catalogue does not declare is refused with `ValueError` | `test_ef_03_an_undeclared_effect_key_is_refused` |
| EF-04 | Omitted `condition`/`lifecycle` auto-fill from the spec; explicit `None` suppresses the spec's value; an explicit value overrides it | `test_ef_04_spec_auto_fill_explicit_none_and_explicit_override` |
| EF-05 | An effect-granted condition is added silently — ref +1, active, none of the condition's own messages | `test_ef_05_an_effect_granted_condition_moves_silently` |
| EF-06 | The `effects` payload is stored verbatim and never interpreted — arbitrary consumer shapes survive round-trip | `test_ef_06_the_payload_is_stored_verbatim` |
| EF-07 | `at_effects_changed()` fires on apply and removal only when a payload exists, and at a moment the changed store is already readable | `test_ef_07_the_hook_fires_only_with_a_payload_and_after_the_store_changed` |
| EF-08 | A raising `at_effects_changed()` unwinds the apply — record gone, condition ref gone, no messages, no `on_apply` — and the exception propagates untouched | `test_ef_08_a_raising_hook_unwinds_the_apply_and_propagates` |
| EF-09 | Apply delivers the spec's start messages after the hook succeeds; an anti-stacked apply delivers nothing | `test_ef_09_apply_delivers_start_messages_and_anti_stacking_is_silent` |
| EF-10 | Per-application `messages=` merges over the spec's — the named key changes, the others keep the spec's text, and the merged set is what removal later delivers | `test_ef_10_message_overrides_merge_and_survive_to_removal` |
| EF-11 | Record extras = the spec's `extras` merged with per-application `extras`, the per-application value winning per key | `test_ef_11_record_extras_merge_spec_and_per_application` |
| EF-12 | `on_apply(target, source, duration)` fires last, with the passed source; the source is not stored on the record | `test_ef_12_on_apply_fires_last_with_the_source_which_is_not_stored` |
| EF-13 | Removal reverses everything — record gone, ref decremented, end messages from the record, `on_remove(target, record)` last with the removed record | `test_ef_13_removal_reverses_everything_and_hands_on_remove_the_record` |
| EF-14 | Removing an absent effect returns False and delivers nothing, fires nothing | `test_ef_14_removing_an_absent_effect_is_false_and_silent` |
| EF-15 | `first_active_effect(keys)` returns the first active key in iteration order, None when none are active | `test_ef_15_first_active_effect_returns_the_first_active_in_order` |
| EF-16 | An explicit `condition=` naming an undeclared key is refused with `ValueError` | `test_ef_16_an_undeclared_explicit_condition_is_refused` |
| EF-17 | Two effects coexist independently — removing one leaves the other's record and condition intact | `test_ef_17_two_effects_coexist_and_one_removal_leaves_the_other` |
| EF-18 | `duration` and `lifecycle` are stored as given; `duration=None` is a valid permanent record | `test_ef_18_duration_and_lifecycle_are_stored_as_given` |
| EF-19 | `active_effects` is a persisted Attribute on the holder — it survives a fresh load | `test_ef_19_the_record_store_is_a_persisted_attribute` |

## LC — lifecycles

The clocks from [design.md](design.md) § Two clocks and a blank. Countdowns are stepped from
outside: the consumer calls `advance_effects(name)` where its own event happens, and the library
decrements every record on that name, expiring what reaches zero — an expiry is a normal removal,
end messages and all. `clear_effects(name)` removes everything on a name at once, which is how
"combat ended" generalises; it also catches the `duration=None` records that `advance_effects()`
deliberately never touches. Both return the keys that ended, so the caller can act on what
happened.

The wall clock is the one lifecycle the library drives: applying with it and a duration creates a
one-shot persistent script on the holder that removes the effect when it fires. No ticking — one
deferred callback. The suite never waits on real time: it asserts the script's shape and invokes
its firing hook directly, which is exactly what the reactor would do.

The escape hook runs at each countdown step, before the decrement — True ends the effect there and
then, at its full remaining duration. It runs only for numeric durations; whether a permanent
record should be escapable is the standing open decision below.

`advance_effects()` refuses the wall-clock name — two clocks may not drive one record — and
refuses an undeclared name, which is a typo by the same argument as CN-10.

| ID | Case | Test function |
|---|---|---|
| LC-01 | Advancing one lifecycle decrements only its own records — other countdowns, wall-clock and unmanaged records untouched | `test_lc_01_advance_touches_only_its_own_lifecycle` |
| LC-02 | A record reaching zero is removed as a normal removal — end messages, condition ref decremented | `test_lc_02_expiry_is_a_normal_removal` |
| LC-03 | `advance_effects()` returns exactly the keys that ended this step; survivors are not in it | `test_lc_03_the_return_names_exactly_what_ended` |
| LC-04 | A `duration=None` record on a countdown lifecycle survives every advance untouched | `test_lc_04_a_permanent_record_survives_every_advance` |
| LC-05 | An escape hook returning True ends the effect that step, without a decrement — the record ends at its full remaining duration | `test_lc_05_a_true_escape_ends_the_effect_without_a_decrement` |
| LC-06 | An escape hook returning False leaves the normal decrement; the hook is called once per advance with `(target, record)` | `test_lc_06_a_false_escape_leaves_the_normal_decrement` |
| LC-07 | The escape hook is not called for `duration=None` records | `test_lc_07_the_escape_hook_is_not_called_for_permanent_records` |
| LC-08 | `advance_effects()` refuses the wall-clock name and undeclared names with `ValueError` | `test_lc_08_advance_refuses_the_wall_clock_and_undeclared_names` |
| LC-09 | `clear_effects(name)` removes everything on that name — `duration=None` included — with messages, returning the removed keys; other lifecycles untouched | `test_lc_09_clear_removes_everything_on_one_lifecycle` |
| LC-10 | A wall-clock apply creates a one-shot timer script on the holder — named for the effect, interval = duration — and its firing removes the effect | `test_lc_10_a_wall_clock_apply_creates_the_one_shot_timer` |
| LC-11 | Removing a wall-clock effect stops and deletes its timer script | `test_lc_11_removal_stops_and_deletes_the_timer` |
| LC-12 | `get_effect_remaining_seconds()` counts down from the duration for a wall-clock record, and is None for other lifecycles and absent effects | `test_lc_12_remaining_seconds_counts_down_for_the_wall_clock_only` |
| LC-13 | A wall-clock apply with `duration=None` starts no timer — permanent until removed | `test_lc_13_a_wall_clock_apply_with_no_duration_starts_no_timer` |

## BK — the break verbs

Forced removal from [design.md](design.md) § Ending things early. `break_effect(key)` is what
"attacking shatters your invisibility" calls: it **zeroes** the condition's ref count — concealment
ends, whoever granted it — drops the record, stops the timer, fires `at_effects_changed()` where a
payload existed, and sends nothing. The caller knows what just happened and says so itself.

`break_effects(keys, excluded=())` is the plural for "this action ends these": the caller supplies
the set (game policy, kept in the consumer's repo), and the return names what actually broke, in
order, so messaging and consequences ride on the result. A key that is only a bare condition falls
back to zeroing the refs silently. Keys and exclusions accept members of either catalogue or raw
strings; a key declared in neither is refused.

**Two ported semantics that look like bugs and are not:**

- **Activity is condition-first.** An effect whose spec declares a condition counts as breakable
  while the *condition* is active, record or no record — and conversely, a record whose condition
  was independently zeroed reports False and stays. A live consequence of the no-reconciliation
  limit (design.md § Stated limits), pinned so nobody "fixes" it.
- **Forced strips skip `on_remove`.** The removal callback belongs to the normal removal path;
  `break_effect` and `clear_all_effects()` end things without it, exactly as the extracted system
  did. Stated here and in the API docs.

| ID | Case | Test function |
|---|---|---|
| BK-01 | Break zeroes a multi-source condition entirely — three grants, one break, count 0 | `test_bk_01_break_zeroes_a_multi_source_condition` |
| BK-02 | Break is silent and total — no messages either person, record gone, ref zeroed | `test_bk_02_break_is_silent_and_total` |
| BK-03 | Breaking a wall-clock effect stops and deletes its timer | `test_bk_03_break_stops_the_wall_clock_timer` |
| BK-04 | Break fires `at_effects_changed()` where a payload existed, and never `on_remove` | `test_bk_04_break_fires_the_hook_and_never_on_remove` |
| BK-05 | Condition-first activity, both directions — a bare condition breaks through its effect's key; a record whose condition was independently zeroed reports False and stays | `test_bk_05_condition_first_activity_in_both_directions` |
| BK-06 | Breaking an inactive effect returns False; an undeclared key is refused | `test_bk_06_inactive_is_false_and_undeclared_is_refused` |
| BK-07 | `break_effects` breaks the caller's set, skips `excluded` and the inactive, returns the broken keys in order — members and strings alike | `test_bk_07_break_effects_breaks_the_set_and_reports_in_order` |
| BK-08 | The bare-condition fallback zeroes silently — a condition that is no declared effect still breaks | `test_bk_08_the_bare_condition_fallback_zeroes_silently` |

## CL — the full strip

`clear_all_effects()` from [design.md](design.md) § Ending things early: every record stripped
silently, for moments where a bigger announcement carries the context — death, a remort. Bare
condition grants survive (a dwarf keeps darkvision through dying); record-contributed refs
decrement rather than zero. Wall-clock timers and spec-declared companion scripts stop — the only
place companion scripts are touched, per the ported asymmetry recorded in design.md. One
`at_effects_changed()` for the whole strip.

| ID | Case | Test function |
|---|---|---|
| CL-01 | Every record goes, across all lifecycle shapes, and the stripped keys come back | `test_cl_01_every_record_goes_and_the_keys_come_back` |
| CL-02 | The strip is silent — no messages either person | `test_cl_02_the_strip_is_silent` |
| CL-03 | Record-contributed condition refs decrement; bare grants survive | `test_cl_03_record_refs_decrement_and_bare_grants_survive` |
| CL-04 | Wall-clock timers and spec-declared companion scripts are stopped | `test_cl_04_timers_and_companion_scripts_are_stopped` |
| CL-05 | One `at_effects_changed()` for the whole strip, and no `on_remove` calls | `test_cl_05_one_hook_call_and_no_on_remove` |

## Open decisions

Deliberately without cases. A case is a commitment, so nothing becomes one until it has been
decided.

- **Decided 2026-09-13: the escape hook fires for numeric durations only** (the behaviour LC-07
  pins). `duration=None` is for things that genuinely persist — a stance, a permanent ward — and
  an escapable hold is properly a countdown with an escape hook, not a permanent. A "held until
  you save" effect is declared with a large duration, which behaves identically in play.
- **[TBD — needs discussion: does a `contrib/` ever exist?]** Candidates would be display commands
  (`effects`, `conditions`) and a reference `effects_broadcast` override. Nothing is scaffolded
  until something is decided.

Not open questions, but out of scope by ruling — see [design.md](design.md) § Out of scope:
interpreting effect payloads, convenience wrappers, policy sets, companion scripts, tables.
