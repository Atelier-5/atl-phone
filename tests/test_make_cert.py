# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atelier-5
"""make_cert.sh, end to end: the bridge's server on the certificate it makes, trusted through its authority alone."""
import shutil
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ros2" / "atl_phone"))
from atl_phone.wsserver import PhoneServer  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("openssl"), reason="no openssl")


def make(d: Path) -> str:
    return subprocess.run([str(ROOT / "scripts" / "make_cert.sh"), str(d)], capture_output=True, text=True, check=True).stdout


def test_the_phone_trusts_the_bridge_through_the_authority(tmp_path):
    d = tmp_path / "certs"
    assert "new authority" in make(d)
    assert (d / "ca.key").stat().st_mode & 0o077 == 0 and (d / "key.pem").stat().st_mode & 0o077 == 0
    s = PhoneServer(ROOT / "ros2" / "atl_phone" / "web", 0, "127.0.0.1", cert=str(d / "cert.pem"),
                    cert_key=str(d / "key.pem"), ca=str(d / "ca.crt")).start()
    try:
        assert s.scheme == "https"
        trust = ssl.create_default_context(cafile=str(d / "ca.crt"))  # only this PC's authority, as on a phone
        for host in ("127.0.0.1", "localhost"):
            r = urllib.request.urlopen(f"https://{host}:{s.port}/ca.crt", context=trust, timeout=5)
            assert r.headers["Content-Type"] == "application/x-x509-ca-cert"
            assert r.read() == (d / "ca.crt").read_bytes()
        with pytest.raises(urllib.error.URLError):  # and a browser without it is warned
            urllib.request.urlopen(f"https://127.0.0.1:{s.port}/", context=ssl.create_default_context(), timeout=5)
    finally:
        s.stop()


def test_a_second_run_keeps_what_is_good(tmp_path):
    d = tmp_path / "certs"
    make(d)
    ca, cert = (d / "ca.crt").read_bytes(), (d / "cert.pem").read_bytes()
    assert "still good" in make(d)
    assert (d / "ca.crt").read_bytes() == ca and (d / "cert.pem").read_bytes() == cert
    (d / "cert.pem").unlink()
    assert "new certificate" in make(d) and (d / "ca.crt").read_bytes() == ca  # the phones keep their authority
