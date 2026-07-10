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
