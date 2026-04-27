#!/usr/bin/env python3
"""Compatibility wrapper for the installable ISBD postprocessor.

Prefer the console command installed by setup.py:

    iridium-sbd-postprocess /path/to/data/inbox/message.isbd
"""

from iridiumSBD.processing.postprocess_isbd import main

if __name__ == "__main__":
    raise SystemExit(main())
