import os
import shutil
import signal
import subprocess
import time

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _hidup(pid):
    """Proses yang sudah mati tapi belum 'dituai' induknya (zombie) dihitung mati."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False
    except OSError:
        pass
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@pytest.mark.skipif(shutil.which("sh") is None or os.name == "nt", reason="butuh sh dan sistem POSIX")
@pytest.mark.parametrize("sinyal", [signal.SIGINT, signal.SIGTERM])
def test_start_berhenti_bersih(tmp_path, sinyal):
    """Ctrl+C (SIGINT) atau SIGTERM harus menghentikan semua proses tanpa crash (dulu: segmentation fault)."""
    catatan = tmp_path / "pid.txt"
    palsu = tmp_path / "python"          # 'python' tiruan yang hanya diam
    palsu.write_text(f'#!/bin/sh\necho $$ >> "{catatan}"\nexec sleep 60\n')
    palsu.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}

    p = subprocess.Popen(["sh", os.path.join(ROOT, "start.sh")], cwd=ROOT, env=env, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):                  # tunggu ketiga proses benar-benar hidup
        if catatan.exists() and len(catatan.read_text().split()) >= 3:
            break
        time.sleep(0.1)
    pids = [int(x) for x in catatan.read_text().split()]
    assert len(pids) == 3

    os.killpg(p.pid, sinyal)             # persis seperti menekan Ctrl+C di terminal
    assert p.wait(timeout=10) == 0       # -11 berarti segmentation fault
    time.sleep(0.3)
    assert not any(_hidup(x) for x in pids)
