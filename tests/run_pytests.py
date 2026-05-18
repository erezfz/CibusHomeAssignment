#!/usr/bin/env python3
import subprocess
import sys


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "pytest",
    ]
    command.extend(sys.argv[1:])
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
