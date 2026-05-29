from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.style_dna_aggregator import build_style_dna


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", default="learning_corpus")
    parser.add_argument("--output-dir", default="style_dna/ali")
    parser.add_argument("--no-strict-counts", action="store_true")
    args = parser.parse_args()

    result = build_style_dna(
        corpus_root=args.corpus_root,
        output_dir=args.output_dir,
        strict_counts=not args.no_strict_counts,
    )

    manifest = result["manifest"]
    print("P5_G3_STYLE_DNA_MANIFEST", result["manifest_path"])
    print("P5_G3_TOTAL_SOURCE_COUNT", manifest["total_source_count"])
    print("P5_G3_SOURCE_COUNTS", json.dumps(manifest["source_counts"], sort_keys=True))
    print(
        "P5_G3_TRANSCRIPT_NON_EMPTY_COUNTS",
        json.dumps(manifest["transcript_non_empty_counts"], sort_keys=True),
    )
    for kind, path in manifest["output_files"].items():
        print(f"P5_G3_OUTPUT {kind} {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
