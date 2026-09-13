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

## Fixtures

None. The only case is the scaffold, which constructs nothing. The fixtures table grows when a
surface needs one.

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
| SP-09 | Two members of one enum may not share a key — pinned at the declaration surface so the boot check (CF) is the only silent-alias path left | `test_sp_09_two_members_sharing_a_key_are_refused_at_declaration` |

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
