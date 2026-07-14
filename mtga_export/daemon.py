"""Client + lifecycle for mtga-tracker-daemon."""

import contextlib
import json
import subprocess
import tempfile
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
            data = json.loads(body)
        except ValueError as e:
            raise DaemonError(
                f"daemon returned invalid JSON from {endpoint}: {e}"
            ) from e
        if not isinstance(data, dict):
            raise DaemonError(
                f"daemon returned unexpected payload from {endpoint}: {data!r}"
            )
        if "error" in data:
            raise DaemonError(f"daemon error from {endpoint}: {data['error']}")
        return data

    def reachable(self) -> bool:
        """True if something answering like mtga-tracker-daemon is at base_url."""
        try:
            return "daemonVersion" in self._get("/status")
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
        try:
            return {c["grpId"]: c["owned"] for c in data["cards"]}
        except (KeyError, TypeError) as e:
            raise DaemonError(f"unexpected /cards payload from daemon: {e}") from e


@contextlib.contextmanager
def daemon_session(binary: Path = VENDORED_BINARY, base_url: str = DEFAULT_URL):
    """Yield a ready DaemonClient. Reuses a running daemon, else spawns the
    vendored binary and terminates it on exit."""
    client = DaemonClient(base_url=base_url)
    if client.reachable():
        yield client
        return
    if base_url.rstrip("/") != DEFAULT_URL:
        raise DaemonError(
            f"no daemon at {base_url}, and the bundled daemon only listens on "
            f"{DEFAULT_URL} — a custom --daemon-url requires --no-spawn"
        )
    if not binary.exists():
        raise DaemonError(
            f"daemon binary not found: {binary}\n"
            "Run scripts/fetch-daemon.sh from the repo root to download it."
        )
    log = tempfile.TemporaryFile()
    try:
        try:
            proc = subprocess.Popen(
                [str(binary)], cwd=binary.parent,
                stdout=log, stderr=subprocess.STDOUT,
            )
        except OSError as e:
            raise DaemonError(
                f"cannot execute daemon binary {binary}: {e}\n"
                "The daemon is an x86-64 glibc Linux binary; if the file is "
                "present but not executable, chmod +x it or re-run "
                "scripts/fetch-daemon.sh."
            ) from e
        try:
            deadline = time.monotonic() + START_TIMEOUT
            while not client.reachable():
                if time.monotonic() > deadline or proc.poll() is not None:
                    log.seek(0)
                    tail = log.read()[-2000:].decode(errors="replace").strip()
                    raise DaemonError(
                        "mtga-tracker-daemon failed to start"
                        + (f"; daemon output:\n{tail}" if tail else "")
                    )
                time.sleep(0.3)
            yield client
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    finally:
        log.close()
