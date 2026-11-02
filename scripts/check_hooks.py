#!/usr/bin/env python3
"""Source-tree and skill-bundle entry point; shares the installed CLI."""

import sys

from hook_doctor.cli import main


if __name__ == "__main__":
    sys.exit(main())
