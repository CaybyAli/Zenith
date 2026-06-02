from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.render.final_render_pipeline import *  # noqa: F401,F403
from core.render.final_render_pipeline import _extract_semantic_question_windows, main


if __name__ == "__main__":
    raise SystemExit(main())
