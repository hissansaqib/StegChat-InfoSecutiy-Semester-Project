"""Import-boundary tests verifying clean modular architecture and crypto isolation.

Rules:
1. Only `backend/app/crypto` may import from `cryptography`.
2. Carriers (`backend/app/carriers/**`) must NOT import anything from:
   - backend.app.api
   - backend.app.db
   - fastapi
   - sqlalchemy
   - cryptography
3. Bench, Analysis, and Recommender must NEVER import a concrete carrier implementation.
"""

import ast
import pathlib
import pytest

BACKEND_APP_DIR = pathlib.Path(__file__).parent.parent / "app"

def get_python_files(directory: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in directory.rglob("*.py") if "__pycache__" not in p.parts]

def get_imported_modules(file_path: pathlib.Path) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

def test_cryptography_import_isolation():
    """Verify that NO file outside backend/app/crypto imports from cryptography."""
    crypto_dir = BACKEND_APP_DIR / "crypto"

    for py_file in get_python_files(BACKEND_APP_DIR):
        # Allow files inside backend/app/crypto
        if py_file.is_relative_to(crypto_dir):
            continue

        imports = get_imported_modules(py_file)
        for imp in imports:
            assert not imp.startswith("cryptography"), (
                f"Architecture violation in {py_file.relative_to(BACKEND_APP_DIR)}: "
                f"Directly imports '{imp}'. "
                f"All cryptographic operations MUST go through backend.app.crypto."
            )

def test_carriers_boundary_isolation():
    """Verify carriers import nothing from api, db, fastapi, sqlalchemy, or cryptography."""
    carriers_dir = BACKEND_APP_DIR / "carriers"
    forbidden_prefixes = (
        "fastapi",
        "sqlalchemy",
        "cryptography",
        "backend.app.api",
        "backend.app.db",
        "app.api",
        "app.db",
    )

    for py_file in get_python_files(carriers_dir):
        imports = get_imported_modules(py_file)
        for imp in imports:
            for forbidden in forbidden_prefixes:
                assert not imp.startswith(forbidden), (
                    f"Architecture violation in {py_file.name}: "
                    f"Carrier illegally imports '{imp}'"
                )

def test_bench_analysis_recommender_isolation():
    """Verify bench, analysis, and recommender never import concrete carriers directly."""
    target_files = [
        BACKEND_APP_DIR / "api" / "bench.py",
        BACKEND_APP_DIR / "api" / "analysis.py",
        BACKEND_APP_DIR / "api" / "recommend.py",
        BACKEND_APP_DIR / "core" / "recommender.py",
    ]

    concrete_carrier_modules = (
        "backend.app.carriers.fake_carrier",
        "backend.app.carriers.png_lsb",
        "backend.app.carriers.wav_lsb",
        "backend.app.carriers.text_zw",
        "app.carriers.fake_carrier",
        "app.carriers.png_lsb",
        "app.carriers.wav_lsb",
        "app.carriers.text_zw",
    )

    for target in target_files:
        if not target.exists():
            continue
        imports = get_imported_modules(target)
        for imp in imports:
            for concrete in concrete_carrier_modules:
                assert not imp.startswith(concrete), (
                    f"Architecture violation in {target.name}: "
                    f"Directly imports concrete carrier '{imp}'. "
                    f"Must use abstract registry or carrier interface instead."
                )
