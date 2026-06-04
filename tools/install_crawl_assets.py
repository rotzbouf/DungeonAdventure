"""
Install Dungeon Crawl Stone Soup sprites into assets/.

Copies selected 32×32 PNGs from the DCSS tilesets into the paths that
src/assets.py expects.  Scales nothing — the AssetManager handles that
at load time via pygame.transform.smoothscale.

Usage:
    python tools/install_crawl_assets.py

The script is idempotent — re-running it just overwrites with the same files.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from PIL import Image

ROOT   = Path(__file__).parent.parent
FULL   = ROOT / "assets" / "Dungeon Crawl Stone Soup Full"   # newer full pack
OLD    = ROOT / "assets" / "crawl-tiles Oct-5-2010"           # older pack (fallback)
OUT    = ROOT / "assets"

# ── helpers ───────────────────────────────────────────────────────────────────

def src(*parts: str) -> Path:
    """Return the path from the FULL pack, falling back to the old pack."""
    p = FULL.joinpath(*parts)
    if p.exists():
        return p
    p2 = OLD.joinpath(*parts)
    if p2.exists():
        return p2
    raise FileNotFoundError(f"Neither FULL nor old pack has: {'/'.join(parts)}")


def copy(source: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    print(f"  {dest.relative_to(ROOT)}")


def copy_scaled(source: Path, dest: Path, size: tuple[int, int]):
    """Copy a PNG, scaling it to *size* with high-quality Lanczos resampling."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(source).convert("RGBA")
    img = img.resize(size, Image.LANCZOS)
    img.save(dest)
    print(f"  {dest.relative_to(ROOT)}  (scaled {img.size})")


# ── Player sprites ─────────────────────────────────────────────────────────────

def install_player():
    print("\n[Player]")
    base = src("player", "base", "human_male.png")
    img  = Image.open(base).convert("RGBA")

    out_dir = OUT / "sprites"
    out_dir.mkdir(parents=True, exist_ok=True)

    # DCSS human_male.png is a top-down sprite (viewed from above).
    # In top-down view, the character is always "upright" — rotating it 90°
    # makes it look like the player is lying flat, and flipping vertically
    # makes them appear upside-down.  The correct approach:
    #
    #   South  — original (character naturally faces toward camera)
    #   North  — same sprite  (top-down: the figure looks the same going away)
    #   East   — flip horizontally  (natural mirror, character appears to face right)
    #   West   — flip horizontally back (or same as south; character faces left)
    #
    # Attack arc + weapon angle communicate the actual movement direction;
    # the sprite just keeps the character looking upright at all times.

    img_flip = img.transpose(Image.FLIP_LEFT_RIGHT)

    img.save(out_dir / "player_south.png");      print(f"  sprites/player_south.png")
    img.save(out_dir / "player_north.png");      print(f"  sprites/player_north.png")
    img_flip.save(out_dir / "player_east.png");  print(f"  sprites/player_east.png")
    img.save(out_dir / "player_west.png");       print(f"  sprites/player_west.png")


# ── Enemy sprites ──────────────────────────────────────────────────────────────

_ENEMY_MAP: dict[str, tuple[str, ...]] = {
    "goblin":       ("monster", "goblin.png"),
    "skeleton":     ("monster", "undead", "skeletal_warrior.png"),
    "orc":          ("monster", "orc_knight.png"),
    "demon":        ("monster", "demons", "fiend.png"),
    # Bosses
    "lich":         ("monster", "undead", "lich.png"),
    "demonlord":    ("monster", "demons", "balrug.png"),
    "stonegolem":   ("monster", "nonliving", "stone_golem.png"),
    "vampirelord":  ("monster", "undead", "vampire_knight.png"),
    "elderdragon":  ("monster", "dragons", "golden_dragon.png"),
    "ironcolossus": ("monster", "nonliving", "iron_golem.png"),
}

def install_enemies():
    print("\n[Enemies]")
    out = OUT / "sprites" / "enemies"
    out.mkdir(parents=True, exist_ok=True)
    for name, path_parts in _ENEMY_MAP.items():
        try:
            s = src(*path_parts)
            copy(s, out / f"{name}.png")
        except FileNotFoundError as e:
            print(f"  SKIP {name}: {e}")


# ── Tile textures ──────────────────────────────────────────────────────────────

TILE_SIZE = 40   # must match settings.TILE_SIZE

# Per-theme floor and wall tile series from DCSS
# Each entry: (floor_glob_pattern, wall_glob_pattern, floor_prefix, wall_prefix, n_variants)
_TILE_MAP = {
    #          floor files                  wall files
    "dungeon":  (("dungeon", "floor"),  "grey_dirt",         ("dungeon", "wall"), "stone_gray",     4),
    "crypt":    (("dungeon", "floor"),  "black_cobalt",      ("dungeon", "wall"), "catacombs",      4),
    "forge":    (("dungeon", "floor"),  "floor_sand_stone",  ("dungeon", "wall"), "brick_brown",    4),
    "inferno":  (("dungeon", "floor"),  "lair",              ("dungeon", "wall"), "volcanic_wall",  4),
    "abyss":    (("dungeon", "floor"),  "grey_dirt_b",       ("dungeon", "wall"), "cobalt_stone",   4),
}

def _find_numbered(pack: Path, subdir: tuple, prefix: str, n: int) -> list[Path]:
    """
    Return up to *n* files matching `prefix_0.png … prefix_N.png`
    (also tries `prefix_00.png` and `prefix0.png` naming variants).
    """
    folder = pack.joinpath(*subdir)
    found: list[Path] = []
    for i in range(n * 3):   # search generously
        for tmpl in (f"{prefix}_{i}.png", f"{prefix}{i}.png",
                     f"{prefix}_{i:02d}.png"):
            p = folder / tmpl
            if p.exists():
                found.append(p)
                break
        if len(found) == n:
            break
    return found[:n]


def install_tiles():
    print("\n[Tiles]")
    out = OUT / "tiles"
    out.mkdir(parents=True, exist_ok=True)

    for theme, (floor_sub, floor_pfx, wall_sub, wall_pfx, n) in _TILE_MAP.items():
        floor_files = _find_numbered(FULL, floor_sub, floor_pfx, n)
        wall_files  = _find_numbered(FULL, wall_sub,  wall_pfx,  n)

        # Pad with repeats if we got fewer than n
        while len(floor_files) < n and floor_files:
            floor_files.append(floor_files[-1])
        while len(wall_files) < n and wall_files:
            wall_files.append(wall_files[-1])

        for i, (fp, wp) in enumerate(zip(floor_files, wall_files)):
            copy_scaled(fp, out / f"floor_{theme}_{i}.png", (TILE_SIZE, TILE_SIZE))
            copy_scaled(wp, out / f"wall_{theme}_{i}.png",  (TILE_SIZE, TILE_SIZE))


# ── Item sprites ───────────────────────────────────────────────────────────────

def install_items():
    print("\n[Items]")
    out = OUT / "items"
    out.mkdir(parents=True, exist_ok=True)

    _ITEM_MAP = {
        "gold_pile":       ("item", "gold",   "gold_pile_3.png"),
        "health_potion":   ("item", "potion", "red_new.png"),
        "weapon_sword":    ("item", "weapon", "short_sword_2.png"),
        "weapon_axe":      ("item", "weapon", "battle_axe_1.png"),
        "weapon_bow":      ("item", "weapon", "ranged", "shortbow.png"),
        "armour_chest":    ("item", "armor",  "torso", "ring_mail.png"),
        "armour_helm":     ("item", "armor",  "headgear", "helmet_1.png"),
        "armour_shield":   ("item", "armor",  "shields", "kite_shield.png"),
        "ring":            ("item", "ring",   "ring_silver.png"),
        "amulet":          ("item", "amulet", "amulet_1.png"),
    }

    for name, parts in _ITEM_MAP.items():
        try:
            s = src(*parts)
            copy(s, out / f"{name}.png")
        except FileNotFoundError:
            # Try alternate names gracefully
            try:
                folder = FULL.joinpath(*parts[:-1])
                candidates = sorted(folder.glob("*.png"))
                if candidates:
                    copy(candidates[0], out / f"{name}.png")
                else:
                    print(f"  SKIP {name}: no candidates in {folder}")
            except Exception as e:
                print(f"  SKIP {name}: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not FULL.exists():
        print(f"ERROR: DCSS full pack not found at:\n  {FULL}")
        print("Place the 'Dungeon Crawl Stone Soup Full' folder inside assets/")
        raise SystemExit(1)

    print(f"Source: {FULL.name}")
    install_player()
    install_enemies()
    install_tiles()
    install_items()
    print(f"\nDone — DCSS assets installed into {OUT.relative_to(ROOT)}/")
