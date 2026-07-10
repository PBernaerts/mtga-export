"""Resolve Arena grpIds to card data from the local Raw_CardDatabase SQLite."""

import re
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_RAW_DIR = Path(
    "~/.steam/steam/steamapps/common/MTGA/MTGA_Data/Downloads/Raw"
).expanduser()

# Arena set codes that differ from paper/Scryfall codes.
SET_REMAP = {"DAR": "DOM", "CONF": "CON"}

COLOR_MAP = {1: "W", 2: "U", 3: "B", 4: "R", 5: "G"}
RARITY_MAP = {1: "basic", 2: "common", 3: "uncommon", 4: "rare", 5: "mythic"}
_MANA_TOKEN = re.compile(r"o(\d+|[A-Z])")


@dataclass
class Card:
    grp_id: int
    name: str
    set_code: str
    collector_number: str
    rarity: str
    colors: list[str]
    mana_cost: str
    digital_only: bool
    rebalanced: bool


def find_card_db(raw_dir: Path = DEFAULT_RAW_DIR) -> Path:
    """Newest Raw_CardDatabase_*.mtga in raw_dir."""
    candidates = sorted(
        Path(raw_dir).glob("Raw_CardDatabase_*.mtga"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No Raw_CardDatabase_*.mtga found in {raw_dir} "
            "(is Arena installed via Steam? use --card-db to override)"
        )
    return candidates[-1]


def _mana_text(old_school: str) -> str:
    return "".join(f"{{{tok}}}" for tok in _MANA_TOKEN.findall(old_school))


class CardResolver:
    def __init__(self, db_path: Path):
        # Copy first: never open Steam's live file, even read-only.
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        shutil.copyfile(db_path, self._tmp.name)
        self._con = sqlite3.connect(f"file:{self._tmp.name}?mode=ro", uri=True)

    def resolve(self, grp_id: int) -> Card | None:
        row = self._con.execute(
            """
            SELECT c.GrpId, l.Loc, c.ExpansionCode, c.CollectorNumber,
                   c.Rarity, c.Colors, c.OldSchoolManaText,
                   c.IsDigitalOnly, c.IsRebalanced
            FROM Cards c
            JOIN Localizations_enUS l ON l.LocId = c.TitleId AND l.Formatted = 0
            WHERE c.GrpId = ?
            """,
            (grp_id,),
        ).fetchone()
        if row is None:
            return None
        (gid, name, set_code, cn, rarity, colors, mana, digital, rebal) = row
        set_code = SET_REMAP.get(set_code, set_code)
        color_list = [
            COLOR_MAP[int(x)] for x in colors.split(",") if x and int(x) in COLOR_MAP
        ]
        return Card(
            grp_id=gid,
            name=name,
            set_code=set_code,
            collector_number=cn,
            rarity=RARITY_MAP.get(rarity, str(rarity)),
            colors=color_list,
            mana_cost=_mana_text(mana),
            digital_only=bool(digital),
            rebalanced=bool(rebal),
        )

    def close(self):
        self._con.close()
        Path(self._tmp.name).unlink(missing_ok=True)
