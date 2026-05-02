from __future__ import annotations

import logging
import sys

# Use absolute import so this file works both as `python -m claukawa`
# and as a PyInstaller entry script (where the package context is lost).
from claukawa.app import ClaukawaApp


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = ClaukawaApp(sys.argv)
    if not app.can_run():
        return 1
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
