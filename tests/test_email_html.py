"""Tests for the HTML notification body, its Discord markdown form and its match with the plain text."""

import difflib
import html as html_module
import json
import os
import re
from pathlib import Path

import pytest

import spotify_profile_monitor as monitor
from test_monitoring_loop import USER, error_alerts_for, profile_snapshot

FIRST_FOLLOWER = {"name": "First Person", "uri": "spotify:user:first"}
SECOND_FOLLOWER = {"name": "Second Person", "uri": "spotify:user:second"}


# Reduces one HTML body back to the text it represents, independently of the module's own converter
def html_to_text(body_html):
    text = re.sub(r"(?is)</?(?:html|head|body)\s*>", "", str(body_html or ""))
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    return html_module.unescape(text)


# Replaces every anchor with its destination, which is what a plain body prints on a bare URL line
def links_as_destinations(line):
    return re.sub(r'(?is)<a\s[^>]*?href="([^"]*)"[^>]*>.*?</a>', r"\1", line)


# Drops the address a plain list row prints in brackets after a name, which the HTML row carries on the name instead
def without_bracketed_url(line):
    return re.sub(r"\s*\[\s*https?://[^\]]*\]", "", line)


# Reports whether one HTML line says what its plain counterpart says, whether it links a name or prints a bare URL
def line_agrees(plain_line, html_line):
    rendered = (html_to_text(html_line), html_to_text(links_as_destinations(html_line)))
    return plain_line in rendered or without_bracketed_url(plain_line) in rendered


# Returns what differs between the plain body and the HTML body, empty when their lines and blank lines match
def structural_diff(body, body_html):
    plain_lines = body.split("\n")
    html_lines = re.sub(r"(?is)</?(?:html|head|body)\s*>", "", str(body_html or "")).split("<br>")
    if len(plain_lines) == len(html_lines) and all(line_agrees(*pair) for pair in zip(plain_lines, html_lines)):
        return ""
    return "\n".join(difflib.unified_diff(plain_lines, [html_to_text(line) for line in html_lines], fromfile="plain", tofile="html-reduced", lineterm=""))


# Builds the profile snapshot one check sees, with the fields a change is reported from
def snapshot(username="Watched Person", followers=0, followings=0):
    answer = profile_snapshot()
    answer.update({"sp_username": username, "sp_user_followers_count": followers, "sp_user_followings_count": followings})
    return answer


@pytest.fixture
# Every alert a timeline covering a renamed profile, a new follower, a new following and an outage produces
def timeline_alerts(monkeypatch, tmp_path, capsys):
    alerts = []
    monkeypatch.setattr(monitor, "PROFILE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "FOLLOWERS_FOLLOWINGS_NOTIFICATION", True)
    error_alerts_for(
        monkeypatch, tmp_path,
        [profile_snapshot(), snapshot(username="Renamed Person", followers=1, followings=1), snapshot(username="Renamed Person", followers=1, followings=1), RuntimeError("401 Unauthorized")],
        4,
        follower_answers=[{"sp_user_followers": [FIRST_FOLLOWER]}],
        initial_followers=[],
        following_answers=[{"sp_user_followings": []}, {"sp_user_followings": [SECOND_FOLLOWER]}],
        alert_log=alerts,
    )
    capsys.readouterr()
    return alerts


# Verifies a value taken from Spotify is escaped before it reaches the HTML body
def test_untrusted_text_is_escaped():
    assert monitor.html_text("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert monitor.html_text("line\nbreak") == "line<br>break"
    assert monitor.escape_html_attr('" onload="x') == "&quot; onload=&quot;x"


# Verifies a bare URL in an alert becomes a link while one already inside an attribute is left alone
def test_bare_urls_are_linked_once():
    assert monitor.html_autolink_urls("Guide: https://example.test/a") == 'Guide: <a href="https://example.test/a">https://example.test/a</a>'
    assert monitor.html_autolink_urls('<a href="https://example.test/a">x</a>') == '<a href="https://example.test/a">x</a>'


# Verifies the Discord body carries the email's emphasis and links instead of raw markup
def test_discord_markdown_mirrors_the_html_body():
    body_html = f'<html><head></head><body>Spotify user <b>{USER}</b> followers have changed<br><br>Guide: <a href="https://example.test/a">docs</a></body></html>'

    assert monitor.html_body_to_discord_markdown(body_html) == f"Spotify user **{USER}** followers have changed\n\nGuide: [docs](https://example.test/a)"


# Verifies the failure alert bolds its summary and the two values that say how bad the outage is
def test_the_failure_alert_bolds_its_summary_and_outage_fields(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    advice = monitor.make_recovery_advice("network.timeout", "Spotify did not answer in time", monitor.recovery_fix_with_guide("Retry later", "https://example.test/guide"), True)

    rendered = monitor.recovery_alert_body_html(advice, 60, 2, 1_700_000_000, with_timestamp=False)

    assert rendered.startswith("<html><head></head><body><b>Spotify did not answer in time</b><br><br>")
    assert 'Guide: <a href="https://example.test/guide">' in rendered
    assert "Failed checks in a row: <b>2</b>" in rendered
    assert "Failing since: <b>" in rendered
    # The retry delay is configured rather than observed, so it carries no emphasis
    assert "Next retry in: 1 minute" in rendered
    assert rendered.endswith("</body></html>")


# Verifies the timeline reaches both alert types, so the structural check is not silently narrow
def test_the_timeline_covers_the_profile_and_failure_alerts(timeline_alerts):
    assert {alert["type"] for alert in timeline_alerts} == {"profile", "followers_followings", "error"}


# Verifies every alert carries an HTML body next to its plain one
def test_every_alert_has_an_html_body(timeline_alerts):
    assert [alert["subject"] for alert in timeline_alerts if not alert["body_html"]] == []


# Verifies each HTML body reduces back to its plain body, so no line break was added or lost
def test_html_bodies_match_the_plain_text(timeline_alerts):
    mismatches = [f"{alert['type']}: {alert['subject']}\n{structural_diff(alert['body'], alert['body_html'])}" for alert in timeline_alerts if structural_diff(alert["body"], alert["body_html"])]

    assert mismatches == []


# Verifies every HTML body is one complete document, so no fragment reaches a mail client unwrapped
def test_html_bodies_are_complete_documents(timeline_alerts):
    for alert in timeline_alerts:
        assert alert["body_html"].startswith("<html><head></head><body>")
        assert alert["body_html"].endswith("</body></html>")


# Verifies the Discord body keeps the wording the ntfy body carries once its markers are removed
def test_discord_bodies_keep_the_plain_wording(timeline_alerts):
    for alert in timeline_alerts:
        discord = monitor.html_body_to_discord_markdown(alert["webhook_body_html"] or alert["body_html"])
        stripped = re.sub(r"\[([^\]]*)\]\((?:[^)]*)\)", r"\1", discord).replace("**", "").replace("*", "")
        plain = (alert["webhook_body"] or alert["body"]).strip()

        assert stripped in (plain, "\n".join(without_bracketed_url(line) for line in plain.split("\n")))


# Verifies the watched account is the bold subject of every alert that names it
def test_alerts_bold_the_account_they_name(timeline_alerts):
    for alert in timeline_alerts:
        if alert["type"] != "error":
            assert "<b>Watched Person</b>" in alert["body_html"] or "<b>Renamed Person</b>" in alert["body_html"]


# Writes the captured alerts as JSON when PREVIEW_ALERTS_JSON names a destination, so a preview tool can render them
@pytest.mark.skipif(not os.environ.get("PREVIEW_ALERTS_JSON"), reason="set PREVIEW_ALERTS_JSON to dump the alerts")
def test_dump_the_alerts_for_a_preview(timeline_alerts):
    dumped = [{**alert, "discord": monitor.html_body_to_discord_markdown(alert["webhook_body_html"] or alert["body_html"])} for alert in timeline_alerts]
    Path(os.environ["PREVIEW_ALERTS_JSON"]).write_text(json.dumps(dumped, indent=2), encoding="utf-8")
