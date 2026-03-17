"""Pull latest changes and reinstall all utilities."""
import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo = Path(__file__).resolve().parent.parent.parent
    install_sh = repo / "install.sh"

    if not install_sh.exists():
        sys.exit(f"Error: install.sh not found at {install_sh}")

    print("Pulling latest changes ...")
    result = subprocess.run(["git", "pull"], cwd=repo)
    if result.returncode != 0:
        sys.exit("Error: git pull failed.")

    print("")
    print("Reinstalling utilities ...")
    result = subprocess.run(["bash", str(install_sh)])
    sys.exit(result.returncode)