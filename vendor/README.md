# Vendored: mtga-tracker-daemon

- Version: 1.0.11.0 (Linux release), pinned in `scripts/fetch-daemon.sh`
- Upstream: https://github.com/frcaton/mtga-tracker-daemon
- License: GPL-3.0 (see the upstream `LICENSE` file)

The binaries are not committed to this repo. Run `scripts/fetch-daemon.sh`
from the repo root to download the pinned release into `bin/` (sha256-verified).

mtga-export spawns this binary to read the collection from the running
Arena process over http://localhost:6842.

To update: bump VERSION and SHA256 in `scripts/fetch-daemon.sh`, re-run it,
and re-run the integration test (`pytest -m integration` with Arena running).
