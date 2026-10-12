#!/usr/bin/env python3
"""CLI wrapper for functional acceptance runner."""

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from benchmarks.tools.functional_acceptance_runner import main

if __name__ == "__main__":
    main()
