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
from django.test import TestCase as DjangoTestCase

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
from evennia_effects_conditions.payloads import (
    UntypedEffectError,
    bucket_effects,
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
            "on_apply", "on_remove", "on_tick", "companion_script_key",
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


class ConditionsMixinTests(DjangoTestCase):
    """The conditions mixin — ref counting, messaging, the seam (CN)."""

    def setUp(self):
        from evennia.utils.create import create_object

        from tests.game_typeclasses import ConditionsObjectStub

        self.holder = create_object(ConditionsObjectStub, key="holder")

    def _conditions(self):
        from tests.spec_stubs import GoodConditions

        return GoodConditions

    # ── the counter ────────────────────────────────────────────────── #

    def test_cn_01_first_add_reports_the_transition_and_counts_one(self):
        """CN-01"""
        conds = self._conditions()
        self.assertTrue(self.holder.add_condition(conds.HIDDEN))
        self.assertTrue(self.holder.has_condition("hidden"))
        self.assertEqual(self.holder.get_condition_count(conds.HIDDEN), 1)
        # Member and raw string are the same condition.
        self.assertTrue(self.holder.has_condition(conds.HIDDEN))
        self.assertTrue(self.holder.remove_condition("hidden"))
        self.assertTrue(self.holder.add_condition("hidden"))
        self.assertEqual(self.holder.get_condition_count("hidden"), 1)

    def test_cn_02_a_second_add_increments_silently(self):
        """CN-02"""
        self.holder.add_condition("hidden")
        self.assertFalse(self.holder.add_condition("hidden"))
        self.assertEqual(self.holder.get_condition_count("hidden"), 2)
        self.assertTrue(self.holder.has_condition("hidden"))

    def test_cn_03_only_the_last_remove_reports_and_absent_removes_are_false(self):
        """CN-03"""
        self.holder.add_condition("hidden")
        self.holder.add_condition("hidden")
        self.assertFalse(self.holder.remove_condition("hidden"))
        self.assertEqual(self.holder.get_condition_count("hidden"), 1)
        self.assertTrue(self.holder.remove_condition("hidden"))
        self.assertFalse(self.holder.remove_condition("hidden"))
        self.assertEqual(self.holder.get_condition_count("hidden"), 0)

    def test_cn_04_an_unheld_condition_reads_back_inactive(self):
        """CN-04"""
        self.assertFalse(self.holder.has_condition("hidden"))
        self.assertEqual(self.holder.get_condition_count("hidden"), 0)

    # ── transition messaging ───────────────────────────────────────── #

    def _recording_holder(self):
        from evennia.utils.create import create_object

        from tests.game_typeclasses import RecordingBroadcastStub

        return create_object(RecordingBroadcastStub, key="recorder")

    def test_cn_05_the_first_add_delivers_start_messages_the_second_nothing(self):
        """CN-05"""
        holder = self._recording_holder()
        holder.add_condition("hidden")
        self.assertIn("You blend into the shadows.", holder.received)
        self.assertEqual(len(holder.broadcasts), 1)
        self.assertIn("melts into the shadows", holder.broadcasts[0])
        holder.add_condition("hidden")
        self.assertEqual(len(holder.received), 1)
        self.assertEqual(len(holder.broadcasts), 1)

    def test_cn_06_the_last_remove_delivers_end_messages_earlier_ones_nothing(self):
        """CN-06"""
        holder = self._recording_holder()
        holder.add_condition("hidden")
        holder.add_condition("hidden")
        holder.received.clear()
        holder.broadcasts.clear()
        holder.remove_condition("hidden")
        self.assertEqual(holder.received, [])
        self.assertEqual(holder.broadcasts, [])
        holder.remove_condition("hidden")
        self.assertIn("You step out of the shadows.", holder.received)
        self.assertEqual(len(holder.broadcasts), 1)
        self.assertIn("steps out of the shadows", holder.broadcasts[0])

    def test_cn_07_missing_messages_fall_back_and_empty_strings_are_silent(self):
        """CN-07"""
        holder = self._recording_holder()
        # DAZZLED declares no messages — the generated fallback names the key.
        holder.add_condition("dazzled")
        self.assertEqual(len(holder.received), 1)
        self.assertIn("dazzled", holder.received[0])
        self.assertEqual(len(holder.broadcasts), 1)
        self.assertIn("dazzled", holder.broadcasts[0])
        # MUTED declares every message as "" — deliberately silent.
        holder.received.clear()
        holder.broadcasts.clear()
        holder.add_condition("muted")
        holder.remove_condition("muted")
        self.assertEqual(holder.received, [])
        self.assertEqual(holder.broadcasts, [])

    # ── the broadcast seam ─────────────────────────────────────────── #

    def test_cn_08_the_default_broadcast_reaches_the_room_not_the_holder(self):
        """CN-08"""
        from evennia.utils.create import create_object

        # No location: the default seam no-ops rather than raising.
        self.holder.add_condition("hidden")
        self.holder.remove_condition("hidden")

        from evennia.objects.objects import DefaultRoom

        from tests.game_typeclasses import ConditionsObjectStub

        room = create_object(DefaultRoom, key="room")
        observer = create_object(ConditionsObjectStub, key="observer", location=room)
        self.holder.location = room
        self.holder.received.clear()
        self.holder.add_condition("hidden")
        third = [text for text in observer.received if text and "shadows" in text]
        self.assertEqual(len(third), 1)
        # {name} was formatted with the holder's key for the naive default.
        self.assertIn("holder", third[0])
        # The holder got only the first-person line.
        self.assertEqual(
            [text for text in self.holder.received if "melts" in (text or "")], []
        )

    def test_cn_09_a_broadcast_override_receives_the_template_unformatted(self):
        """CN-09"""
        holder = self._recording_holder()
        holder.add_condition("hidden")
        self.assertIn("{name}", holder.broadcasts[0])

    # ── refusal and persistence ────────────────────────────────────── #

    def test_cn_10_an_undeclared_key_is_refused_add_and_remove_alike(self):
        """CN-10"""
        with self.assertRaises(ValueError):
            self.holder.add_condition("no_such_condition")
        with self.assertRaises(ValueError):
            self.holder.remove_condition("no_such_condition")

    def test_cn_11_the_store_is_a_persisted_attribute_on_the_holder(self):
        """CN-11"""
        self.holder.add_condition("hidden")
        self.assertEqual(self.holder.attributes.get("conditions"), {"hidden": 1})
        pk = self.holder.pk
        self.holder.flush_from_cache()

        from evennia.objects.models import ObjectDB

        fresh = ObjectDB.objects.get(id=pk)
        self.assertEqual(dict(fresh.conditions), {"hidden": 1})


class EffectsMixinCoreTests(DjangoTestCase):
    """The effects mixin core — apply, remove, query, the hook (EF)."""

    def setUp(self):
        from evennia.utils.create import create_object

        from tests.game_typeclasses import EffectsObjectStub
        from tests.spec_stubs import CALLBACK_LOG

        self.holder = create_object(EffectsObjectStub, key="holder")
        CALLBACK_LOG.clear()

    def _effects(self):
        from tests.spec_stubs import GoodEffects

        return GoodEffects

    def _raising_holder(self):
        from evennia.utils.create import create_object

        from tests.game_typeclasses import RaisingHookStub

        return create_object(RaisingHookStub, key="raiser")

    # ── apply and the record ───────────────────────────────────────── #

    def test_ef_01_apply_records_the_effect_with_the_documented_fields(self):
        """EF-01"""
        effects = self._effects()
        self.assertTrue(self.holder.apply_named_effect(effects.BLESSED, duration=3))
        self.assertTrue(self.holder.has_effect("blessed"))
        self.assertTrue(self.holder.has_effect(effects.BLESSED))
        record = self.holder.get_named_effect("blessed")
        self.assertEqual(record["condition"], "glowing")
        self.assertEqual(record["effects"], [])
        self.assertEqual(record["duration"], 3)
        self.assertEqual(record["lifecycle"], "combat_rounds")
        self.assertEqual(record["extras"], {})
        self.assertEqual(record["messages"]["start_first"], "You are blessed!")
        # Raw string works everywhere the member does.
        self.holder.remove_named_effect("blessed")
        self.assertTrue(self.holder.apply_named_effect("blessed", duration=1))

    def test_ef_02_a_second_apply_anti_stacks_and_leaves_the_record_alone(self):
        """EF-02"""
        self.holder.apply_named_effect("blessed", duration=3)
        self.assertFalse(
            self.holder.apply_named_effect(
                "blessed", duration=99, effects=[{"x": 1}]
            )
        )
        record = self.holder.get_named_effect("blessed")
        self.assertEqual(record["duration"], 3)
        self.assertEqual(record["effects"], [])

    def test_ef_03_an_undeclared_effect_key_is_refused(self):
        """EF-03"""
        with self.assertRaises(ValueError):
            self.holder.apply_named_effect("no_such_effect")

    def test_ef_04_spec_auto_fill_explicit_none_and_explicit_override(self):
        """EF-04"""
        # Omitted → from the spec.
        self.holder.apply_named_effect("blessed", duration=1)
        self.assertTrue(self.holder.has_condition("glowing"))
        self.holder.remove_named_effect("blessed")
        # Explicit None → suppressed.
        self.holder.apply_named_effect("blessed", duration=1, condition=None)
        self.assertIsNone(self.holder.get_named_effect("blessed")["condition"])
        self.assertFalse(self.holder.has_condition("glowing"))
        self.holder.remove_named_effect("blessed")
        # Explicit value → overrides the spec.
        self.holder.apply_named_effect("blessed", duration=1, condition="hidden")
        self.assertTrue(self.holder.has_condition("hidden"))
        self.assertFalse(self.holder.has_condition("glowing"))

    def test_ef_05_an_effect_granted_condition_moves_silently(self):
        """EF-05"""
        self.holder.apply_named_effect("blessed", duration=1)
        self.assertEqual(self.holder.get_condition_count("glowing"), 1)
        for line in self.holder.received:
            self.assertNotIn("affected by glowing", line or "")

    def test_ef_06_the_payload_is_stored_verbatim(self):
        """EF-06"""
        payload = [{"weird": ["shape", 1]}, {"type": "custom", "n": 2.5}]
        self.holder.apply_named_effect("trapped", duration=2, effects=payload)
        self.assertEqual(
            list(self.holder.get_named_effect("trapped")["effects"]), payload
        )

    # ── the hook ───────────────────────────────────────────────────── #

    def test_ef_07_the_hook_fires_only_with_a_payload_and_after_the_store_changed(self):
        """EF-07"""
        self.holder.apply_named_effect("trapped", duration=2, effects=[{"x": 1}])
        self.assertEqual(len(self.holder.hook_calls), 1)
        self.assertIn("trapped", self.holder.hook_calls[0])
        # No payload — nothing the consumer's rebuild could see changed.
        self.holder.apply_named_effect("blessed", duration=1)
        self.assertEqual(len(self.holder.hook_calls), 1)
        # Removal mirrors: payload fires, no payload does not.
        self.holder.remove_named_effect("trapped")
        self.assertEqual(len(self.holder.hook_calls), 2)
        self.assertNotIn("trapped", self.holder.hook_calls[1])
        self.holder.remove_named_effect("blessed")
        self.assertEqual(len(self.holder.hook_calls), 2)

    def test_ef_08_a_raising_hook_unwinds_the_apply_and_propagates(self):
        """EF-08"""
        from tests.spec_stubs import CALLBACK_LOG

        holder = self._raising_holder()
        with self.assertRaises(RuntimeError):
            holder.apply_named_effect(
                "callbacked", effects=[{"x": 1}], condition="glowing",
            )
        self.assertFalse(holder.has_effect("callbacked"))
        self.assertIsNone(holder.get_named_effect("callbacked"))
        self.assertEqual(holder.get_condition_count("glowing"), 0)
        self.assertEqual(holder.received, [])
        self.assertEqual(holder.broadcasts, [])
        self.assertEqual(CALLBACK_LOG, [])

    # ── messages and extras ────────────────────────────────────────── #

    def test_ef_09_apply_delivers_start_messages_and_anti_stacking_is_silent(self):
        """EF-09"""
        self.holder.apply_named_effect("blessed", duration=1)
        self.assertIn("You are blessed!", self.holder.received)
        self.assertIn("{name} glows.", self.holder.broadcasts)
        self.holder.received.clear()
        self.holder.broadcasts.clear()
        self.holder.apply_named_effect("blessed", duration=1)
        self.assertEqual(self.holder.received, [])
        self.assertEqual(self.holder.broadcasts, [])

    def test_ef_10_message_overrides_merge_and_survive_to_removal(self):
        """EF-10"""
        self.holder.apply_named_effect(
            "blessed", duration=1, messages={"start_first": "CUSTOM start"}
        )
        self.assertIn("CUSTOM start", self.holder.received)
        self.assertNotIn("You are blessed!", self.holder.received)
        self.assertIn("{name} glows.", self.holder.broadcasts)
        self.holder.received.clear()
        self.holder.remove_named_effect("blessed")
        self.assertIn("The blessing fades.", self.holder.received)
        # An empty-string override silences that key alone.
        self.holder.received.clear()
        self.holder.broadcasts.clear()
        self.holder.apply_named_effect(
            "blessed", duration=1, messages={"start_third": ""}
        )
        self.assertIn("You are blessed!", self.holder.received)
        self.assertEqual(self.holder.broadcasts, [])

    def test_ef_11_record_extras_merge_spec_and_per_application(self):
        """EF-11"""
        self.holder.apply_named_effect(
            "trapped", duration=2, extras={"save_dc": 20, "note": "x"}
        )
        self.assertEqual(
            self.holder.get_named_effect("trapped")["extras"],
            {"save_dc": 20, "note": "x"},
        )
        self.holder.remove_named_effect("trapped")
        self.holder.apply_named_effect("trapped", duration=2)
        self.assertEqual(
            self.holder.get_named_effect("trapped")["extras"], {"save_dc": 12}
        )

    # ── the callbacks ──────────────────────────────────────────────── #

    def test_ef_12_on_apply_fires_last_with_the_source_which_is_not_stored(self):
        """EF-12"""
        from evennia.utils.create import create_object

        from tests.game_typeclasses import EffectsObjectStub
        from tests.spec_stubs import CALLBACK_LOG

        source = create_object(EffectsObjectStub, key="source")
        self.holder.apply_named_effect("callbacked", source=source, duration=4)
        self.assertEqual(CALLBACK_LOG, [("on_apply", self.holder, source, 4)])
        self.assertNotIn("source", self.holder.get_named_effect("callbacked"))

    def test_ef_13_removal_reverses_everything_and_hands_on_remove_the_record(self):
        """EF-13"""
        from tests.spec_stubs import CALLBACK_LOG

        self.holder.apply_named_effect("blessed", duration=2)
        self.holder.add_condition("glowing")  # a second, bare grant
        self.holder.received.clear()
        self.assertTrue(self.holder.remove_named_effect("blessed"))
        self.assertFalse(self.holder.has_effect("blessed"))
        self.assertIn("The blessing fades.", self.holder.received)
        # Decremented, not zeroed — the bare grant survives.
        self.assertEqual(self.holder.get_condition_count("glowing"), 1)

        self.holder.apply_named_effect("callbacked", duration=7)
        CALLBACK_LOG.clear()
        self.holder.remove_named_effect("callbacked")
        self.assertEqual(len(CALLBACK_LOG), 1)
        name, target, record = CALLBACK_LOG[0]
        self.assertEqual(name, "on_remove")
        self.assertEqual(target, self.holder)
        self.assertEqual(record["duration"], 7)

    def test_ef_14_removing_an_absent_effect_is_false_and_silent(self):
        """EF-14"""
        self.assertFalse(self.holder.remove_named_effect("blessed"))
        self.assertEqual(self.holder.received, [])
        self.assertEqual(self.holder.hook_calls, [])

    # ── queries, coexistence, persistence ──────────────────────────── #

    def test_ef_15_first_active_effect_returns_the_first_active_in_order(self):
        """EF-15"""
        effects = self._effects()
        self.holder.apply_named_effect("blessed", duration=1)
        self.holder.apply_named_effect("trapped", duration=1)
        self.assertEqual(
            self.holder.first_active_effect(["stunned", "trapped", "blessed"]),
            "trapped",
        )
        self.assertEqual(
            self.holder.first_active_effect([effects.STUNNED, effects.BLESSED]),
            "blessed",
        )
        self.assertIsNone(self.holder.first_active_effect(["stunned"]))

    def test_ef_16_an_undeclared_explicit_condition_is_refused(self):
        """EF-16"""
        with self.assertRaises(ValueError):
            self.holder.apply_named_effect(
                "blessed", duration=1, condition="no_such_condition"
            )
        self.assertFalse(self.holder.has_effect("blessed"))

    def test_ef_17_two_effects_coexist_and_one_removal_leaves_the_other(self):
        """EF-17"""
        self.holder.apply_named_effect("blessed", duration=1)
        self.holder.apply_named_effect("trapped", duration=2, effects=[{"x": 1}])
        self.holder.remove_named_effect("trapped")
        self.assertTrue(self.holder.has_effect("blessed"))
        self.assertTrue(self.holder.has_condition("glowing"))

    def test_ef_18_duration_and_lifecycle_are_stored_as_given(self):
        """EF-18"""
        self.holder.apply_named_effect("trapped", duration=4)
        self.assertEqual(self.holder.get_named_effect("trapped")["duration"], 4)
        self.holder.apply_named_effect("blessed", duration=None)
        record = self.holder.get_named_effect("blessed")
        self.assertIsNone(record["duration"])
        self.assertEqual(record["lifecycle"], "combat_rounds")

    def test_ef_19_the_record_store_is_a_persisted_attribute(self):
        """EF-19"""
        self.holder.apply_named_effect("trapped", duration=2)
        pk = self.holder.pk
        self.holder.flush_from_cache()

        from evennia.objects.models import ObjectDB

        fresh = ObjectDB.objects.get(id=pk)
        self.assertIn("trapped", fresh.active_effects)

    # ── on_active: what a second apply does ────────────────────────── #

    def test_ef_20_reset_replaces_the_remaining_duration(self):
        """EF-20"""
        effects = self._effects()
        self.holder.apply_named_effect(effects.STUNNED, duration=10)
        self.holder.advance_effects("combat_rounds")
        self.assertEqual(self.holder.get_named_effect("stunned")["duration"], 9)

        applied = self.holder.apply_named_effect(
            effects.STUNNED, duration=10, on_active="reset"
        )
        self.assertTrue(applied)
        self.assertEqual(self.holder.get_named_effect("stunned")["duration"], 10)

    def test_ef_21_extend_adds_to_what_remains(self):
        """EF-21"""
        effects = self._effects()
        self.holder.apply_named_effect(effects.STUNNED, duration=10)
        self.holder.advance_effects("combat_rounds")

        applied = self.holder.apply_named_effect(
            effects.STUNNED, duration=10, on_active="extend"
        )
        self.assertTrue(applied)
        self.assertEqual(self.holder.get_named_effect("stunned")["duration"], 19)

    def test_ef_22_max_duration_clips_extend_and_reset_ignores_it(self):
        """EF-22"""
        effects = self._effects()
        self.holder.apply_named_effect(effects.STUNNED, duration=10)
        self.holder.apply_named_effect(
            effects.STUNNED, duration=10, on_active="extend", max_duration=15
        )
        self.assertEqual(self.holder.get_named_effect("stunned")["duration"], 15)

        # Reset is bounded by what it applies, so the ceiling means nothing.
        self.holder.apply_named_effect(
            effects.STUNNED, duration=30, on_active="reset", max_duration=15
        )
        self.assertEqual(self.holder.get_named_effect("stunned")["duration"], 30)

    def test_ef_23_readjusting_is_silent_and_does_not_fire_on_apply(self):
        """EF-23"""
        from tests.spec_stubs import CALLBACK_LOG

        effects = self._effects()
        self.holder.apply_named_effect(effects.CALLBACKED, duration=5)
        self.holder.received.clear()
        CALLBACK_LOG.clear()

        for mode in ("reset", "extend"):
            self.holder.apply_named_effect(
                effects.CALLBACKED, duration=5, on_active=mode
            )
        self.assertEqual(self.holder.received, [])
        self.assertEqual(
            [entry for entry in CALLBACK_LOG if entry[0] == "on_apply"], []
        )

    def test_ef_24_readjusting_leaves_the_condition_ref_alone(self):
        """EF-24"""
        effects = self._effects()
        self.holder.apply_named_effect(effects.BLESSED, duration=5)
        self.assertEqual(self.holder.get_condition_count("glowing"), 1)

        self.holder.apply_named_effect(
            effects.BLESSED, duration=5, on_active="reset"
        )
        self.holder.apply_named_effect(
            effects.BLESSED, duration=5, on_active="extend"
        )
        self.assertEqual(self.holder.get_condition_count("glowing"), 1)
        self.assertTrue(self.holder.has_condition("glowing"))

    def test_ef_25_extras_merge_into_the_standing_record(self):
        """EF-25"""
        effects = self._effects()
        self.holder.apply_named_effect(
            effects.TRAPPED, duration=5, extras={"damage": 1}
        )
        self.holder.apply_named_effect(
            effects.TRAPPED, duration=5, on_active="reset",
            extras={"damage": 4},
        )
        extras = self.holder.get_named_effect("trapped")["extras"]
        self.assertEqual(extras["damage"], 4)
        # The spec's own extras survive — a merge, not a replacement.
        self.assertEqual(extras["save_dc"], 12)

    def test_ef_26_readjusting_reschedules_the_wall_clock_timer(self):
        """EF-26"""
        effects = self._effects()
        self.holder.apply_named_effect(effects.INVISIBLE, duration=60)
        self.holder.apply_named_effect(
            effects.INVISIBLE, duration=300, on_active="reset"
        )
        self.assertEqual(
            self.holder.get_named_effect("invisible")["duration"], 300
        )
        remaining = self.holder.get_effect_remaining_seconds("invisible")
        self.assertIsNotNone(remaining)
        self.assertLessEqual(remaining, 300)
        self.assertGreater(remaining, 60)

    def test_ef_27_readjusting_an_inactive_effect_is_a_normal_apply(self):
        """EF-27"""
        effects = self._effects()
        applied = self.holder.apply_named_effect(
            effects.BLESSED, duration=5, on_active="reset"
        )
        self.assertTrue(applied)
        self.assertTrue(self.holder.has_effect("blessed"))
        self.assertIn("You are blessed!", self.holder.received)
        self.assertEqual(self.holder.get_condition_count("glowing"), 1)

    def test_ef_28_an_unknown_on_active_is_refused(self):
        """EF-28"""
        effects = self._effects()
        with self.assertRaises(ValueError):
            self.holder.apply_named_effect(
                effects.STUNNED, duration=5, on_active="refresh"
            )
        self.holder.apply_named_effect(effects.STUNNED, duration=5)
        with self.assertRaises(ValueError):
            self.holder.apply_named_effect(
                effects.STUNNED, duration=5, on_active="refresh"
            )

    def test_ef_29_readjusting_against_a_permanent_record(self):
        """EF-29"""
        effects = self._effects()
        # Reset gives a permanent a duration; extend leaves it permanent.
        self.holder.apply_named_effect(effects.STUNNED, duration=None)
        self.holder.apply_named_effect(
            effects.STUNNED, duration=8, on_active="extend"
        )
        self.assertIsNone(self.holder.get_named_effect("stunned")["duration"])
        self.holder.apply_named_effect(
            effects.STUNNED, duration=8, on_active="reset"
        )
        self.assertEqual(self.holder.get_named_effect("stunned")["duration"], 8)

        # Resetting a timed wall-clock record to None makes it permanent and
        # stops its timer.
        self.holder.apply_named_effect(effects.INVISIBLE, duration=60)
        self.holder.apply_named_effect(
            effects.INVISIBLE, duration=None, on_active="reset"
        )
        self.assertIsNone(self.holder.get_named_effect("invisible")["duration"])
        self.assertIsNone(
            self.holder.get_effect_remaining_seconds("invisible")
        )


class LifecycleTests(DjangoTestCase):
    """Lifecycles — advancing, clearing, the wall-clock timer (LC)."""

    def setUp(self):
        from evennia.utils.create import create_object

        from tests.game_typeclasses import EffectsObjectStub
        from tests.spec_stubs import CALLBACK_LOG, ESCAPE_RETURN

        self.holder = create_object(EffectsObjectStub, key="holder")
        CALLBACK_LOG.clear()
        ESCAPE_RETURN["value"] = False

    # ── advancing ──────────────────────────────────────────────────── #

    def test_lc_01_advance_touches_only_its_own_lifecycle(self):
        """LC-01"""
        self.holder.apply_named_effect("stunned", duration=3)
        self.holder.apply_named_effect("danced", duration=3)
        self.holder.apply_named_effect("invisible", duration=300)
        self.holder.apply_named_effect("poisoned", duration=5)
        self.holder.advance_effects("combat_rounds")
        self.assertEqual(self.holder.get_named_effect("stunned")["duration"], 2)
        self.assertEqual(self.holder.get_named_effect("danced")["duration"], 3)
        self.assertEqual(self.holder.get_named_effect("invisible")["duration"], 300)
        self.assertEqual(self.holder.get_named_effect("poisoned")["duration"], 5)

    def test_lc_02_expiry_is_a_normal_removal(self):
        """LC-02"""
        self.holder.apply_named_effect("blessed", duration=1)
        self.holder.received.clear()
        ended = self.holder.advance_effects("combat_rounds")
        self.assertEqual(ended, ["blessed"])
        self.assertFalse(self.holder.has_effect("blessed"))
        self.assertIn("The blessing fades.", self.holder.received)
        self.assertEqual(self.holder.get_condition_count("glowing"), 0)

    def test_lc_03_the_return_names_exactly_what_ended(self):
        """LC-03"""
        self.holder.apply_named_effect("stunned", duration=2)
        self.holder.apply_named_effect("blessed", duration=1)
        ended = self.holder.advance_effects("combat_rounds")
        self.assertEqual(ended, ["blessed"])
        self.assertTrue(self.holder.has_effect("stunned"))

    def test_lc_04_a_permanent_record_survives_every_advance(self):
        """LC-04"""
        self.holder.apply_named_effect("blessed", duration=None)
        self.holder.advance_effects("combat_rounds")
        self.holder.advance_effects("combat_rounds")
        self.assertTrue(self.holder.has_effect("blessed"))
        self.assertIsNone(self.holder.get_named_effect("blessed")["duration"])

    # ── the tick hook ─────────────────────────────────────────────── #

    def test_lc_05_a_true_tick_ends_the_effect_without_a_decrement(self):
        """LC-05"""
        from tests.spec_stubs import CALLBACK_LOG, ESCAPE_RETURN

        ESCAPE_RETURN["value"] = True
        self.holder.apply_named_effect("escapable", duration=4)
        ended = self.holder.advance_effects("combat_rounds")
        self.assertEqual(ended, ["escapable"])
        self.assertFalse(self.holder.has_effect("escapable"))
        removals = [entry for entry in CALLBACK_LOG if entry[0] == "on_remove"]
        self.assertEqual(len(removals), 1)
        # Ended at its full remaining duration — no decrement first.
        self.assertEqual(removals[0][2]["duration"], 4)

    def test_lc_06_a_false_tick_leaves_the_normal_decrement(self):
        """LC-06"""
        from tests.spec_stubs import CALLBACK_LOG

        self.holder.apply_named_effect("escapable", duration=3)
        self.holder.advance_effects("combat_rounds")
        self.assertEqual(self.holder.get_named_effect("escapable")["duration"], 2)
        ticks = [entry for entry in CALLBACK_LOG if entry[0] == "tick"]
        self.assertEqual(len(ticks), 1)
        self.assertEqual(ticks[0][1], self.holder)
        self.assertEqual(ticks[0][2]["duration"], 3)
        self.holder.advance_effects("combat_rounds")
        ticks = [entry for entry in CALLBACK_LOG if entry[0] == "tick"]
        self.assertEqual(len(ticks), 2)

    def test_lc_07_the_tick_hook_runs_for_permanent_records(self):
        """LC-07"""
        from tests.spec_stubs import CALLBACK_LOG, ESCAPE_RETURN

        # Falsy: it ticks, and survives with no duration to count down.
        ESCAPE_RETURN["value"] = False
        self.holder.apply_named_effect("escapable", duration=None)
        self.holder.advance_effects("combat_rounds")
        ticks = [entry for entry in CALLBACK_LOG if entry[0] == "tick"]
        self.assertEqual(len(ticks), 1)
        self.assertEqual(ticks[0][1], self.holder)
        self.assertIsNone(ticks[0][2]["duration"])
        self.assertTrue(self.holder.has_effect("escapable"))

        # Ticks again — nothing about it wears down.
        self.holder.advance_effects("combat_rounds")
        self.assertEqual(
            len([entry for entry in CALLBACK_LOG if entry[0] == "tick"]), 2
        )
        self.assertTrue(self.holder.has_effect("escapable"))

        # Truthy ends it, which is what makes "permanent until you escape"
        # expressible without standing a large number in for infinity.
        ESCAPE_RETURN["value"] = True
        ended = self.holder.advance_effects("combat_rounds")
        self.assertEqual(ended, ["escapable"])
        self.assertFalse(self.holder.has_effect("escapable"))

    # ── refusals and clearing ──────────────────────────────────────── #

    def test_lc_08_advance_refuses_the_wall_clock_and_undeclared_names(self):
        """LC-08"""
        with self.assertRaises(ValueError):
            self.holder.advance_effects(WALL_CLOCK)
        with self.assertRaises(ValueError):
            self.holder.advance_effects("no_such_lifecycle")

    def test_lc_09_clear_removes_everything_on_one_lifecycle(self):
        """LC-09"""
        self.holder.apply_named_effect("stunned", duration=2)
        self.holder.apply_named_effect("blessed", duration=None)
        self.holder.apply_named_effect("danced", duration=1)
        self.holder.received.clear()
        cleared = self.holder.clear_effects("combat_rounds")
        self.assertEqual(set(cleared), {"stunned", "blessed"})
        self.assertFalse(self.holder.has_effect("stunned"))
        self.assertFalse(self.holder.has_effect("blessed"))
        self.assertTrue(self.holder.has_effect("danced"))
        self.assertIn("The blessing fades.", self.holder.received)

    # ── the wall clock ─────────────────────────────────────────────── #

    def test_lc_10_a_wall_clock_apply_creates_the_one_shot_timer(self):
        """LC-10"""
        self.holder.apply_named_effect("invisible", duration=300)
        scripts = self.holder.scripts.get("effect_timer_invisible")
        self.assertEqual(len(scripts), 1)
        script = scripts[0]
        self.assertEqual(script.interval, 300)
        self.assertEqual(script.effect_key, "invisible")
        # Firing it is exactly what the reactor would do on expiry.
        script.at_repeat()
        self.assertFalse(self.holder.has_effect("invisible"))
        self.assertFalse(self.holder.has_condition("hidden"))

    def test_lc_11_removal_stops_and_deletes_the_timer(self):
        """LC-11"""
        self.holder.apply_named_effect("invisible", duration=300)
        self.holder.remove_named_effect("invisible")
        self.assertFalse(self.holder.scripts.get("effect_timer_invisible"))

    def test_lc_12_remaining_seconds_counts_down_for_the_wall_clock_only(self):
        """LC-12"""
        self.holder.apply_named_effect("invisible", duration=300)
        remaining = self.holder.get_effect_remaining_seconds("invisible")
        self.assertIsNotNone(remaining)
        self.assertGreater(remaining, 299)
        self.assertLessEqual(remaining, 300)
        self.holder.apply_named_effect("stunned", duration=3)
        self.assertIsNone(self.holder.get_effect_remaining_seconds("stunned"))
        self.assertIsNone(self.holder.get_effect_remaining_seconds("blessed"))

    def test_lc_13_a_wall_clock_apply_with_no_duration_starts_no_timer(self):
        """LC-13"""
        self.holder.apply_named_effect("invisible", duration=None)
        self.assertFalse(self.holder.scripts.get("effect_timer_invisible"))
        self.assertTrue(self.holder.has_effect("invisible"))


class BreakVerbTests(DjangoTestCase):
    """The break verbs — forced, silent removal (BK)."""

    def setUp(self):
        from evennia.utils.create import create_object

        from tests.game_typeclasses import EffectsObjectStub
        from tests.spec_stubs import CALLBACK_LOG

        self.holder = create_object(EffectsObjectStub, key="holder")
        CALLBACK_LOG.clear()

    def test_bk_01_break_zeroes_a_multi_source_condition(self):
        """BK-01"""
        self.holder.apply_named_effect("invisible", duration=None)
        self.holder.add_condition("hidden")
        self.holder.add_condition("hidden")
        self.assertEqual(self.holder.get_condition_count("hidden"), 3)
        self.assertTrue(self.holder.break_effect("invisible"))
        self.assertEqual(self.holder.get_condition_count("hidden"), 0)
        self.assertFalse(self.holder.has_effect("invisible"))

    def test_bk_02_break_is_silent_and_total(self):
        """BK-02"""
        self.holder.apply_named_effect("invisible", duration=None)
        self.holder.received.clear()
        self.holder.broadcasts.clear()
        self.assertTrue(self.holder.break_effect("invisible"))
        self.assertEqual(self.holder.received, [])
        self.assertEqual(self.holder.broadcasts, [])
        self.assertIsNone(self.holder.get_named_effect("invisible"))
        self.assertEqual(self.holder.get_condition_count("hidden"), 0)

    def test_bk_03_break_stops_the_wall_clock_timer(self):
        """BK-03"""
        self.holder.apply_named_effect("invisible", duration=300)
        self.holder.break_effect("invisible")
        self.assertFalse(self.holder.scripts.get("effect_timer_invisible"))

    def test_bk_04_break_fires_the_hook_and_never_on_remove(self):
        """BK-04"""
        from tests.spec_stubs import CALLBACK_LOG

        self.holder.apply_named_effect("trapped", duration=2, effects=[{"x": 1}])
        hook_count = len(self.holder.hook_calls)
        self.holder.break_effect("trapped")
        self.assertEqual(len(self.holder.hook_calls), hook_count + 1)
        self.holder.apply_named_effect("callbacked")
        CALLBACK_LOG.clear()
        self.holder.break_effect("callbacked")
        self.assertEqual(
            [entry for entry in CALLBACK_LOG if entry[0] == "on_remove"], []
        )

    def test_bk_05_condition_first_activity_in_both_directions(self):
        """BK-05"""
        # A bare condition breaks through its effect's key, record or none.
        self.holder.add_condition("glowing")
        self.assertTrue(self.holder.break_effect("blessed"))
        self.assertEqual(self.holder.get_condition_count("glowing"), 0)
        # A record whose condition was independently zeroed reports False
        # and stays — the no-reconciliation limit, live.
        self.holder.apply_named_effect("blessed", duration=2)
        self.holder.break_effects(("glowing",))
        self.assertFalse(self.holder.break_effect("blessed"))
        self.assertTrue(self.holder.has_effect("blessed"))

    def test_bk_06_inactive_is_false_and_undeclared_is_refused(self):
        """BK-06"""
        self.assertFalse(self.holder.break_effect("blessed"))
        with self.assertRaises(ValueError):
            self.holder.break_effect("no_such_effect")

    def test_bk_07_break_effects_breaks_the_set_and_reports_in_order(self):
        """BK-07"""
        from tests.spec_stubs import GoodConditions, GoodEffects

        self.holder.apply_named_effect("blessed", duration=2)
        self.holder.add_condition("hidden")
        broken = self.holder.break_effects(
            (GoodEffects.BLESSED, "hidden", "stunned", GoodConditions.MUTED)
        )
        self.assertEqual(broken, ["blessed", "hidden"])
        self.assertFalse(self.holder.has_effect("blessed"))
        self.assertFalse(self.holder.has_condition("hidden"))
        # excluded is honoured.
        self.holder.apply_named_effect("blessed", duration=2)
        self.holder.add_condition("hidden")
        broken = self.holder.break_effects(
            ("blessed", "hidden"), excluded=("hidden",)
        )
        self.assertEqual(broken, ["blessed"])
        self.assertTrue(self.holder.has_condition("hidden"))
        # A key declared in neither catalogue is a typo.
        with self.assertRaises(ValueError):
            self.holder.break_effects(("no_such_key",))

    def test_bk_08_the_bare_condition_fallback_zeroes_silently(self):
        """BK-08"""
        self.holder.add_condition("hidden")
        self.holder.add_condition("hidden")
        self.holder.received.clear()
        self.holder.broadcasts.clear()
        broken = self.holder.break_effects(("hidden",))
        self.assertEqual(broken, ["hidden"])
        self.assertEqual(self.holder.get_condition_count("hidden"), 0)
        self.assertEqual(self.holder.received, [])
        self.assertEqual(self.holder.broadcasts, [])


class ClearAllTests(DjangoTestCase):
    """clear_all_effects() — the silent full strip (CL)."""

    def setUp(self):
        from evennia.utils.create import create_object, create_script

        from evennia_effects_conditions.scripts import EffectsTimerScript
        from tests.game_typeclasses import EffectsObjectStub
        from tests.spec_stubs import CALLBACK_LOG

        self.holder = create_object(EffectsObjectStub, key="holder")
        CALLBACK_LOG.clear()
        # One of every lifecycle shape, plus a bare condition grant.
        self.holder.apply_named_effect("stunned", duration=2)
        self.holder.apply_named_effect(
            "blessed", duration=None, effects=[{"x": 1}]
        )
        self.holder.apply_named_effect("invisible", duration=300)
        self.holder.apply_named_effect("poisoned", duration=5)
        self.holder.apply_named_effect("callbacked")
        self.holder.apply_named_effect("scripted")
        create_script(
            EffectsTimerScript, obj=self.holder, key="companion_stub",
            autostart=False,
        )
        self.holder.add_condition("glowing")  # bare, beside blessed's grant

    def test_cl_01_every_record_goes_and_the_keys_come_back(self):
        """CL-01"""
        stripped = self.holder.clear_all_effects()
        self.assertEqual(
            set(stripped),
            {"stunned", "blessed", "invisible", "poisoned", "callbacked", "scripted"},
        )
        for key in stripped:
            self.assertFalse(self.holder.has_effect(key))

    def test_cl_02_the_strip_is_silent(self):
        """CL-02"""
        self.holder.received.clear()
        self.holder.broadcasts.clear()
        self.holder.clear_all_effects()
        self.assertEqual(self.holder.received, [])
        self.assertEqual(self.holder.broadcasts, [])

    def test_cl_03_record_refs_decrement_and_bare_grants_survive(self):
        """CL-03"""
        self.assertEqual(self.holder.get_condition_count("glowing"), 2)
        self.assertEqual(self.holder.get_condition_count("hidden"), 1)
        self.holder.clear_all_effects()
        self.assertEqual(self.holder.get_condition_count("glowing"), 1)
        self.assertEqual(self.holder.get_condition_count("hidden"), 0)

    def test_cl_04_timers_and_companion_scripts_are_stopped(self):
        """CL-04"""
        self.assertTrue(self.holder.scripts.get("effect_timer_invisible"))
        self.assertTrue(self.holder.scripts.get("companion_stub"))
        self.holder.clear_all_effects()
        self.assertFalse(self.holder.scripts.get("effect_timer_invisible"))
        self.assertFalse(self.holder.scripts.get("companion_stub"))

    def test_cl_05_one_hook_call_and_no_on_remove(self):
        """CL-05"""
        from tests.spec_stubs import CALLBACK_LOG

        hook_count = len(self.holder.hook_calls)
        CALLBACK_LOG.clear()
        self.holder.clear_all_effects()
        self.assertEqual(len(self.holder.hook_calls), hook_count + 1)
        self.assertEqual(
            [entry for entry in CALLBACK_LOG if entry[0] == "on_remove"], []
        )


class BucketEffectsTests(TestCase):
    """PB — grouping a store's payloads by their type."""

    def test_pb_01_an_empty_store_gives_an_empty_dict(self):
        """PB-01"""
        self.assertEqual(bucket_effects({}), {})
        self.assertEqual(bucket_effects(None), {})

    def test_pb_02_a_payload_lands_under_its_type(self):
        """PB-02"""
        payload = {"type": "stat_bonus", "stat": "strength", "value": 1}

        self.assertEqual(
            bucket_effects({"ring": {"effects": [payload]}}),
            {"stat_bonus": [payload]},
        )

    def test_pb_03_payloads_of_one_type_collect_in_order(self):
        """PB-03"""
        # A caller totalling per type needs the same answer every call. Which
        # order records come out of the store is the store's business; two
        # payloads inside one record must not be reordered.
        first = {"type": "stat_bonus", "stat": "strength", "value": 1}
        second = {"type": "stat_bonus", "stat": "wisdom", "value": 2}

        buckets = bucket_effects({"ring": {"effects": [first, second]}})

        self.assertEqual(buckets["stat_bonus"], [first, second])

    def test_pb_04_different_types_are_held_apart(self):
        """PB-04"""
        stat = {"type": "stat_bonus", "stat": "strength", "value": 1}
        size = {"type": "size_shift", "value": 1}

        buckets = bucket_effects({"spell": {"effects": [stat, size]}})

        self.assertEqual(buckets, {"stat_bonus": [stat], "size_shift": [size]})

    def test_pb_05_payloads_are_gathered_across_records(self):
        """PB-05"""
        ring = {"type": "stat_bonus", "stat": "strength", "value": 1}
        spell = {"type": "stat_bonus", "stat": "strength", "value": 2}

        buckets = bucket_effects(
            {
                "ring": {"effects": [ring]},
                "spell": {"effects": [spell]},
            }
        )

        self.assertCountEqual(buckets["stat_bonus"], [ring, spell])

    def test_pb_06_a_record_without_payloads_contributes_nothing(self):
        """PB-06"""
        # A condition with no payload is the ordinary case, not an error.
        self.assertEqual(
            bucket_effects(
                {
                    "stunned": {"condition": "stunned"},
                    "blinded": {"effects": []},
                }
            ),
            {},
        )

    def test_pb_07_a_payload_with_no_type_raises(self):
        """PB-07"""
        for payload in ({"value": 1}, {"type": "", "value": 1},
                        {"type": None, "value": 1}):
            with self.subTest(payload):
                with self.assertRaises(UntypedEffectError) as caught:
                    bucket_effects({"mystery": {"effects": [payload]}})

                # The record key, or you know a payload is broken without
                # knowing which of twenty records holds it.
                self.assertIn("mystery", str(caught.exception))

    def test_pb_08_a_payload_that_is_not_a_mapping_raises(self):
        """PB-08"""
        for payload in ("stat_bonus", 7, ["stat_bonus", 1], None):
            with self.subTest(payload):
                with self.assertRaises(UntypedEffectError) as caught:
                    bucket_effects({"mystery": {"effects": [payload]}})

                self.assertIn("mystery", str(caught.exception))

    def test_pb_09_the_returned_dict_is_plain(self):
        """PB-09"""
        # Several receivers read one bucket dict during a dispatch. A
        # defaultdict would have each miss insert an empty list while the
        # others are still reading it.
        buckets = bucket_effects(
            {"ring": {"effects": [{"type": "stat_bonus", "value": 1}]}}
        )

        self.assertIs(type(buckets), dict)
        with self.assertRaises(KeyError):
            buckets["size_shift"]
        self.assertNotIn("size_shift", buckets)

    def test_pb_10_the_payloads_are_the_stored_objects(self):
        """PB-10"""
        # Nothing is copied. Copying every payload on every rebuild to guard
        # against a caller that mutates one would cost more than it saves.
        payload = {"type": "stat_bonus", "stat": "strength", "value": 1}

        buckets = bucket_effects({"ring": {"effects": [payload]}})

        self.assertIs(buckets["stat_bonus"][0], payload)
