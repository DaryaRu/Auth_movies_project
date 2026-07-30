#!/usr/bin/env python3
"""Локальный аналог mypy job из CI.
Вызывается через make mypy.
Окружения кэшируются в .mypy-check-venvs/.
"""
import json
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VENV_DIR = ROOT / ".mypy-check-venvs"
UV = shutil.which("uv")


def install_packages(python_path: Path, *args: str) -> None:
    """Ставит пакеты в указанный venv через uv, если он есть (если нет, то через pip)."""
    if UV:
        subprocess.run([UV, "pip", "install", "--python", str(python_path), *args], check=True, cwd=ROOT)
    else:
        subprocess.run([str(python_path), "-m", "pip", "install", "-q", *args], check=True, cwd=ROOT)


def build_matrix() -> list[dict[str, Any]]:
    """Запускает build_mypy_matrix.py и возвращает список записей."""
    result = subprocess.run(
        [sys.executable, str(ROOT / ".github/scripts/build_mypy_matrix.py")],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)["include"]


def check_entry(entry: dict[str, Any]) -> tuple[str, bool]:
    """Ставит зависимости одной записи матрицы в её venv и прогоняет mypy."""
    path = entry["path"]
    reqs = entry["requirements"]
    venv_dir = VENV_DIR / path.replace("/", "_")
    if not venv_dir.exists():
        venv.create(venv_dir, with_pip=True)
    python_path = venv_dir / "bin" / "python"

    install_packages(python_path, "mypy", "pydantic")
    for req in reqs:
        lines = (ROOT / req).read_text().splitlines()
        filtered = [line for line in lines if not line.startswith("uwsgi")]
        tmp_reqs = venv_dir / "_reqs.txt"
        tmp_reqs.write_text("\n".join(filtered))
        install_packages(python_path, "-r", str(tmp_reqs))

    print(f"\n=== mypy {path} ===", flush=True)
    result = subprocess.run([str(venv_dir / "bin" / "mypy"), path], cwd=ROOT)
    return path, result.returncode == 0


def main() -> int:
    """Строит матрицу, проверяет каждую запись и печатает итог."""
    VENV_DIR.mkdir(exist_ok=True)
    matrix = build_matrix()

    results: list[tuple[str, bool]] = [check_entry(entry) for entry in matrix]

    print("\n=== Результаты проверки: ===")
    ok = True
    for path, passed in results:
        print(f"{'✅' if passed else '⛔️'}  {path}")
        ok = ok and passed

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
