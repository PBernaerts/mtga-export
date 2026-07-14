"""Resolve Arena grpIds to card data from the local Raw_CardDatabase SQLite."""

import re
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Steam roots to search, in order. ~/.steam/steam is often a symlink to
# ~/.local/share/Steam; duplicates are collapsed by resolved path.
STEAM_ROOTS = [
    Path("~/.steam/steam"),
    Path("~/.local/share/Steam"),
    Path("~/.var/app/com.valvesoftware.Steam/.local/share/Steam"),
]
RAW_SUBPATH = Path("steamapps/common/MTGA/MTGA_Data/Downloads/Raw")
_VDF_PATH = re.compile(r'"path"\s+"([^"]+)"')

# Arena set codes that differ from paper/Scryfall codes.
SET_REMAP = {"DAR": "DOM", "CONF": "CON"}

COLOR_MAP = {1: "W", 2: "U", 3: "B", 4: "R", 5: "G"}
RARITY_MAP = {1: "basic", 2: "common", 3: "uncommon", 4: "rare", 5: "mythic"}
# Arena wraps multi-part symbols such as hybrid and Phyrexian mana in
# parentheses (for example, "o(G/W)" and "o(W/P)").
_MANA_TOKEN = re.compile(r"o(?:\(([^)]+)\)|(\d+|[A-Z]))")
# Formatted=1 titles may embed markup like <nobr>...</nobr>; strip any tags.
_TAG = re.compile(r"<[^>]+>")


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


def _steam_libraries(root: Path) -> list[Path]:
    """The Steam root itself plus extra library folders from libraryfolders.vdf."""
    libs = [root]
    vdf = root / "steamapps" / "libraryfolders.vdf"
    if vdf.is_file():
        try:
            text = vdf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return libs
        libs += [Path(m) for m in _VDF_PATH.findall(text)]
    return libs


def find_card_db(raw_dir: Path | None = None) -> Path:
    """Newest Raw_CardDatabase_*.mtga. Searches raw_dir if given, otherwise
    every known Steam root and its extra library folders."""
    if raw_dir is not None:
        raw_dirs = [Path(raw_dir)]
    else:
        roots = [r.expanduser() for r in STEAM_ROOTS]
        raw_dirs = [
            lib / RAW_SUBPATH
            for root in roots
            if root.is_dir()
            for lib in _steam_libraries(root)
        ] or [root / RAW_SUBPATH for root in roots]
    candidates = {
        p.resolve(): p for d in raw_dirs for p in d.glob("Raw_CardDatabase_*.mtga")
    }
    if not candidates:
        searched = "\n  ".join(str(d) for d in raw_dirs)
        raise FileNotFoundError(
            "No Raw_CardDatabase_*.mtga found. Searched:\n  "
            f"{searched}\n"
            "Is MTG Arena installed via Steam? For other installs "
            "(Lutris, custom Wine prefix) pass --card-db."
        )
    return max(candidates.values(), key=lambda p: p.stat().st_mtime)


def _mana_text(old_school: str) -> str:
    return "".join(
        f"{{{parenthesized or simple}}}"
        for parenthesized, simple in _MANA_TOKEN.findall(old_school)
    )


class CardResolver:
    def __init__(self, db_path: Path):
        # Copy first: never open Steam's live file, even read-only.
        # delete=True: on Linux the named file persists until self._tmp.close(),
        # and sqlite can open it by name; closing the handle deletes the file.
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite")
        try:
            shutil.copyfile(db_path, self._tmp.name)
            self._con = sqlite3.connect(f"file:{self._tmp.name}?mode=ro", uri=True)
        except BaseException:
            self._tmp.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def resolve(self, grp_id: int) -> Card | None:
        row = self._con.execute(
            """
            SELECT c.GrpId, l.Loc, c.ExpansionCode, c.CollectorNumber,
                   c.Rarity, c.Colors, c.OldSchoolManaText,
                   c.IsDigitalOnly, c.IsRebalanced
            FROM Cards c
            JOIN Localizations_enUS l ON l.LocId = c.TitleId
            WHERE c.GrpId = ?
            ORDER BY l.Formatted
            LIMIT 1
            """,
            (grp_id,),
        ).fetchone()
        if row is None:
            return None
        (gid, name, set_code, cn, rarity, colors, mana, digital, rebal) = row
        # Coalesce NULLs defensively: the DB schema has shifted between Arena
        # updates before, and one bad row must not take the whole export down.
        name = _TAG.sub("", name or "")
        if not name:
            return None
        set_code = SET_REMAP.get(set_code, set_code or "")
        color_list = [
            COLOR_MAP[int(x)]
            for x in (colors or "").split(",")
            if x and int(x) in COLOR_MAP
        ]
        return Card(
            grp_id=gid,
            name=name,
            set_code=set_code,
            collector_number=cn or "",
            rarity=RARITY_MAP.get(rarity, str(rarity)),
            colors=color_list,
            mana_cost=_mana_text(mana or ""),
            digital_only=bool(digital),
            rebalanced=bool(rebal),
        )

    def close(self):
        self._con.close()
        self._tmp.close()  # deletes the temp copy
