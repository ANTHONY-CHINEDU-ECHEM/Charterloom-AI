"""Allow ``python charterloom`` style execution of the command line interface."""

import sys

from charterloom.cli import main

if __name__ == "__main__":
    sys.exit(main())
