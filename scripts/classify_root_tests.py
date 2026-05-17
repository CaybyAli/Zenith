from pathlib import Path
import subprocess
import sys
import re
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "PHASE1_ROOT_TEST_CLASSIFICATION.tsv"

root_tests = sorted(ROOT.glob("test_*.py"), key=lambda p: p.name)

rows = []

for index, test_file in enumerate(root_tests, start=1):
    print(f"[{index}/{len(root_tests)}] {test_file.name}", flush=True)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", test_file.name],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=90,
    )

    output = (result.stdout or "") + "\n" + (result.stderr or "")

    category = "LEBEND"
    missing = ""

    if result.returncode != 0:
        match = re.search(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", output)
        if match:
            category = "VERWAIST"
            missing = match.group(1)
        else:
            category = "UNKLAR"

    rows.append((test_file.name, category, missing))

counts = Counter(row[1] for row in rows)

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8", newline="\n") as f:
    f.write("file\tcategory\tmissing\n")
    for filename, category, missing in rows:
        f.write(f"{filename}\t{category}\t{missing}\n")

print("=== Fertig ===")
print(f"Root-Tests gesamt: {len(rows)}")
print(f"LEBEND: {counts.get('LEBEND', 0)}")
print(f"VERWAIST: {counts.get('VERWAIST', 0)}")
print(f"UNKLAR: {counts.get('UNKLAR', 0)}")