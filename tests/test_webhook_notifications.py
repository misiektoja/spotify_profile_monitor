import argparse
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
from dotenv import dotenv_values
from PIL import Image

import spotify_profile_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "webhook_test_artifacts"


# Creates one disposable webhook test directory under the project local directory
def make_test_directory():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=str(ARTIFACT_ROOT))


class FakeResponse:
    # Initializes one response value used by the isolated transport tests
    def __init__(self, status_code=204, text="", headers=None, payload=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.payload = payload

    # Returns the configured JSON payload or raises when none was provided
    def json(self):
        if self.payload is None:
            raise ValueError("no JSON payload")
        return self.payload


class FakeDownloadResponse:
    # Initializes one streamed response from fixed bytes and headers
    def __init__(self, content, headers=None, status_code=200):
        self.content = content
        self.headers = headers or {"Content-Type": "image/png", "Content-Length": str(len(content))}
        self.status_code = status_code

    # Returns this response when entering its context manager
    def __enter__(self):
        return self

    # Leaves the response context without suppressing exceptions
    def __exit__(self, exc_type, exc_value, traceback):
        return False

    # Raises a requests error for unsuccessful status codes
    def raise_for_status(self):
        if self.status_code >= 400:
            raise monitor.req.HTTPError(f"HTTP {self.status_code}")

    # Yields the stored response body in requested chunk sizes
    def iter_content(self, chunk_size):
        for offset in range(0, len(self.content), chunk_size):
            yield self.content[offset:offset + chunk_size]


# Enables one valid profile webhook without affecting email settings
def configure_webhook(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/123/private-token")
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_USERNAME", "Spotify Profile Monitor")
    monkeypatch.setattr(monitor, "WEBHOOK_AVATAR_URL", "")
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {})
    monkeypatch.setattr(monitor, "WEBHOOK_TEMPLATE", {"username": "{username}", "avatar_url": "{avatar_url}", "allowed_mentions": {"parse": []}, "embeds": [{"title": "{title}", "description": "{description}", "color": "{color}"}]})
    monkeypatch.setattr(monitor, "WEBHOOK_TRANSFORMS", [])
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "")
    monkeypatch.setattr(monitor, "NTFY_IMAGES", False)
    monkeypatch.setattr(monitor, "WEBHOOK_PROFILE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)


# Verifies startup email and webhook summaries use compact single-line category rollups
def test_startup_notification_summaries_use_compact_rollups(monkeypatch):
    monkeypatch.setattr(monitor, "PROFILE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "FOLLOWERS_FOLLOWINGS_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROFILE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    expected_email = "* Notifications (email):        On (profile changes, followers/followings, errors)"
    expected_webhook = "* Notifications (webhook):      On (profile changes, followers/followings, errors)"
    assert monitor._startup_notification_summary_lines() == [expected_email, expected_webhook]


# Verifies disabled master and parent switches hide ineffective notification categories
def test_startup_notification_summaries_respect_master_switches(monkeypatch):
    monkeypatch.setattr(monitor, "PROFILE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "FOLLOWERS_FOLLOWINGS_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_PROFILE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    assert monitor._startup_notification_summary_lines() == ["* Notifications (email):        On (errors)", "* Notifications (webhook):      Off"]


# Verifies webhook URLs require complete HTTPS endpoints without embedded credentials
@pytest.mark.parametrize("url,expected", [("https://discord.com/api/webhooks/123/token", True), ("https://hooks.example.test/discord/path", True), ("http://discord.com/api/webhooks/123/token", False), ("https://user:password@example.test/hook", False), ("https://example.test", False), ("not-a-url", False), ("", False)])
def test_webhook_url_validation(url, expected):
    assert monitor.validate_webhook_url(url) is expected


@pytest.mark.parametrize("url,expected", [("https://discord.com/api/webhooks/123/token", "discord"), ("https://canary.discord.com/api/v10/webhooks/123/token", "discord"), ("https://ntfy.sh/private-topic", "ntfy"), ("https://ntfy.example.test/private-topic", ""), ("https://example.test/custom-hook", "")])
# Verifies distinctive Discord and public ntfy URLs select the proper payload provider
def test_webhook_provider_detection(url, expected):
    assert monitor.detect_webhook_provider(url) == expected


# Verifies private webhook entry requires a TTY and a writable dotenv destination
def test_set_webhook_url_requires_safe_persistence():
    with pytest.raises(monitor.WebhookConfigurationError, match="interactive terminal"):
        monitor.run_set_webhook_url(interactive=False, getpass_func=Mock(side_effect=AssertionError("prompted")))
    with pytest.raises(monitor.WebhookConfigurationError, match="requires a dotenv destination"):
        monitor.run_set_webhook_url(env_file="none", interactive=True, getpass_func=Mock(side_effect=AssertionError("prompted")))


# Verifies private setup persists only the webhook key after confirmation
def test_set_webhook_url_updates_only_secret(capsys):
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        destination.write_text("# keep\nUNRELATED=stay\nWEBHOOK_URL=old-value\n", encoding="utf-8")
        secret = "https://discord.com/api/webhooks/123/new-private-token"
        result = monitor.run_set_webhook_url(env_file=destination, interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: secret)
        output = capsys.readouterr().out
        assert result == str(destination.resolve())
        assert destination.read_text(encoding="utf-8").startswith("# keep\nUNRELATED=stay\n")
        assert dotenv_values(str(destination), interpolate=False) == {"UNRELATED": "stay", "WEBHOOK_URL": secret}
        assert secret not in output
        assert "--send-test-webhook" in output


# Verifies rejected private setup never writes or displays the entered URL
def test_set_webhook_url_rejects_invalid_secret_without_leak(capsys):
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        secret = "http://example.test/private-token"
        with pytest.raises(monitor.WebhookConfigurationError, match="complete HTTPS") as error:
            monitor.run_set_webhook_url(env_file=destination, interactive=True, getpass_func=lambda prompt: secret)
        assert secret not in capsys.readouterr().out
        assert secret not in str(error.value)
        assert not destination.exists()


# Verifies Discord payloads are bounded, mention-safe and secret-redacted
def test_webhook_payload_is_bounded_and_safe(monkeypatch):
    configure_webhook(monkeypatch)
    secret = monitor.WEBHOOK_URL
    payload = monitor.build_webhook_payload("@everyone " + ("t" * 300), f"failed at {secret} @here", "error")
    embed = payload["embeds"][0]
    assert len(embed["title"]) == monitor.WEBHOOK_EMBED_TITLE_LIMIT
    assert secret not in embed["description"]
    assert payload["allowed_mentions"] == {"parse": []}
    assert embed["color"] == 0xE74C3C


# Verifies templates, avatars, transforms and header placeholders share sanitized values
def test_advanced_webhook_customization(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_AVATAR_URL", "https://cdn.example.test/avatar.png")
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"X-Webhook-Title": "{title}", "X-Webhook-Version": "{version}"})
    monkeypatch.setattr(monitor, "WEBHOOK_TEMPLATE", {"content": "{title}: {description}", "avatar_url": "{avatar_url}", "color": "{color}", "allowed_mentions": {"parse": ["everyone"]}})
    monkeypatch.setattr(monitor, "WEBHOOK_TRANSFORMS", [("title", "replace", "secret", "masked"), ("description", "upper")])
    webhook_post = Mock(return_value=FakeResponse())
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("secret title", "custom body", "profile") == 0
    request = webhook_post.call_args
    assert request.kwargs["json"] == {"content": "masked title: CUSTOM BODY", "avatar_url": "https://cdn.example.test/avatar.png", "color": 0x1DB954, "allowed_mentions": {"parse": []}}
    assert request.kwargs["headers"]["X-Webhook-Title"] == "masked title"
    assert request.kwargs["headers"]["X-Webhook-Version"] == monitor.VERSION


# Verifies a string webhook template is delivered as a raw request body
def test_string_webhook_template_uses_raw_body(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_TEMPLATE", "{title}: {description}")
    webhook_post = Mock(return_value=FakeResponse())
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "profile") == 0
    assert webhook_post.call_args.kwargs["data"] == "Title: Body"
    assert "json" not in webhook_post.call_args.kwargs


# Verifies formatted headers are validated again before network delivery
def test_formatted_webhook_headers_reject_line_breaks(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"X-Description": "{description}"})
    webhook_post = Mock(side_effect=AssertionError("webhook request attempted"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "first\nsecond", "profile") == 1
    webhook_post.assert_not_called()


# Verifies one successful webhook uses the isolated session
def test_successful_webhook_uses_isolated_session(monkeypatch):
    configure_webhook(monkeypatch)
    webhook_post = Mock(return_value=FakeResponse())
    spotify_post = Mock(side_effect=AssertionError("Spotify session used"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    monkeypatch.setattr(monitor.SESSION, "post", spotify_post)
    assert monitor.send_webhook("Title", "Body", "profile") == 0
    assert webhook_post.call_count == 1
    assert webhook_post.call_args.kwargs["timeout"] == monitor.WEBHOOK_TIMEOUT_SECONDS
    spotify_post.assert_not_called()


# Verifies ntfy receives a native UTF-8 message with its title in query parameters
def test_successful_ntfy_webhook_uses_native_topic_api(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.sh/private-topic?auth=private-auth-value")
    webhook_post = Mock(return_value=FakeResponse(200))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Spotify title \u017c\u00f3\u0142\u0107", "Profile: Bj\u00f6rk", "profile") == 0
    request = webhook_post.call_args
    assert request.args == ("https://ntfy.sh/private-topic?auth=private-auth-value",)
    assert request.kwargs["data"] == "Profile: Bj\u00f6rk".encode("utf-8")
    assert request.kwargs["params"] == {"title": "Spotify title \u017c\u00f3\u0142\u0107"}
    assert request.kwargs["headers"]["Content-Type"] == "text/plain; charset=utf-8"
    assert "json" not in request.kwargs


# Verifies long ntfy messages stay below the server attachment boundary with a visible truncation marker
def test_ntfy_message_stays_below_attachment_boundary():
    title, message = monitor.build_ntfy_webhook_message("Spotify title", ("a" * monitor.NTFY_MESSAGE_LIMIT_BYTES) + "\U0001f3b5")
    assert title == "Spotify title"
    assert message.endswith(monitor.NTFY_TRUNCATION_SUFFIX)
    assert len(message.encode("utf-8")) <= monitor.NTFY_MESSAGE_LIMIT_BYTES
    assert len(message.encode("utf-8")) < 4096
    assert "\ufffd" not in message


# Verifies a private ntfy token overrides custom authentication headers
def test_ntfy_access_token_uses_bearer_authentication(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.example.test/private-topic")
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"authorization": "Basic older-value", "Content-Type": "application/json", "X-Priority": "high"})
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "tk_private_access_token")
    webhook_post = Mock(return_value=FakeResponse(200))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "profile") == 0
    headers = webhook_post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer tk_private_access_token"
    assert "authorization" not in headers
    assert headers["Content-Type"] == "text/plain; charset=utf-8"
    assert headers["X-Priority"] == "high"


# Verifies ntfy artwork is downloaded with bounds and converted in memory
def test_ntfy_image_is_bounded_and_built_in_memory(monkeypatch):
    source = BytesIO()
    Image.new("RGB", (320, 640), (12, 34, 56)).save(source, format="PNG")
    image_get = Mock(return_value=FakeDownloadResponse(source.getvalue()))
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "get", image_get)
    result = monitor.build_ntfy_image("https://i.scdn.co/image/profile.png")
    assert isinstance(result, bytes)
    with Image.open(BytesIO(result)) as output:
        assert output.format == "JPEG"
        assert output.size == (400, 160)
    assert image_get.call_args.kwargs["allow_redirects"] is False
    assert image_get.call_args.kwargs["stream"] is True


# Verifies image downloads cannot target arbitrary hosts
def test_ntfy_image_rejects_non_spotify_hosts(monkeypatch):
    image_get = Mock(side_effect=AssertionError("untrusted image host contacted"))
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "get", image_get)
    assert monitor.build_ntfy_image("https://127.0.0.1/private-image.jpg") is None
    assert monitor.build_ntfy_image("https://evilscdn.co/private-image.jpg") is None
    image_get.assert_not_called()


# Verifies a successful ntfy artwork upload retains authentication and metadata
def test_successful_ntfy_image_upload_preserves_headers(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.example.test/private-topic")
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "tk_private_access_token")
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor, "build_ntfy_image", Mock(return_value=b"jpeg-data"))
    webhook_post = Mock(return_value=FakeResponse(200))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "profile", image_url="https://i.scdn.co/image/profile.jpg") == 0
    request = webhook_post.call_args
    assert request.kwargs["data"] == b"jpeg-data"
    assert request.kwargs["params"] == {"title": "Title", "message": "Body"}
    assert request.kwargs["headers"]["Authorization"] == "Bearer tk_private_access_token"
    assert request.kwargs["headers"]["Content-Type"] == "image/jpeg"
    assert request.kwargs["headers"]["X-Filename"] == monitor.NTFY_IMAGE_FILENAME


# Verifies rejected artwork uploads retry once as text
@pytest.mark.parametrize("first_result,expected_sleeps", [(FakeResponse(400, "bad attachment"), []), (monitor.req.ConnectionError("upload failed"), [monitor.WEBHOOK_FALLBACK_RETRY_SECONDS])])
def test_ntfy_image_upload_failure_falls_back_to_text(monkeypatch, first_result, expected_sleeps):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.example.test/private-topic")
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor, "build_ntfy_image", Mock(return_value=b"jpeg-data"))
    webhook_post = Mock(side_effect=[first_result, FakeResponse(200)])
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    sleeps = []
    assert monitor.send_webhook("Title", "Body", "profile", image_url="https://i.scdn.co/image/profile.jpg", sleeper=sleeps.append) == 0
    assert webhook_post.call_args_list[0].kwargs["data"] == b"jpeg-data"
    assert webhook_post.call_args_list[1].kwargs["data"] == b"Body"
    assert sleeps == expected_sleeps


# Verifies rate-limit retries use a bounded server delay
def test_rate_limit_retry_is_bounded(monkeypatch):
    configure_webhook(monkeypatch)
    webhook_post = Mock(side_effect=[FakeResponse(429, headers={"Retry-After": "999"}), FakeResponse(204)])
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    sleeps = []
    assert monitor.send_webhook("Title", "Body", "profile", sleeper=sleeps.append) == 0
    assert sleeps == [monitor.WEBHOOK_MAX_RETRY_AFTER_SECONDS]


# Verifies webhook failures redact the configured destination
def test_webhook_failure_redacts_private_url(monkeypatch, capsys):
    configure_webhook(monkeypatch)
    secret = monitor.WEBHOOK_URL
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", Mock(return_value=FakeResponse(400, text=f"rejected {secret}")))
    assert monitor.send_webhook("Title", "Body", "profile") == 1
    output = capsys.readouterr().out
    assert secret not in output
    assert "<redacted>" in output


# Verifies email and webhook delivery remain independent
def test_notification_channels_are_independent(monkeypatch):
    configure_webhook(monkeypatch)
    email = Mock(return_value=1)
    webhook = Mock(return_value=0)
    monkeypatch.setattr(monitor, "send_email", email)
    monkeypatch.setattr(monitor, "send_webhook", webhook)
    assert monitor.send_notification_channels("profile", "Title", "Body", email_enabled=True) == (True, True)
    email.assert_called_once()
    webhook.assert_called_once()


# Verifies a follower event can use webhook delivery while email is disabled
def test_follower_change_uses_webhook_without_email(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    webhook = Mock(return_value=0)
    email = Mock(side_effect=AssertionError("email attempted"))
    monkeypatch.setattr(monitor, "send_webhook", webhook)
    monkeypatch.setattr(monitor, "send_email", email)
    current = [{"name": "New Follower", "uri": "spotify:user:new-follower"}]
    with patch("builtins.open", mock_open()), patch("builtins.print"):
        monitor.spotify_print_changed_followers_followings_playlists("user", current, [], 1, 0, "Followers", "for", "Added followers", "Added Follower", "Removed followers", "Removed Follower", "state.json", None, False, False, notification_image_url="https://i.scdn.co/image/profile.jpg", webhook_notification_allowed=True)
    webhook.assert_called_once()
    assert webhook.call_args.args[2] == "followers_followings"
    assert webhook.call_args.kwargs["image_url"] == "https://i.scdn.co/image/profile.jpg"
    email.assert_not_called()


# Verifies follower alerts require both profile and follower event switches
def test_follower_webhook_event_switches(monkeypatch):
    configure_webhook(monkeypatch)
    assert monitor.webhook_event_enabled("followers_followings") is True
    monkeypatch.setattr(monitor, "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION", False)
    assert monitor.webhook_event_enabled("followers_followings") is False
    monkeypatch.setattr(monitor, "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROFILE_NOTIFICATION", False)
    assert monitor.webhook_event_enabled("followers_followings") is False


# Verifies runtime webhook options enable only their selected settings
def test_webhook_cli_overrides(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "your_webhook_url")
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_PROFILE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    args = argparse.Namespace(webhook_provider="ntfy", webhook_url="https://ntfy.sh/private-topic", webhook_enabled=None, webhook_profile=True, webhook_followers_followings=False, webhook_errors=False)
    monitor.apply_webhook_cli_overrides(args, argparse.ArgumentParser())
    assert monitor.WEBHOOK_ENABLED is True
    assert monitor.WEBHOOK_PROVIDER == "ntfy"
    assert monitor.WEBHOOK_URL == "https://ntfy.sh/private-topic"
    assert monitor.WEBHOOK_PROFILE_NOTIFICATION is True
    assert monitor.WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION is False
    assert monitor.WEBHOOK_ERROR_NOTIFICATION is False


# Verifies a known ntfy URL corrects a stale configured provider and sends native text
def test_runtime_provider_detection_corrects_config_mismatch(monkeypatch, capsys):
    configure_webhook(monkeypatch)
    args = argparse.Namespace(webhook_provider=None, webhook_url="https://ntfy.sh/private-topic", webhook_enabled=None, webhook_profile=None, webhook_followers_followings=None, webhook_errors=None)
    monitor.apply_webhook_cli_overrides(args, argparse.ArgumentParser())
    assert monitor.WEBHOOK_PROVIDER == "ntfy"
    assert "Using ntfy" in capsys.readouterr().out
    webhook_post = Mock(return_value=FakeResponse(200))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Spotify title", "Native body", "profile", force=True) == 0
    request = webhook_post.call_args
    assert request.kwargs["data"] == b"Native body"
    assert "json" not in request.kwargs


# Verifies generated configuration contains the complete advanced webhook block
def test_generated_config_includes_webhook_settings():
    namespace = {}
    exec(monitor.CONFIG_BLOCK, namespace)
    assert namespace["WEBHOOK_PROVIDER"] == "discord"
    assert namespace["WEBHOOK_USERNAME"] == "Spotify Profile Monitor"
    assert namespace["WEBHOOK_HEADERS"] == {}
    assert namespace["WEBHOOK_TEMPLATE"]["allowed_mentions"] == {"parse": []}
    assert namespace["WEBHOOK_TRANSFORMS"] == []
    assert namespace["NTFY_ACCESS_TOKEN"] == ""
    assert namespace["NTFY_IMAGES"] is True
