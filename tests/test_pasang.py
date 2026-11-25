import os
import shutil
import subprocess

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.mark.skipif(shutil.which("sh") is None, reason="butuh sh")
def test_pasang_membuat_boot_dan_widget(tmp_path):
    env = {**os.environ, "HOME": str(tmp_path)}
    r = subprocess.run(["sh", os.path.join(ROOT, "termux", "pasang.sh")], env=env, capture_output=True, text=True)
    assert r.returncode == 0
    boot = (tmp_path / ".termux" / "boot" / "saku.sh").read_text()
    widget = (tmp_path / ".shortcuts" / "SakuAI-catat-suara").read_text()
    assert ROOT in boot and "start.sh" in boot and ROOT in widget and "catat_suara.py" in widget
    assert os.access(tmp_path / ".termux" / "boot" / "saku.sh", os.X_OK)
