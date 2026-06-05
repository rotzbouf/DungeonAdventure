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

    # Each key becomes assets/items/{key}.png
    # The value is a path tuple relative to FULL.
    _ITEM_MAP = {
        # ── Ground drops ─────────────────────────────────────────────────────
        "gold_pile":           ("item", "gold",   "gold_pile_3.png"),
        "health_potion":       ("item", "potion", "ruby.png"),
        # ── Swords ───────────────────────────────────────────────────────────
        "Dagger":              ("item", "weapon", "dagger.png"),
        "Short Sword":         ("item", "weapon", "short_sword_2.png"),
        "Long Sword":          ("item", "weapon", "long_sword_1.png"),
        "Scimitar":            ("item", "weapon", "falchion_1.png"),
        "Rapier":              ("item", "weapon", "rapier_1.png"),
        "Broad Sword":         ("item", "weapon", "elven_broadsword.png"),
        "Claymore":            ("item", "weapon", "claymore.png"),
        "Great Sword":         ("item", "weapon", "double_sword.png"),
        "Demon Blade":         ("item", "weapon", "demon_blade.png"),
        # ── Axes ─────────────────────────────────────────────────────────────
        "Hand Axe":            ("item", "weapon", "hand_axe_1.png"),
        "War Axe":             ("item", "weapon", "war_axe_1.png"),
        "Battle Axe":          ("item", "weapon", "battle_axe_1.png"),
        "Great Axe":           ("item", "weapon", "broad_axe_1.png"),
        "Executioner's Axe":   ("item", "weapon", "executioner_axe_1.png"),
        # ── Maces ────────────────────────────────────────────────────────────
        "Club":                ("item", "weapon", "club.png"),
        "Mace":                ("item", "weapon", "mace_1.png"),
        "Flail":               ("item", "weapon", "flail_1.png"),
        "Morningstar":         ("item", "weapon", "morningstar_1.png"),
        "War Hammer":          ("item", "weapon", "hammer_2_new.png"),
        "Dire Flail":          ("item", "weapon", "dire_flail_1.png"),
        # ── Polearms ─────────────────────────────────────────────────────────
        "Spear":               ("item", "weapon", "spear_1.png"),
        "Halberd":             ("item", "weapon", "halberd_1.png"),
        "Glaive":              ("item", "weapon", "glaive_1.png"),
        "Bardiche":            ("item", "weapon", "bardiche_1.png"),
        # ── Staves ───────────────────────────────────────────────────────────
        "Quarterstaff":        ("item", "weapon", "quarterstaff.png"),
        "Battle Staff":        ("item", "weapon", "quarterstaff_2.png"),
        # ── Ranged ───────────────────────────────────────────────────────────
        "Short Bow":           ("item", "weapon", "ranged", "shortbow.png"),
        "Long Bow":            ("item", "weapon", "ranged", "longbow.png"),
        "Hunter's Bow":        ("item", "weapon", "ranged", "bow_1.png"),
        "Hand Crossbow":       ("item", "weapon", "ranged", "hand_crossbow.png"),
        "War Bow":             ("item", "weapon", "ranged", "longbow_1.png"),
        "Crossbow":            ("item", "weapon", "ranged", "crossbow_1.png"),
        "Arbalest":            ("item", "weapon", "ranged", "arbalest_1.png"),
        # ── Shields ──────────────────────────────────────────────────────────
        "Buckler":             ("item", "armor", "shields", "buckler_1.png"),
        "Heater Shield":       ("item", "armor", "shields", "shield_1.png"),
        "Kite Shield":         ("item", "armor", "shields", "shield_2_kite.png"),
        "Round Shield":        ("item", "armor", "shields", "shield_3_round.png"),
        "Tower Shield":        ("item", "armor", "shields", "large_shield_1.png"),
        "Dwarven Shield":      ("item", "armor", "shields", "dwarven_buckler_1.png"),
        # ── Helms ────────────────────────────────────────────────────────────
        "Cap":                 ("item", "armor", "headgear", "cap_1.png"),
        "Leather Helm":        ("item", "armor", "headgear", "elven_leather_helm.png"),
        "Helm":                ("item", "armor", "headgear", "helmet_1.png"),
        "Visored Helm":        ("item", "armor", "headgear", "helmet_1_visored.png"),
        "Great Helm":          ("item", "armor", "headgear", "helmet_2.png"),
        "Dragon Helm":         ("item", "armor", "headgear", "crested_helmet.png"),
        # ── Chest ────────────────────────────────────────────────────────────
        "Leather Armor":       ("item", "armor", "torso", "leather_armor_1.png"),
        "Ring Mail":           ("item", "armor", "torso", "dwarven_ringmail.png"),
        "Chain Mail":          ("item", "armor", "torso", "chain_mail_1.png"),
        "Banded Mail":         ("item", "armor", "torso", "banded_mail_1.png"),
        "Plate Armor":         ("item", "armor", "torso", "plate_mail_1.png"),
        "Crystal Plate":       ("item", "armor", "torso", "crystal_plate_mail.png"),
        # ── Gloves ───────────────────────────────────────────────────────────
        "Leather Gloves":      ("item", "armor", "hands", "glove_1.png"),
        "Chain Gloves":        ("item", "armor", "hands", "glove_2.png"),
        "Gauntlets":           ("item", "armor", "hands", "gauntlet_1.png"),
        "War Gauntlets":       ("item", "armor", "hands", "glove_3.png"),
        # ── Boots ────────────────────────────────────────────────────────────
        "Leather Boots":       ("item", "armor", "feet", "boots_1_brown_new.png"),
        "Chain Boots":         ("item", "armor", "feet", "boots_3_stripe_new.png"),
        "Greaves":             ("item", "armor", "feet", "boots_iron_2.png"),
        "Iron Boots":          ("item", "armor", "feet", "low_boots.png"),
        # ── Belt (use cloaks as belt sprites — similar silhouette) ────────────
        "Sash":                ("item", "armor", "back", "cloak_1_leather.png"),
        "Belt":                ("item", "armor", "back", "cloak_2.png"),
        "Studded Belt":        ("item", "armor", "back", "cloak_3.png"),
        "War Belt":            ("item", "armor", "back", "cloak_4.png"),
        # ── Rings ────────────────────────────────────────────────────────────
        "Ring":                ("item", "ring", "brass.png"),
        "Iron Ring":           ("item", "ring", "iron.png"),
        "Silver Ring":         ("item", "ring", "glass.png"),
        "Gold Ring":           ("item", "ring", "gold.png"),
        "Ancient Ring":        ("item", "ring", "opal.png"),
        # ── Amulets ──────────────────────────────────────────────────────────
        "Amulet":              ("item", "amulet", "bone_gray.png"),
        "Stone Amulet":        ("item", "amulet", "stone_1_cyan.png"),
        "Runed Amulet":        ("item", "amulet", "celtic_red.png"),
        "Elven Amulet":        ("item", "amulet", "crystal_green.png"),
        "Ancient Amulet":      ("item", "amulet", "penta_orange.png"),
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

# ── Player equipment overlays ─────────────────────────────────────────────────
# Maps (layer_dir, dest_name) → source path in FULL/player/{layer}/
# dest_name is used as the key in EQUIPMENT_OVERLAYS in assets.py.

_OVERLAY_MAP: dict[str, tuple[str, str]] = {
    # ── Chest (body layer) ────────────────────────────────────────────────────
    "body_none":         ("body", "leather_armor.png"),   # unarmoured default
    "body_Leather Armor":("body", "leather_armor.png"),
    "body_Ring Mail":    ("body", "ringmail.png"),
    "body_Chain Mail":   ("body", "chainmail.png"),
    "body_Banded Mail":  ("body", "banded.png"),
    "body_Plate Armor":  ("body", "plate.png"),
    "body_Crystal Plate":("body", "crystal_plate.png"),
    # ── Helm (head layer) ─────────────────────────────────────────────────────
    "head_Cap":          ("head", "cap_black_1.png"),
    "head_Leather Helm": ("head", "cap_blue.png"),
    "head_Helm":         ("head", "iron_1.png"),
    "head_Visored Helm": ("head", "iron_2.png"),
    "head_Great Helm":   ("head", "helm_gimli.png"),
    "head_Dragon Helm":  ("head", "art_dragonhelm.png"),
    # ── Weapon (hand_right layer) ─────────────────────────────────────────────
    "wpn_Dagger":              ("hand_right", "dagger.png"),
    "wpn_Short Sword":         ("hand_right", "short_sword.png"),
    "wpn_Long Sword":          ("hand_right", "long_sword.png"),
    "wpn_Scimitar":            ("hand_right", "scimitar.png"),
    "wpn_Rapier":              ("hand_right", "rapier.png"),
    "wpn_Broad Sword":         ("hand_right", "broadsword.png"),
    "wpn_Claymore":            ("hand_right", "great_sword.png"),
    "wpn_Great Sword":         ("hand_right", "double_sword.png"),
    "wpn_Demon Blade":         ("hand_right", "black_sword.png"),
    "wpn_Hand Axe":            ("hand_right", "axe_short.png"),
    "wpn_War Axe":             ("hand_right", "axe.png"),
    "wpn_Battle Axe":          ("hand_right", "battleaxe.png"),
    "wpn_Great Axe":           ("hand_right", "broad_axe.png"),
    "wpn_Executioner's Axe":   ("hand_right", "axe_executioner.png"),
    "wpn_Club":                ("hand_right", "mace.png"),
    "wpn_Mace":                ("hand_right", "mace_2.png"),
    "wpn_Flail":               ("hand_right", "flail_ball.png"),
    "wpn_Morningstar":         ("hand_right", "morningstar.png"),
    "wpn_War Hammer":          ("hand_right", "hammer_2.png"),
    "wpn_Dire Flail":          ("hand_right", "flail_great.png"),
    "wpn_Spear":               ("hand_right", "d_glaive.png"),
    "wpn_Halberd":             ("hand_right", "halberd.png"),
    "wpn_Glaive":              ("hand_right", "glaive.png"),
    "wpn_Bardiche":            ("hand_right", "glaive_three.png"),
    "wpn_Quarterstaff":        ("hand_right", "quarterstaff_1.png"),
    "wpn_Battle Staff":        ("hand_right", "great_staff.png"),
    "wpn_Short Bow":           ("hand_right", "bow.png"),
    "wpn_Long Bow":            ("hand_right", "bow_2.png"),
    "wpn_Hunter's Bow":        ("hand_right", "bow_3.png"),
    "wpn_War Bow":             ("hand_right", "bow_blue.png"),
    "wpn_Hand Crossbow":       ("hand_right", "hand_crossbow.png"),
    "wpn_Crossbow":            ("hand_right", "crossbow.png"),
    "wpn_Arbalest":            ("hand_right", "crossbow_4.png"),
    # ── Shield (hand_left layer) ──────────────────────────────────────────────
    "shld_Buckler":            ("hand_left", "buckler_round_2.png"),
    "shld_Heater Shield":      ("hand_left", "buckler_rb.png"),
    "shld_Kite Shield":        ("hand_left", "lshield_green.png"),
    "shld_Round Shield":       ("hand_left", "buckler_spiral.png"),
    "shld_Tower Shield":       ("hand_left", "lshield_quartered.png"),
    "shld_Dwarven Shield":     ("hand_left", "lshield_louise.png"),
    # ── Boots ─────────────────────────────────────────────────────────────────
    "boot_Leather Boots":      ("boots", "middle_brown.png"),
    "boot_Chain Boots":        ("boots", "middle_gray.png"),
    "boot_Greaves":            ("boots", "mesh_blue.png"),
    "boot_Iron Boots":         ("boots", "mesh_black.png"),
    # ── Gloves ────────────────────────────────────────────────────────────────
    "glv_Leather Gloves":      ("gloves", "glove_brown.png"),
    "glv_Chain Gloves":        ("gloves", "glove_gray.png"),
    "glv_Gauntlets":           ("gloves", "gauntlet_blue.png"),
    "glv_War Gauntlets":       ("gloves", "glove_grayfist.png"),
}


def install_player_overlays():
    print("\n[Player overlays]")
    out = OUT / "player_overlays"
    out.mkdir(exist_ok=True)
    for key, (layer, fname) in _OVERLAY_MAP.items():
        try:
            s = src("player", layer, fname)
            dest = out / f"{key}.png"
            copy(s, dest)
        except FileNotFoundError as e:
            print(f"  SKIP {key}: {e}")


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
    install_player_overlays()
    print(f"\nDone — DCSS assets installed into {OUT.relative_to(ROOT)}/")
