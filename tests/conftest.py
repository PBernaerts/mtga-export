import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest


@pytest.fixture
def card_db(tmp_path):
    """Minimal Raw_CardDatabase clone with real rows from the 2026-07-10 snapshot."""
    path = tmp_path / "Raw_CardDatabase_test.mtga"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE Cards(
            GrpId INT UNIQUE PRIMARY KEY NOT NULL,
            TitleId INT NOT NULL,
            ExpansionCode TEXT,
            CollectorNumber TEXT,
            Rarity INT,
            Colors TEXT,
            Types TEXT,
            OldSchoolManaText TEXT,
            IsRebalanced BOOLEAN NOT NULL,
            IsDigitalOnly BOOLEAN NOT NULL,
            IsToken BOOLEAN NOT NULL,
            IsPrimaryCard BOOLEAN NOT NULL
        );
        CREATE TABLE Localizations_enUS(
            LocId INT NOT NULL, Formatted INT NOT NULL, Loc TEXT,
            PRIMARY KEY (LocId, Formatted)
        );
        """
    )
    rows = [
        # grpId, titleId, set, cn, rarity, colors, types, mana, rebal, digital, token, primary
        (75450, 1001, "ANB", "9", 3, "1", "2", "o1oW", 0, 1, 0, 1),      # Hallowed Priest, Arena-only set
        (67330, 1002, "DAR", "168", 2, "5", "2", "oG", 0, 0, 0, 1),      # Llanowar Elves, DAR→DOM remap
        (90001, 1003, "YMID", "A-25", 4, "2", "2", "o1oU", 1, 1, 0, 1),  # rebalanced Alchemy card
        (80100, 1004, "NEO", "45", 5, "2,3", "2,3", "oXoUoB", 0, 0, 0, 1),  # multicolor mythic
        (81000, 1005, "NEO", "240", 2, "", "1", "o2", 0, 0, 0, 1),          # colorless artifact
        (82000, 1006, "FDN", "100", 2, "1", "2", "o1", 0, 0, 0, 1),         # Formatted=1-only title
        (82001, 1007, "FDN", "101", 2, "1", "2", "o1", 0, 0, 0, 1),         # both Formatted variants
        # NULL-heavy row: the real schema allows NULLs and has shifted
        # between Arena updates; resolution must not crash on one.
        (83000, 1008, None, None, None, None, None, None, 0, 0, 0, 1),
    ]
    con.executemany("INSERT INTO Cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    names = [(1001, 0, "Hallowed Priest"), (1002, 0, "Llanowar Elves"),
             (1003, 0, "A-Test Card"), (1004, 0, "Test Mythic"),
             (1005, 0, "Test Artifact"),
             # 1006 has NO Formatted=0 row (like most real cards) and carries markup
             (1006, 1, "<nobr>Half-Elf</nobr> Monk"),
             # 1007 has both variants; Formatted=0 must win
             (1007, 0, "Plain Name"), (1007, 1, "<i>Fancy</i> Name"),
             (1008, 0, "Null Heavy Card")]
    con.executemany("INSERT INTO Localizations_enUS VALUES (?,?,?)", names)
    con.commit()
    con.close()
    return path


@pytest.fixture
def stub_daemon():
    responses = {
        "/status": {"isRunning": True, "daemonVersion": "1.0.11.0",
                    "updating": False, "processId": 123},
        "/cards": {"cards": [{"grpId": 67330, "owned": 4},
                             {"grpId": 75450, "owned": 1}]},
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            payload = responses.get(self.path, {})
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}", responses
    srv.shutdown()
