"""Client + lifecycle for mtga-tracker-daemon."""

import contextlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_URL = "http://localhost:6842"
VENDORED_BINARY = (
    Path(__file__).resolve().parent.parent
    / "vendor" / "mtga-tracker-daemon" / "bin" / "mtga-tracker-daemon"
)
START_TIMEOUT = 15.0


class DaemonError(RuntimeError):
    pass


class DaemonClient:
    def __init__(self, base_url: str = DEFAULT_URL, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, endpoint: str) -> dict:
        try:
            with urllib.request.urlopen(
                f"{self.base_url}{endpoint}", timeout=self.timeout
            ) as resp:
                body = resp.read()
        except (urllib.error.URLError, OSError) as e:
            raise DaemonError(f"daemon unreachable at {self.base_url}: {e}") from e
        try:
            return json.loads(body)
        except ValueError as e:
            raise DaemonError(
                f"daemon returned invalid JSON from {endpoint}: {e}"
            ) from e

    def reachable(self) -> bool:
        try:
            self._get("/status")
            return True
        except DaemonError:
            return False

    def status(self) -> dict:
        return self._get("/status")

    def get_cards(self) -> dict[int, int]:
        if not self.status().get("isRunning"):
            raise DaemonError(
                "MTG Arena process not found. Launch Arena and try again."
            )
        data = self._get("/cards")
        return {c["grpId"]: c["owned"] for c in data["cards"]}


@contextlib.contextmanager
def daemon_session(binary: Path = VENDORED_BINARY, base_url: str = DEFAULT_URL):
    """Yield a ready DaemonClient. Reuses a running daemon, else spawns the
    vendored binary and terminates it on exit."""
    client = DaemonClient(base_url=base_url)
    if client.reachable():
        yield client
        return
    if not binary.exists():
        raise DaemonError(f"daemon binary not found: {binary}")
    proc = subprocess.Popen(
        [str(binary)], cwd=binary.parent,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + START_TIMEOUT
        while not client.reachable():
            if time.monotonic() > deadline or proc.poll() is not None:
                raise DaemonError("mtga-tracker-daemon failed to start")
            time.sleep(0.3)
        yield client
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
