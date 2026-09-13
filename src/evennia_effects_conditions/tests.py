# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for evennia-effects-conditions, run via ``python runtests.py``.

Every case the library commits to lives in docs/test-plan.md, and every test
function here carries its case ID as its docstring so the trail reads both ways.
"""

import dataclasses
from unittest import TestCase

import evennia_effects_conditions
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
