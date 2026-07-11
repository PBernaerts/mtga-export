# Vendored: mtga-tracker-daemon

- Version: 1.0.11.0 (Linux release)
- Upstream: https://github.com/frcaton/mtga-tracker-daemon
- Source: https://github.com/frcaton/mtga-tracker-daemon/releases/download/1.0.11.0/mtga-tracker-daemon-Linux.tar.gz
- License: upstream repo (MIT)
- Why vendored: mtga-export spawns this binary to read the collection from
  the running Arena process. Verified working on Arch + Steam/Proton as a
  regular user on 2026-07-10.

To update: download the new Linux release, replace `bin/`, update this file,
and re-run the integration test (`pytest -m integration` with Arena running).
