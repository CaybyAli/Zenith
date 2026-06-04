from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.aggregate_style_dna as aggregate_style_dna


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", default=str(aggregate_style_dna.DEFAULT_CORPUS_ROOT))
    parser.add_argument("--output-dir", default=str(aggregate_style_dna.DEFAULT_OUTPUT_DIR))
    parser.add_argument("--pair-truth-path", default=str(aggregate_style_dna.PAIR_TRUTH_PATH))
    args = parser.parse_args()

    result = aggregate_style_dna.build_style_dna(
        corpus_root=args.corpus_root,
        output_dir=args.output_dir,
        pair_truth_path=args.pair_truth_path,
    )

    print("P5_G3_STYLE_DNA_OUTPUT_DIR", args.output_dir)
    print("P5_G3_PAIR_TRUTH_PATH", args.pair_truth_path)
    for kind, payload in result.items():
        dna = payload["dna"]
        print(f"P5_G3_OUTPUT {kind} {payload['output_path']}")
        print(
            f"P5_G3_SOURCE_COUNT {kind} "
            f"{json.dumps({'source_count': dna.get('source_count')}, sort_keys=True)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    