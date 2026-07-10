import sqlite3
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
            CollectorNumber TEXT NOT NULL,
            Rarity INT NOT NULL,
            Colors TEXT NOT NULL,
            Types TEXT NOT NULL,
            OldSchoolManaText TEXT NOT NULL,
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
    ]
    con.executemany("INSERT INTO Cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    names = [(1001, 0, "Hallowed Priest"), (1002, 0, "Llanowar Elves"),
             (1003, 0, "A-Test Card"), (1004, 0, "Test Mythic"),
             (1005, 0, "Test Artifact")]
    con.executemany("INSERT INTO Localizations_enUS VALUES (?,?,?)", names)
    con.commit()
    con.close()
    return path
