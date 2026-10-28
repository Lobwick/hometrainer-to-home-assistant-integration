"""Charge la logique du home trainer sans Home Assistant (tests rapides)."""

import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "hometrainer"

pkg = types.ModuleType("ht_core")
pkg.__path__ = [str(ROOT)]
sys.modules["ht_core"] = pkg
for name in ("const", "trainer"):
    spec = importlib.util.spec_from_file_location(f"ht_core.{name}", ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"ht_core.{name}"] = module
    spec.loader.exec_module(module)
