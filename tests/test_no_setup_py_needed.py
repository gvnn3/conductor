"""Test that the package works without setup.py."""

import subprocess
import sys
from pathlib import Path


class TestNoSetupPyNeeded:
    """Test that setup.py is not required for modern packaging."""

    def test_install_without_setup_py(self, tmp_path):
        """Test that package can be installed without setup.py."""
        project_root = Path(__file__).parent.parent

        # Temporarily rename setup.py if it exists
        setup_py = project_root / "setup.py"
        setup_py_backup = None

        if setup_py.exists():
            setup_py_backup = project_root / "setup.py.backup"
            setup_py.rename(setup_py_backup)

        try:
            # Try to install with pip
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--dry-run",
                    str(project_root),
                ],
                capture_output=True,
                text=True,
            )

            # Should succeed without setup.py
            assert result.returncode == 0, (
                f"Install failed without setup.py: {result.stderr}"
            )

        finally:
            # Restore setup.py if we moved it
            if setup_py_backup and setup_py_backup.exists():
                setup_py_backup.rename(setup_py)
