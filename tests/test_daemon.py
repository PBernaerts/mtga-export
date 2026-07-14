import pytest

from mtga_export.daemon import DaemonClient, DaemonError


def test_status(stub_daemon):
    url, _ = stub_daemon
    c = DaemonClient(base_url=url)
    s = c.status()
    assert s["isRunning"] is True
    assert s["daemonVersion"] == "1.0.11.0"


def test_get_cards(stub_daemon):
    url, _ = stub_daemon
    assert DaemonClient(base_url=url).get_cards() == {67330: 4, 75450: 1}


def test_arena_not_running_raises(stub_daemon):
    url, responses = stub_daemon
    responses["/status"]["isRunning"] = False
    with pytest.raises(DaemonError, match="Arena"):
        DaemonClient(base_url=url).get_cards()


def test_invalid_json_raises_daemon_error(stub_daemon):
    url, responses = stub_daemon
    responses["/status"] = b"<html>not json</html>"
    c = DaemonClient(base_url=url)
    with pytest.raises(DaemonError, match="invalid JSON"):
        c.status()
    assert c.reachable() is False


def test_daemon_unreachable():
    c = DaemonClient(base_url="http://127.0.0.1:1", timeout=0.2)
    assert c.reachable() is False


@pytest.mark.integration
def test_real_daemon_roundtrip():
    """Needs MTG Arena running. Spawns the vendored daemon if needed."""
    from mtga_export.daemon import daemon_session

    try:
        with daemon_session() as client:
            cards = client.get_cards()
    except DaemonError as e:
        pytest.skip(f"Arena not running: {e}")
    assert len(cards) > 100
    assert all(isinstance(k, int) and v >= 1 for k, v in cards.items())


def test_malformed_cards_payload_raises_daemon_error(stub_daemon):
    url, responses = stub_daemon
    responses["/cards"] = {"unexpected": "shape"}
    with pytest.raises(DaemonError, match="/cards"):
        DaemonClient(base_url=url).get_cards()


def test_daemon_error_payload_preserves_message(stub_daemon):
    url, responses = stub_daemon
    responses["/cards"] = {"error": "memory read failed"}
    with pytest.raises(
        DaemonError, match=r"^daemon error from /cards: memory read failed$"
    ):
        DaemonClient(base_url=url).get_cards()


def test_non_dict_payload_raises_daemon_error(stub_daemon):
    url, responses = stub_daemon
    responses["/status"] = [1, 2, 3]
    c = DaemonClient(base_url=url)
    with pytest.raises(DaemonError, match="unexpected payload"):
        c.status()
    assert c.reachable() is False


def test_spawn_refuses_custom_url(tmp_path):
    from mtga_export.daemon import daemon_session

    with pytest.raises(DaemonError, match="no-spawn"):
        with daemon_session(
            binary=tmp_path / "missing", base_url="http://127.0.0.1:1"
        ):
            pass


def test_spawn_binary_missing(tmp_path, monkeypatch):
    import mtga_export.daemon as daemon

    monkeypatch.setattr(daemon, "DEFAULT_URL", "http://127.0.0.1:1")
    with pytest.raises(DaemonError, match="not found"):
        with daemon.daemon_session(
            binary=tmp_path / "missing", base_url="http://127.0.0.1:1"
        ):
            pass


def test_spawn_failure_includes_daemon_output(tmp_path, monkeypatch):
    import mtga_export.daemon as daemon

    monkeypatch.setattr(daemon, "DEFAULT_URL", "http://127.0.0.1:1")
    monkeypatch.setattr(daemon, "START_TIMEOUT", 2.0)
    binary = tmp_path / "fake-daemon"
    binary.write_text("#!/bin/sh\necho boom-diagnostic >&2\nexit 3\n")
    binary.chmod(0o755)
    with pytest.raises(DaemonError, match="boom-diagnostic"):
        with daemon.daemon_session(binary=binary, base_url="http://127.0.0.1:1"):
            pass


def test_spawn_non_executable_binary(tmp_path, monkeypatch):
    import mtga_export.daemon as daemon

    monkeypatch.setattr(daemon, "DEFAULT_URL", "http://127.0.0.1:1")
    binary = tmp_path / "fake-daemon"
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o644)
    with pytest.raises(DaemonError, match="cannot execute"):
        with daemon.daemon_session(binary=binary, base_url="http://127.0.0.1:1"):
            pass
