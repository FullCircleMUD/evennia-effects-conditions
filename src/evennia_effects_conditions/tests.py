# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for evennia-effects-conditions, run via ``python runtests.py``.

Every case the library commits to lives in docs/test-plan.md, and every test
function here carries its case ID as its docstring so the trail reads both ways.
"""

from unittest import TestCase

import evennia_effects_conditions


class ScaffoldTests(TestCase):
    """The install and the test runner work end to end."""

    def test_sc_01_package_imports_and_reports_its_version(self):
        """SC-01"""
        self.assertEqual(evennia_effects_conditions.__version__, "0.0.1")
