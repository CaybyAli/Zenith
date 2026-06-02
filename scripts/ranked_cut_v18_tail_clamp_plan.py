from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.cut_planning.tail_clamp import *  # noqa: F401,F403
from core.cut_planning.tail_clamp import main


if __name__ == "__main__":
    raise SystemExit(main())
