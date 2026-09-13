# SPDX-License-Identifier: BSD-3-Clause
"""A consumer module that fails on import — the negative fixture for CF-06.

Kept apart from spec_stubs.py so importing the good stubs never trips this.
The boot check must surface this error as the chained cause of its refusal
rather than swallowing it into "could not be loaded".
"""

raise RuntimeError("this consumer module is broken on purpose")
