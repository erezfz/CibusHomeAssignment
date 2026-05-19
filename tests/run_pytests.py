#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    command = [
        sys.executable,
        "-m",
        "pytest",
    ]
    args = sys.argv[1:] if sys.argv[1:] else ["tests"]
    command.extend(args)
    return subprocess.call(command, cwd=project_root)


if __name__ == "__main__":
    raise SystemExit(main())
