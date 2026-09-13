# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for evennia-effects-conditions, run via ``python runtests.py``.

Every case the library commits to lives in docs/test-plan.md, and every test
function here carries its case ID as its docstring so the trail reads both ways.
"""

import dataclasses
import os
from unittest import TestCase

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

import evennia_effects_conditions
from evennia_effects_conditions.config import (
    PROBLEM_PREFIX,
    SETTING_CONDITION_ENUM,
    SETTING_EFFECT_ENUM,
    SETTING_LIFECYCLES,
    WALL_CLOCK,
    check_settings,
    get_condition_enum,
    get_effect_enum,
    get_lifecycles,
)
from evennia_effects_conditions.specs import (
    Condition,
    ConditionSpec,
    EffectSpec,
    NamedEffect,
)


class ScaffoldTests(TestCase):
    """The install and the test runner work end to end."""

    def test_sc_01_package_imports_and_reports_its_version(self):
        """SC-01"""
        self.assertEqual(evennia_effects_conditions.__version__, "0.0.1")


class SpecTests(TestCase):
    """The declaration surface — specs and the base enums (SP)."""

    def test_sp_01_member_carries_its_spec_and_its_value_is_the_key(self):
        """SP-01"""
        cond_spec = ConditionSpec("hidden")
        effect_spec = EffectSpec("stunned")

        class Conds(Condition):
            HIDDEN = cond_spec

        class Effects(NamedEffect):
            STUNNED = effect_spec

        self.assertIs(Conds.HIDDEN.spec, cond_spec)
        self.assertEqual(Conds.HIDDEN.value, "hidden")
        self.assertIs(Effects.STUNNED.spec, effect_spec)
        self.assertEqual(Effects.STUNNED.value, "stunned")

    def test_sp_02_lookup_by_raw_key_string_resolves_to_the_member(self):
        """SP-02"""

        class Conds(Condition):
            HIDDEN = ConditionSpec("hidden")

        class Effects(NamedEffect):
            STUNNED = EffectSpec("stunned")

        self.assertIs(Conds("hidden"), Conds.HIDDEN)
        self.assertIs(Effects("stunned"), Effects.STUNNED)

    def test_sp_03_named_effect_member_refuses_anything_but_an_effect_spec(self):
        """SP-03"""
        with self.assertRaises(TypeError):

            class WrongSpec(NamedEffect):
                STUNNED = ConditionSpec("stunned")

        with self.assertRaises(TypeError):

            class BareString(NamedEffect):
                STUNNED = "stunned"

    def test_sp_04_condition_member_refuses_anything_but_a_condition_spec(self):
        """SP-04"""
        with self.assertRaises(TypeError):

            class WrongSpec(Condition):
                HIDDEN = EffectSpec("hidden")

        with self.assertRaises(TypeError):

            class BareString(Condition):
                HIDDEN = "hidden"

    def test_sp_05_specs_are_frozen(self):
        """SP-05"""
        cond_spec = ConditionSpec("hidden")
        effect_spec = EffectSpec("stunned")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            cond_spec.key = "other"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            effect_spec.lifecycle = "other"

    def test_sp_06_extras_mapping_is_read_only_on_the_spec(self):
        """SP-06"""
        spec = EffectSpec("stunned", extras={"save_dc": 12})
        self.assertEqual(spec.extras["save_dc"], 12)
        with self.assertRaises(TypeError):
            spec.extras["save_dc"] = 15

    def test_sp_07_key_only_declaration_defaults_every_other_field(self):
        """SP-07"""
        cond_spec = ConditionSpec("hidden")
        for field_name in ("start_first", "start_third", "end_first", "end_third"):
            self.assertIsNone(getattr(cond_spec, field_name))
        self.assertEqual(dict(cond_spec.extras), {})

        effect_spec = EffectSpec("stunned")
        for field_name in (
            "start_first", "start_third", "end_first", "end_third",
            "condition", "lifecycle",
            "on_apply", "on_remove", "escape_hook", "companion_script_key",
        ):
            self.assertIsNone(getattr(effect_spec, field_name))
        self.assertEqual(dict(effect_spec.extras), {})

    def test_sp_08_the_base_enums_have_no_members(self):
        """SP-08"""
        self.assertEqual(list(Condition), [])
        self.assertEqual(list(NamedEffect), [])

    def test_sp_09_two_members_sharing_a_key_are_refused_at_declaration(self):
        """SP-09"""
        with self.assertRaises(ValueError):

            class DupEffects(NamedEffect):
                FIRST = EffectSpec("same", start_first="one thing")
                SECOND = EffectSpec("same", start_first="another thing")

        with self.assertRaises(ValueError):

            class DupConds(Condition):
                FIRST = ConditionSpec("same")
                SECOND = ConditionSpec("same", start_first="differs")


class BootCheckTests(SimpleTestCase):
    """The settings and the boot check (CF)."""

    # ── helpers ────────────────────────────────────────────────────── #

    def _refusal(self, **overrides):
        """Run check_settings under overrides, return the refusal text."""
        with override_settings(**overrides):
            with self.assertRaises(ImproperlyConfigured) as caught:
                check_settings()
        return str(caught.exception)

    def _cause(self, **overrides):
        """Run check_settings under overrides, return the chained cause."""
        with override_settings(**overrides):
            with self.assertRaises(ImproperlyConfigured) as caught:
                check_settings()
        return caught.exception.__cause__

    # CF-21 reads the log back from disk rather than mocking the log
    # function — a mocked delivery case can pass while no line ever
    # reaches a file.

    def _read_back_logs(self):
        """Everything under the suite's LOG_DIR, as one string."""
        from django.conf import settings

        text = []
        for name in sorted(os.listdir(settings.LOG_DIR)):
            if name.endswith(".log"):
                path = os.path.join(settings.LOG_DIR, name)
                with open(path, encoding="utf-8") as handle:
                    text.append(handle.read())
        return "\n".join(text)

    def _clear_logs(self):
        """Empty LOG_DIR's files so a line read back was written by this test.

        Truncated, never removed: Evennia's log machinery caches the file
        handle after the first write, and removing the file leaves that
        handle appending to an unlinked inode — every later line silently
        vanishes. An append-mode handle seeks to the end on each write, so
        a truncated file stays live.
        """
        from django.conf import settings

        for name in os.listdir(settings.LOG_DIR):
            if name.endswith(".log"):
                with open(os.path.join(settings.LOG_DIR, name), "w"):
                    pass

    # ── the resolution chain ───────────────────────────────────────── #

    def test_cf_01_a_valid_configuration_raises_nothing(self):
        """CF-01"""
        check_settings()  # the suite's own settings are the valid case

    def test_cf_02_condition_enum_unset_is_refused_naming_the_setting(self):
        """CF-02"""
        message = self._refusal(**{SETTING_CONDITION_ENUM: None})
        self.assertIn(SETTING_CONDITION_ENUM, message)

    def test_cf_03_effect_enum_unset_is_refused_naming_the_setting(self):
        """CF-03"""
        message = self._refusal(**{SETTING_EFFECT_ENUM: None})
        self.assertIn(SETTING_EFFECT_ENUM, message)

    def test_cf_04_both_unset_produce_one_raise_carrying_both(self):
        """CF-04"""
        message = self._refusal(
            **{SETTING_CONDITION_ENUM: None, SETTING_EFFECT_ENUM: None}
        )
        self.assertIn(SETTING_CONDITION_ENUM, message)
        self.assertIn(SETTING_EFFECT_ENUM, message)
        self.assertGreaterEqual(message.count(PROBLEM_PREFIX), 2)

    def test_cf_05_an_unresolvable_path_is_refused_with_the_cause_chained(self):
        """CF-05"""
        cause = self._cause(
            **{SETTING_CONDITION_ENUM: "tests.spec_stubs.DoesNotExist"}
        )
        self.assertIsInstance(cause, ImportError)

    def test_cf_06_a_raising_consumer_module_is_refused_with_that_error_chained(self):
        """CF-06"""
        cause = self._cause(
            **{SETTING_EFFECT_ENUM: "tests.raising_spec_module.Anything"}
        )
        self.assertIsInstance(cause, RuntimeError)

    def test_cf_07_a_path_resolving_to_a_non_class_is_refused(self):
        """CF-07"""
        message = self._refusal(
            **{SETTING_CONDITION_ENUM: "tests.spec_stubs.NOT_A_CLASS"}
        )
        self.assertIn(SETTING_CONDITION_ENUM, message)

    def test_cf_08_a_class_not_subclassing_the_right_base_is_refused(self):
        """CF-08"""
        # A perfectly good condition catalogue is still not an effect catalogue.
        message = self._refusal(
            **{SETTING_EFFECT_ENUM: "tests.spec_stubs.GoodConditions"}
        )
        self.assertIn(SETTING_EFFECT_ENUM, message)

    def test_cf_09_the_library_base_itself_is_refused(self):
        """CF-09"""
        message = self._refusal(
            **{SETTING_CONDITION_ENUM: "evennia_effects_conditions.specs.Condition"}
        )
        self.assertIn(SETTING_CONDITION_ENUM, message)

    # ── the per-member audit ───────────────────────────────────────── #

    def test_cf_10_a_non_string_message_field_is_refused_naming_member_and_field(self):
        """CF-10"""
        message = self._refusal(
            **{SETTING_EFFECT_ENUM: "tests.spec_stubs.BadMessageEffects"}
        )
        self.assertIn("broken", message)
        self.assertIn("start_first", message)
        message = self._refusal(
            **{SETTING_CONDITION_ENUM: "tests.spec_stubs.BadMessageConditions"}
        )
        self.assertIn("broken", message)
        self.assertIn("end_third", message)

    def test_cf_11_a_non_callable_hook_is_refused(self):
        """CF-11"""
        message = self._refusal(
            **{SETTING_EFFECT_ENUM: "tests.spec_stubs.BadCallableEffects"}
        )
        self.assertIn("on_apply", message)

    def test_cf_12_an_empty_companion_script_key_is_refused(self):
        """CF-12"""
        message = self._refusal(
            **{SETTING_EFFECT_ENUM: "tests.spec_stubs.BadCompanionEffects"}
        )
        self.assertIn("companion_script_key", message)

    def test_cf_13_an_empty_consumer_enum_is_allowed(self):
        """CF-13"""
        with override_settings(
            **{
                SETTING_CONDITION_ENUM: "tests.spec_stubs.EmptyConditions",
                SETTING_EFFECT_ENUM: "tests.spec_stubs.EmptyEffects",
            }
        ):
            check_settings()

    # ── the lifecycle declaration ──────────────────────────────────── #

    def test_cf_14_lifecycles_as_a_bare_string_is_refused(self):
        """CF-14"""
        message = self._refusal(**{SETTING_LIFECYCLES: "combat_rounds"})
        self.assertIn(SETTING_LIFECYCLES, message)

    def test_cf_15_a_non_string_or_empty_lifecycle_entry_is_refused(self):
        """CF-15"""
        message = self._refusal(**{SETTING_LIFECYCLES: ("combat_rounds", 3)})
        self.assertIn(SETTING_LIFECYCLES, message)
        message = self._refusal(**{SETTING_LIFECYCLES: ("combat_rounds", "")})
        self.assertIn(SETTING_LIFECYCLES, message)

    def test_cf_16_duplicate_lifecycle_names_are_refused(self):
        """CF-16"""
        message = self._refusal(
            **{SETTING_LIFECYCLES: ("combat_rounds", "combat_rounds")}
        )
        self.assertIn(SETTING_LIFECYCLES, message)

    def test_cf_17_the_reserved_wall_clock_name_is_refused(self):
        """CF-17"""
        message = self._refusal(**{SETTING_LIFECYCLES: ("combat_rounds", WALL_CLOCK)})
        self.assertIn(WALL_CLOCK, message)

    # ── the cross-checks ───────────────────────────────────────────── #

    def test_cf_18_an_effect_naming_an_undeclared_condition_is_refused(self):
        """CF-18"""
        message = self._refusal(
            **{SETTING_EFFECT_ENUM: "tests.spec_stubs.UndeclaredConditionEffects"}
        )
        self.assertIn("broken", message)
        self.assertIn("no_such_condition", message)

    def test_cf_19_an_effect_naming_an_undeclared_lifecycle_is_refused(self):
        """CF-19"""
        message = self._refusal(
            **{SETTING_EFFECT_ENUM: "tests.spec_stubs.UndeclaredLifecycleEffects"}
        )
        self.assertIn("broken", message)
        self.assertIn("no_such_lifecycle", message)

    def test_cf_20_the_wall_clock_lifecycle_needs_no_declaration(self):
        """CF-20"""
        # GoodEffects.INVISIBLE is on the wall clock, and the suite's
        # settings declare only the two countdown names. Making the
        # lifecycles truly absent proves the wall clock rides on nothing.
        with override_settings():
            from django.conf import settings

            delattr(settings, SETTING_LIFECYCLES)
            with override_settings(
                **{SETTING_CONDITION_ENUM: "tests.spec_stubs.GoodConditions"}
            ):
                # Only wall-clock and unmanaged effects may remain when no
                # countdown lifecycle is declared — STUNNED would now be
                # refused, which is CF-19's ground, so check the message
                # names only the countdown member.
                with self.assertRaises(ImproperlyConfigured) as caught:
                    check_settings()
                self.assertIn("stunned", str(caught.exception))
                self.assertNotIn("invisible", str(caught.exception))

    # ── logging and the accessors ──────────────────────────────────── #

    def test_cf_21_the_refusal_is_logged_at_error_with_the_same_text(self):
        """CF-21"""
        self._clear_logs()
        with override_settings(**{SETTING_CONDITION_ENUM: None}):
            with self.assertRaises(ImproperlyConfigured) as caught:
                check_settings()
        logged = self._read_back_logs()
        self.assertIn("[ERROR]", logged)
        self.assertIn(str(caught.exception), logged)

    def test_cf_22_the_accessors_return_the_resolved_values(self):
        """CF-22"""
        from tests.spec_stubs import GoodConditions, GoodEffects

        self.assertIs(get_condition_enum(), GoodConditions)
        self.assertIs(get_effect_enum(), GoodEffects)
        self.assertEqual(get_lifecycles(), ("combat_rounds", "fair_dances"))
        with override_settings():
            from django.conf import settings

            delattr(settings, SETTING_LIFECYCLES)
            self.assertEqual(get_lifecycles(), ())
