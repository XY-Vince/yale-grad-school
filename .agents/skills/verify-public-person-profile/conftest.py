"""pytest root configuration for verify-public-person-profile.

Ensures the skill root is in sys.path so tests can be run from any working directory
without requiring manual PYTHONPATH manipulation.
"""

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))
