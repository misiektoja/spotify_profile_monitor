import ast
import inspect
import os
import re
import signal
import time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, call

import pytest

import spotify_profile_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "request"}


# Collects every outgoing HTTP call in the module together with the verify argument it passes
def http_calls_with_verification():
    tree = ast.parse((PROJECT_ROOT / "spotify_profile_monitor.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in HTTP_METHODS:
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
        if "timeout" not in keywords and "verify" not in keywords:
            continue
        verify = keywords.get("verify")
        yield node.lineno, ast.unparse(node.func.value), None if verify is None else ast.unparse(verify)


POSIX_ALARMS = pytest.mark.skipif(os.name != "posix" or not hasattr(signal, "setitimer"), reason="POSIX interval timers only")


@contextmanager
# Arms a real interval timer for the test and always clears it, so a failure cannot leak a pending SIGALRM
def real_alarm(delay):
    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, monitor.timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, delay)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


# Confirms a nested request alarm restores the enclosing loop deadline instead of discarding it
def test_nested_timeout_alarm_restores_outer_deadline(monkeypatch):
    get_handler = Mock(side_effect=["original-handler", monitor.timeout_handler])
    get_timer = Mock(side_effect=[(0.0, 0.0), (28.0, 0.0)])
    set_handler = Mock()
    set_timer = Mock()
    monotonic = Mock(side_effect=[100.0, 102.0, 103.0, 106.0])
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(monitor.signal, "getsignal", get_handler)
    monkeypatch.setattr(monitor.signal, "getitimer", get_timer)
    monkeypatch.setattr(monitor.signal, "signal", set_handler)
    monkeypatch.setattr(monitor.signal, "setitimer", set_timer)
    monkeypatch.setattr(monitor.time, "monotonic", monotonic)

    outer_state = monitor._start_timeout_alarm(30)
    inner_state = monitor._start_timeout_alarm(60)
    monitor._restore_timeout_alarm(inner_state)
    monitor._restore_timeout_alarm(outer_state)

    assert set_timer.call_args_list == [
        call(monitor.signal.ITIMER_REAL, 30.0),
        call(monitor.signal.ITIMER_REAL, 28.0),
        call(monitor.signal.ITIMER_REAL, 27.0, 0.0),
        call(monitor.signal.ITIMER_REAL, 0, 0.0),
    ]
    assert set_handler.call_args_list[-2:] == [call(monitor.signal.SIGALRM, monitor.timeout_handler), call(monitor.signal.SIGALRM, "original-handler")]


# Confirms a longer nested timeout is clamped down so it cannot postpone the enclosing watchdog
def test_nested_alarm_never_extends_the_enclosing_deadline(monkeypatch):
    set_timer = Mock()
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(monitor.signal, "getsignal", lambda sig: "original-handler")
    monkeypatch.setattr(monitor.signal, "getitimer", lambda which: (4.0, 0.0))
    monkeypatch.setattr(monitor.signal, "signal", Mock())
    monkeypatch.setattr(monitor.signal, "setitimer", set_timer)

    monitor._start_timeout_alarm(monitor.FUNCTION_TIMEOUT + 2)

    assert set_timer.call_args_list == [call(monitor.signal.ITIMER_REAL, 4.0)]


# Confirms a restore never resurrects an expired deadline as a disabled timer
def test_restore_keeps_an_overrun_deadline_armed(monkeypatch):
    set_timer = Mock()
    monotonic = Mock(side_effect=[100.0, 400.0])
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(monitor.signal, "getsignal", lambda sig: "original-handler")
    monkeypatch.setattr(monitor.signal, "getitimer", lambda which: (5.0, 0.0))
    monkeypatch.setattr(monitor.signal, "signal", Mock())
    monkeypatch.setattr(monitor.signal, "setitimer", set_timer)
    monkeypatch.setattr(monitor.time, "monotonic", monotonic)

    monitor._restore_timeout_alarm(monitor._start_timeout_alarm(5))

    assert set_timer.call_args_list[-1] == call(monitor.signal.ITIMER_REAL, 0.000001, 0.0)


# Confirms no enclosing deadline means the timer is cleared rather than left running
def test_restore_clears_the_timer_when_nothing_enclosed_it(monkeypatch):
    set_timer = Mock()
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(monitor.signal, "getsignal", lambda sig: "original-handler")
    monkeypatch.setattr(monitor.signal, "getitimer", lambda which: (0.0, 0.0))
    monkeypatch.setattr(monitor.signal, "signal", Mock())
    monkeypatch.setattr(monitor.signal, "setitimer", set_timer)

    monitor._restore_timeout_alarm(monitor._start_timeout_alarm(30))

    assert set_timer.call_args_list[-1] == call(monitor.signal.ITIMER_REAL, 0, 0.0)


# Confirms Windows keeps its per-request timeouts without touching unsupported interval timers
def test_timeout_alarm_is_noop_on_windows(monkeypatch):
    get_timer = Mock()
    monkeypatch.setattr(monitor.platform, "system", lambda: "Windows")
    monkeypatch.setattr(monitor.signal, "getitimer", get_timer)

    assert monitor._start_timeout_alarm(30) is None
    monitor._restore_timeout_alarm(None)
    get_timer.assert_not_called()


# Confirms an interpreter without interval timers is handled like Windows rather than raising
def test_timeout_alarm_is_noop_without_setitimer(monkeypatch):
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    monkeypatch.delattr(monitor.signal, "setitimer", raising=False)

    assert monitor._start_timeout_alarm(30) is None
    monitor._restore_timeout_alarm(None)


@POSIX_ALARMS
# Confirms the real regression: a token helper's own alarm no longer cancels the main-loop watchdog
def test_token_helper_leaves_the_loop_watchdog_armed(monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor.req, "get", Mock(return_value=Mock(status_code=200)))

    with real_alarm(30):
        assert monitor.check_token_validity("token", "client-id") is True
        remaining = signal.getitimer(signal.ITIMER_REAL)[0]

    assert remaining > 0, "the enclosing watchdog was cancelled by the nested request alarm"
    assert remaining <= 30


@POSIX_ALARMS
# Confirms a token helper that fails still restores the enclosing deadline through its finally
def test_failed_token_helper_leaves_the_loop_watchdog_armed(monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor.req, "get", Mock(side_effect=Exception("connection reset")))

    with real_alarm(30):
        assert monitor.check_token_validity("token", "client-id") is False
        remaining = signal.getitimer(signal.ITIMER_REAL)[0]

    assert remaining > 0


@POSIX_ALARMS
# Confirms the restored deadline still fires, so a wedged request cannot hang the loop forever
def test_restored_watchdog_still_fires(monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor.req, "get", Mock(return_value=Mock(status_code=200)))

    with real_alarm(0.35):
        monitor.check_token_validity("token", "client-id")
        with pytest.raises(monitor.TimeoutException):
            time.sleep(1.5)


@POSIX_ALARMS
# Confirms an unnested arm and restore leaves no stray timer behind for the next loop iteration
def test_unnested_alarm_leaves_no_pending_timer():
    monitor._restore_timeout_alarm(monitor._start_timeout_alarm(30))

    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0.0


# Confirms the loop watchdog outlasts any single request alarm it encloses, so it cannot fire spuriously
def test_alarm_timeout_exceeds_the_nested_request_alarm():
    assert monitor.ALARM_TIMEOUT > monitor.FUNCTION_TIMEOUT + 2
    assert monitor.ALARM_TIMEOUT >= 2 * (monitor.FUNCTION_TIMEOUT + 2)
    assert monitor.ALARM_RETRY > 0


# Confirms every armed alarm is paired with a restore, so no call site can leak a deadline
def test_every_alarm_arm_has_a_restore():
    source = inspect.getsource(monitor)
    starts = source.count("_start_timeout_alarm(")
    restores = source.count("_restore_timeout_alarm(")

    assert starts >= 8, "alarm call sites disappeared, update this guard"
    assert restores >= starts, "an alarm is armed without a matching restore"
    assert "signal.alarm(" not in source, "raw signal.alarm bypasses the deadline-preserving helpers"


# Confirms the main loop arms its watchdog with the loop-sized timeout rather than a request-sized one
def test_main_loop_arms_the_watchdog_with_alarm_timeout():
    source = inspect.getsource(monitor.spotify_profile_monitor_uri)

    assert "_start_timeout_alarm(ALARM_TIMEOUT)" in source
    assert re.search(r"except TimeoutException[\s\S]{0,400}?time\.sleep\(ALARM_RETRY\)", source), "a watchdog timeout must retry on the alarm delay"


# Confirms a SIGHUP reload picks up rotated secrets from the dotenv file
def test_sighup_reloads_rotated_secrets(monkeypatch, tmp_path, capsys):
    env_file = tmp_path / "rotated.env"
    env_file.write_text("SP_DC_COOKIE=rotated-cookie-value\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "DOTENV_FILE", str(env_file))
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "stale-cookie-value")
    monkeypatch.setattr(monitor, "SP_CACHED_ACCESS_TOKEN", "stale-token")
    monkeypatch.setattr(monitor, "SP_ACCESS_TOKEN_EXPIRES_AT", time.time() + 3600)

    monitor.reload_secrets_signal_handler(signal.SIGHUP, None)

    assert monitor.SP_DC_COOKIE == "rotated-cookie-value"
    assert monitor.SP_CACHED_ACCESS_TOKEN is None, "a rotated secret must invalidate the cached token"
    assert monitor.SP_ACCESS_TOKEN_EXPIRES_AT == 0
    output = capsys.readouterr().out
    assert "Reloaded SP_DC_COOKIE" in output
    assert "rotated-cookie-value" not in output, "a reloaded secret must never be echoed"


# Confirms an unchanged dotenv leaves the cached token in place so SIGHUP is not a forced re-auth
def test_sighup_without_changes_keeps_the_cached_token(monkeypatch, tmp_path):
    env_file = tmp_path / "unchanged.env"
    env_file.write_text("SP_DC_COOKIE=same-cookie-value\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "DOTENV_FILE", str(env_file))
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "same-cookie-value")
    monkeypatch.setattr(monitor, "SP_CACHED_ACCESS_TOKEN", "live-token")

    monitor.reload_secrets_signal_handler(signal.SIGHUP, None)

    assert monitor.SP_CACHED_ACCESS_TOKEN == "live-token"


# Confirms DOTENV_FILE set to none disables the reload rather than scanning for a stray .env
def test_sighup_honors_disabled_dotenv(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "configured-cookie-value")
    monkeypatch.setenv("SP_DC_COOKIE", "environment-cookie-value")

    monitor.reload_secrets_signal_handler(signal.SIGHUP, None)

    assert monitor.SP_DC_COOKIE == "configured-cookie-value"


# TLS verification must always come from the documented setting, since a call that hardcodes it either
# cannot be turned off for a TLS-inspecting proxy or cannot be turned back on for everyone else
def test_every_http_call_verifies_through_the_configured_setting():
    calls = list(http_calls_with_verification())
    offenders = [(line, receiver, verify) for line, receiver, verify in calls if verify not in ("VERIFY_SSL", "verify")]

    # A refactor that renames the sessions must not quietly leave this test matching nothing
    assert len(calls) >= 25
    assert offenders == []
