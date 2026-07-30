#!/usr/bin/env python3
"""Строит матрицу mypy для CI по расположению requirements.txt в репозитории."""
import json
import logging
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDE_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "migrations"}
SRC_DIR_NAME = "src"
TESTS_DIR_NAME = "tests"
REQUIREMENTS_FILENAME = "requirements.txt"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def is_excluded(path: Path) -> bool:
    """Проверяет, попадает ли путь в директорию, которую проверять не нужно."""
    return any(part in EXCLUDE_DIR_NAMES for part in path.relative_to(ROOT).parts)


def find_requirements_files() -> list[Path]:
    """Находит все requirements.txt в репозитории, пропуская исключенные директории."""
    found = sorted(p for p in ROOT.rglob(REQUIREMENTS_FILENAME) if not is_excluded(p))
    logger.info("Найдено %d файлов %s", len(found), REQUIREMENTS_FILENAME)
    for req in found:
        logger.debug("  %s", req.relative_to(ROOT))
    return found


def find_base_requirements(service_root: Path) -> Path | None:
    """Находит собственный requirements.txt сервиса по обеим раскладкам директорий."""
    direct = service_root / REQUIREMENTS_FILENAME
    if direct.exists():
        return direct
    via_src = service_root / SRC_DIR_NAME / REQUIREMENTS_FILENAME
    if via_src.exists():
        return via_src
    return None


def main() -> None:
    """Строит матрицу mypy и выводит её в stdout в виде JSON."""
    req_files = find_requirements_files()
    entries = []
    tests_groups = defaultdict(list)

    for req in req_files:
        parts = req.relative_to(ROOT).parts
        if TESTS_DIR_NAME not in parts:
            service_dir = req.parent
            src_subdir = service_dir / SRC_DIR_NAME
            code_path = src_subdir if src_subdir.is_dir() else service_dir
            entries.append({
                "path": str(code_path.relative_to(ROOT)),
                "requirements": [str(req.relative_to(ROOT))],
            })
            continue

        idx = parts.index(TESTS_DIR_NAME)
        service_root = ROOT.joinpath(*parts[:idx])
        tests_groups[service_root].append(req)

    for service_root, reqs in sorted(tests_groups.items()):
        base = find_base_requirements(service_root)
        combined = ([base] if base else []) + sorted(reqs)
        entries.append({
            "path": str((service_root / TESTS_DIR_NAME).relative_to(ROOT)),
            "requirements": [str(r.relative_to(ROOT)) for r in combined],
        })

    entries.sort(key=lambda e: e["path"])

    paths = [e["path"] for e in entries]
    duplicates = {p for p in paths if paths.count(p) > 1}
    if duplicates:
        raise SystemExit(
            f"build_mypy_matrix: несколько requirements.txt ведут к одному "
            f"и тому же пути в матрице: {sorted(duplicates)}"
        )

    logger.info("Построена матрица из %d записей:", len(entries))
    for entry in entries:
        logger.info("  %s - %s", entry["path"], ", ".join(entry["requirements"]))

    print(json.dumps({"include": entries}))


if __name__ == "__main__":
    main()
