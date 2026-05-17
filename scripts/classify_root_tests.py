from __future__ import annotations

import ast
import importlib.util
import importlib
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "PHASE1_ROOT_TEST_CLASSIFICATION.md"

EXPECTED_COUNTS = {
    "LEBEND": 29,
    "VERWAIST": 135,
    "UNKLAR": 1,
}

THIRD_PARTY_ALLOWLIST = {
    "cv2",
    "dotenv",
    "flask",
    "moviepy",
    "numpy",
    "openai",
    "pandas",
    "PIL",
    "pytest",
    "requests",
    "streamlit",
    "yaml",
}


def top_level_name(module_name: str) -> str:
    return module_name.split(".", 1)[0]


def is_stdlib(module_name: str) -> bool:
    top = top_level_name(module_name)

    if top in sys.builtin_module_names:
        return True

    stdlib_names = getattr(sys, "stdlib_module_names", set())
    return top in stdlib_names


def is_third_party_allowed(module_name: str) -> bool:
    return top_level_name(module_name) in THIRD_PARTY_ALLOWLIST


def spec_exists(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False

def imported_symbol_exists(module_name: str, symbol_name: str) -> bool:
    if symbol_name == "*":
        return True

    if not spec_exists(module_name):
        return False

    try:
        module = importlib.import_module(module_name)
    except Exception:
        return False

    return hasattr(module, symbol_name)

def imported_modules_from_ast(tree: ast.AST) -> set[str]:
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or not node.module:
                continue

            base = node.module
            modules.add(base)

            # from core import xyz -> auch core.xyz prüfen
            # from models import xyz -> auch models.xyz prüfen
            # from shared import xyz -> auch shared.xyz prüfen
            # from app import xyz -> auch app.xyz prüfen
            if base in {"core", "models", "shared", "app"}:
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    modules.add(f"{base}.{alias.name}")

    return modules


def should_check_module(module_name: str) -> bool:
    if is_stdlib(module_name):
        return False

    if is_third_party_allowed(module_name):
        return False

    return True


def classify_file(path: Path) -> tuple[str, list[str]]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return "UNKLAR", []

    imported_modules = sorted(imported_modules_from_ast(tree))
    checked_modules = [module for module in imported_modules if should_check_module(module)]
    missing = [module for module in checked_modules if not spec_exists(module)]

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue

        if node.level != 0 or not node.module:
            continue

        base = node.module

        if not should_check_module(base):
            continue

        for alias in node.names:
            if not imported_symbol_exists(base, alias.name):
                missing.append(f"{base}.{alias.name}")

    missing = sorted(set(missing))

    if missing:
        return "VERWAIST", missing

    return "LEBEND", []

def main() -> int:
    sys.path.insert(0, str(ROOT))

    root_tests = sorted(ROOT.glob("test_*.py"), key=lambda p: p.name)
    rows: list[tuple[str, str, list[str]]] = []

    for index, test_file in enumerate(root_tests, start=1):
        print(f"[{index}/{len(root_tests)}] {test_file.name}", flush=True)
        category, missing = classify_file(test_file)
        rows.append((test_file.name, category, missing))

    counts = Counter(category for _, category, _ in rows)

    missing_groups: dict[str, list[str]] = defaultdict(list)
    for filename, category, missing_modules in rows:
        if category == "VERWAIST":
            for module in missing_modules:
                missing_groups[module].append(filename)

    lines: list[str] = []
    lines.append("# PROJECT ZENITH — Phase 1.5b Root-Test-Klassifizierung")
    lines.append("")
    lines.append("Diese Datei ersetzt die alte falsche Klassifizierung.")
    lines.append("")
    lines.append("## Kriterium")
    lines.append("")
    lines.append("- LEBEND: alle relevanten importierten Projektmodule sind per `importlib.util.find_spec()` auffindbar.")
    lines.append("- VERWAIST: mindestens ein relevanter importierter Modulname ist nicht auffindbar.")
    lines.append("- UNKLAR: Datei kann nicht sauber geparst werden.")
    lines.append("")
    lines.append("Es werden auch präfixlose Projektimporte geprüft, z. B. `dashboard`, `publisher_worker`, `rerender_worker`.")
    lines.append("Standardbibliothek und bekannte Drittanbieter-Pakete werden ignoriert.")
    lines.append("")
    lines.append("Es wurde nichts verschoben, nichts archiviert und nichts gelöscht.")
    lines.append("")
    lines.append("## Summen")
    lines.append("")
    lines.append(f"- Root-Tests gesamt: {len(rows)}")
    lines.append(f"- LEBEND: {counts.get('LEBEND', 0)}")
    lines.append(f"- VERWAIST: {counts.get('VERWAIST', 0)}")
    lines.append(f"- UNKLAR: {counts.get('UNKLAR', 0)}")
    lines.append("")
    lines.append("## Fehlende Module")
    lines.append("")
    lines.append("| Fehlendes Modul | Anzahl Dateien |")
    lines.append("|---|---|")
    for module in sorted(missing_groups):
        lines.append(f"| `{module}` | {len(missing_groups[module])} |")
    lines.append("")
    lines.append("## Einzeltabelle")
    lines.append("")
    lines.append("| Datei | Kategorie | fehlende Module |")
    lines.append("|---|---|---|")

    for filename, category, missing in rows:
        missing_cell = ", ".join(f"`{module}`" for module in missing)
        lines.append(f"| `{filename}` | {category} | {missing_cell} |")

    OUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")

    print("=== Fertig ===")
    print(f"Root-Tests gesamt: {len(rows)}")
    print(f"LEBEND: {counts.get('LEBEND', 0)}")
    print(f"VERWAIST: {counts.get('VERWAIST', 0)}")
    print(f"UNKLAR: {counts.get('UNKLAR', 0)}")

    expected_ok = all(counts.get(key, 0) == expected for key, expected in EXPECTED_COUNTS.items())

    if not expected_ok:
        print("STOPP: Zahlen stimmen nicht mit Masterchat-Vorgabe überein.")
        print(
            "Erwartet: "
            f"LEBEND={EXPECTED_COUNTS['LEBEND']} "
            f"VERWAIST={EXPECTED_COUNTS['VERWAIST']} "
            f"UNKLAR={EXPECTED_COUNTS['UNKLAR']}"
        )
        return 2

    print("KLASSIFIZIERUNG OK: Zahlen stimmen mit Masterchat-Vorgabe überein.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())