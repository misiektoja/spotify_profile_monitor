import ast
import inspect
import tempfile
from pathlib import Path

import pytest

import spotify_profile_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "notification_escaping_test_artifacts"

HOSTILE_NAME = '<img src=x onerror="alert(1)">'
HOSTILE_ESCAPED = "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"

# Interpolations that are safe without escape() because the value is a number the API reports as a count,
# never free text. Listed explicitly so a new unescaped name cannot slip in behind a blanket exemption
ALLOWED_UNESCAPED = frozenset({"f_count", "f_old_count", "p_tracks", "p_tracks_old", "p_collaborators", "p_collaborators_old"})

# Helpers that emit their own markup or render only dates, durations and numbers. None of them can carry
# Spotify-supplied text, so escaping their output would only mangle the timestamps users read
SAFE_HELPERS = frozenset({"get_cur_ts", "display_time", "get_short_date_from_ts", "calculate_timespan", "get_range_of_dates_from_tss"})


# Creates a disposable test directory under the project local directory
def make_test_directory():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=str(ARTIFACT_ROOT))


# Collects every HTML notification body the module builds, as (function, source line, expression) triples
def html_body_interpolations():
    tree = ast.parse(inspect.getsource(monitor))
    enclosing = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                enclosing[id(child)] = node.name

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if not any("body_html" in name for name in targets):
            continue
        for part in ast.walk(node.value):
            if isinstance(part, ast.FormattedValue):
                yield enclosing.get(id(node), "<module>"), node.lineno, ast.unparse(part.value)


# Reports whether one interpolated expression is neutralized before it reaches the HTML body
def interpolation_is_safe(expression):
    parsed = ast.parse(expression, mode="eval").body

    if isinstance(parsed, ast.Name):
        # A fragment this sweep already checks in its own right, or an allowlisted numeric count
        return parsed.id.endswith("_html") or "body_html" in parsed.id or parsed.id in ALLOWED_UNESCAPED

    if isinstance(parsed, ast.Call):
        function = parsed.func
        name = function.id if isinstance(function, ast.Name) else getattr(function, "attr", "")
        return name in {"escape", "escape_html_attr", *SAFE_HELPERS}

    return False


# Drives the real follower notification and returns the HTML body it handed to the delivery layer
def render_follower_notification(monkeypatch, username, added_name):
    captured = {}
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "FOLLOWERS_FOLLOWINGS_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "webhook_event_enabled", lambda notification_type: False)
    monkeypatch.setattr(monitor, "send_notification_channels", lambda *arguments, **keywords: captured.update(subject=arguments[1], body=arguments[2], body_html=arguments[3]))

    with make_test_directory() as directory:
        monitor.spotify_print_changed_followers_followings_playlists(
            username,
            [{"name": added_name, "uri": "spotify:user:newfollower"}],
            [],
            1,
            0,
            "Followers",
            "for",
            "Added followers", "Added Follower",
            "Removed followers", "Removed Follower",
            str(Path(directory) / "followers.json"),
            "",
            True,
            False,
        )
    return captured


# Confirms a hostile display name cannot inject markup into the notification body users receive
def test_hostile_display_name_is_escaped_in_the_email_body(monkeypatch):
    captured = render_follower_notification(monkeypatch, HOSTILE_NAME, "Normal Follower")

    assert HOSTILE_ESCAPED in captured["body_html"]
    assert "<img src=x" not in captured["body_html"]


# Confirms a hostile follower name is escaped in the rendered list, not only the headline
def test_hostile_follower_name_is_escaped_in_the_email_body(monkeypatch):
    captured = render_follower_notification(monkeypatch, "Normal User", HOSTILE_NAME)

    assert HOSTILE_ESCAPED in captured["body_html"]
    assert "<img src=x" not in captured["body_html"]


# Confirms the plain-text body and subject stay readable, since escaping belongs to the HTML body only
def test_plain_text_notification_is_not_html_escaped(monkeypatch):
    captured = render_follower_notification(monkeypatch, "Ordinary User", "Ordinary Follower")

    assert "&lt;" not in captured["body"]
    assert "&amp;" not in captured["subject"]


@pytest.mark.parametrize("hostile", ['" onmouseover="alert(1)', "<script>alert(1)</script>", "name & <b>bold</b>", '<a href="https://evil.example">Reset your password</a>'])
# Confirms no crafted display name shape survives into the body as live markup
def test_no_hostile_display_name_shape_survives(monkeypatch, hostile):
    captured = render_follower_notification(monkeypatch, hostile, "Normal Follower")
    body_html = captured["body_html"]

    assert "<script" not in body_html
    assert 'onmouseover="' not in body_html, "an unescaped quote would let a display name open a new attribute"
    assert f"<b>{hostile}</b>" not in body_html


# Confirms every value interpolated into an HTML notification body is escaped at the point it is built
def test_every_html_body_interpolation_is_escaped():
    unsafe = [f"{function}:{line} -> {{{expression}}}" for function, line, expression in html_body_interpolations() if not interpolation_is_safe(expression)]

    assert not unsafe, "unescaped Spotify-supplied text can reach an HTML email body:\n" + "\n".join(unsafe)


# Confirms the sweep above is actually looking at the notification bodies rather than silently finding none
def test_html_body_sweep_covers_every_notification():
    interpolations = list(html_body_interpolations())
    functions = {function for function, _, _ in interpolations}

    assert len(interpolations) >= 40, "the HTML body sweep stopped finding notification bodies, update its matching"
    assert "spotify_profile_monitor_uri" in functions
    assert "spotify_print_changed_followers_followings_playlists" in functions


# Confirms an unescaped interpolation would actually be reported, so the sweep cannot pass vacuously
@pytest.mark.parametrize("expression,expected", [("escape(username)", True), ("escape_html_attr(p_url)", True), ("added_f_list_mbody_html", True), ("f_count", True), ("username", False), ("p_name", False), ("f_dict['name']", False), ("spotify_convert_uri_to_url(uri)", False)])
def test_interpolation_safety_rule(expression, expected):
    assert interpolation_is_safe(expression) is expected
