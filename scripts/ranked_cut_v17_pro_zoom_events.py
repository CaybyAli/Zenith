from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.render.reaction_size_events import *  # noqa: F401,F403
from core.render.reaction_size_events import (
    PRO_ZOOM_REACTION_SIGNAL_SIZE_SOURCE as REACTION_SIGNAL_SIZE_SOURCE,
    PRO_ZOOM_SEMANTIC_QUESTION_SIZE_SOURCE as SEMANTIC_QUESTION_SIZE_SOURCE,
    main,
)


if __name__ == "__main__":
    raise SystemExit(main())
