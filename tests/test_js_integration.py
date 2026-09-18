import subprocess
import os
import sys
from pathlib import Path

def test_js_integration_suite():
    """Run the JavaScript browser integration tests as part of the pytest suite."""
    base_dir = Path(__file__).resolve().parent.parent
    runner_script = base_dir / "run_tests.py"

    result = subprocess.run(
        [sys.executable, str(runner_script)],
        cwd=str(base_dir),
        capture_output=True,
        text=True
    )

    # Print output for pytest logs
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    assert result.returncode == 0, f"JS Integration tests failed! Output:\n{result.stdout}\n{result.stderr}"
