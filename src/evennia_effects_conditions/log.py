# SPDX-License-Identifier: BSD-3-Clause
"""Logging shim for evennia-effects-conditions.

Every line the library emits goes to its own ``effects-conditions.log`` under
``settings.LOG_DIR``. The mechanism belongs to ``evennia-logging-extension``;
this file names the file and nothing else.

Internal to the library, not part of the consumer-facing API.
"""

from evennia_logging_extension import make_logger

effects_conditions_log = make_logger("effects-conditions.log")
