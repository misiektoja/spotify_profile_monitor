"""Verify actionable interval errors at the real startup entry point."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("name", ["SPOTIFY_CHECK_INTERVAL", "LIVENESS_CHECK_INTERVAL"])
# Names the rejected setting in ordinary output before any network request
def test_invalid_interval_names_the_setting_without_debug(tmp_path, name):
    config = tmp_path / "settings.conf"
    config.write_text(f"CLEAR_SCREEN=False\n{name}='daily'\n", encoding="utf-8")
    script = """
import requests
import socket
import sys
from unittest.mock import patch
import spotify_profile_monitor as monitor
attempts = []
# Records unwanted network work without replacing the real startup or error renderer
def offline(*args, **kwargs):
    attempts.append(True)
    raise requests.ConnectionError("offline")
sys.argv = ["spotify_profile_monitor", "target", "--config-file", sys.argv[1], "--env-file", "none", "--no-color"]
try:
    with patch.object(requests.Session, "send", offline), patch.object(socket.socket, "connect", offline):
        monitor.main()
except SystemExit as exc:
    print("EXIT:", exc.code)
print("NETWORK_ATTEMPTS:", len(attempts))
"""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-c", script, str(config)], cwd=root, env=dict(os.environ, NO_COLOR="1"), capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert f"{name} must be a number" in result.stdout
    assert "numeric seconds" in result.stdout
    assert "EXIT: 1" in result.stdout
    assert "NETWORK_ATTEMPTS: 0" in result.stdout
