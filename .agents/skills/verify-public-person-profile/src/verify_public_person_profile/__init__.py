"""
verify-public-person-profile: Evidence-grounded public person profile investigation and verification tool.
"""

import sys
from pathlib import Path

# Add package root to sys.path so core and models resolve smoothly
PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from core.run_profile import run_pipeline, main
from models.schemas import RootBundle, Dossier, Claim, Evidence, RunManifest

__version__ = "1.0.0"
__all__ = [
    "run_pipeline",
    "main",
    "RootBundle",
    "Dossier",
    "Claim",
    "Evidence",
    "RunManifest",
]
