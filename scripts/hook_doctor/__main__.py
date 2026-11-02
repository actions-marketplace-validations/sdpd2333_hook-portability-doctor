"""Run the installed checker with python -m hook_doctor."""

import sys

from .cli import main


if __name__ == "__main__":
    sys.exit(main())
