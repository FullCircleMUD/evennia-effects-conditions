# Test plan

Every test case the library commits to covering, and the test function that covers it. The library is
built test-first: cases are agreed here, tests are written against them, then the implementation is
written to pass. The **Test function** column is the auditable trail — it is filled in as each test is
written, so an empty cell means the case is agreed but not yet covered.

Case IDs are stable and referenceable. Do not renumber; retire an ID rather than reuse it. Every test
function carries its case ID as its docstring, so the trail reads in both directions.

All test functions live in `src/evennia_effects_conditions/tests.py`.

Cases land here as each surface is agreed, and no code is written before they do. Nothing is agreed
yet, so the only case below is the scaffold.

Behaviour is agreed here first, before any test or code — see
[test-first-process.md](../../../design/test-first-process.md).

| Prefix | Covers |
|---|---|
| `SC` | The scaffold — the package installs and the runner runs |

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
