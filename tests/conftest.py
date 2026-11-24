import importlib.util
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from core import config  # noqa: E402


@pytest.fixture()
def app_ctx(tmp_path, monkeypatch):
    """Muat api/main.py dengan database sementara & tanpa kunci API."""
    monkeypatch.setattr(config, "APP_DB", str(tmp_path / "app.db"))
    monkeypatch.setattr(config, "LEDGER_DB", str(tmp_path / "ledger.db"))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    spec = importlib.util.spec_from_file_location("saku_main", os.path.join(ROOT, "api", "main.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, mod.app.test_client()
