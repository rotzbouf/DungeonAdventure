"""
Loot system.

Quality tiers  : Normal (white) → Magic (blue) → Rare (yellow) → Unique (gold)
Equipment slots : weapon · shield · helm · chest · gloves · boots · belt · ring×2 · amulet
Modifier types  : atk · atk_pct · def · max_hp · hp_regen · life_steal · crit ·
                  thorns · speed · gold_find · max_mana · atk_spd
"""
from __future__ import annotations

import math
import random
import pygame
from src.settings import (TILE_SIZE, ITEM_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT,
                           HUD_HEIGHT, WHITE, BLACK)

# ── Quality ───────────────────────────────────────────────────────────────────

QUALITY_NORMAL = 0
QUALITY_MAGIC  = 1
QUALITY_RARE   = 2
QUALITY_UNIQUE = 3

Q_COLOR = {
    QUALITY_NORMAL: (188, 188, 188),   # white / light grey
    QUALITY_MAGIC:  ( 80,  80, 255),   # blue
    QUALITY_RARE:   (252, 188,   0),   # yellow
    QUALITY_UNIQUE: (200, 115,   0),   # dark gold / orange
}
Q_GLOW = {                             # inner glow for ground sprite
    QUALITY_NORMAL: (100, 100, 100),
    QUALITY_MAGIC:  ( 30,  30, 180),
    QUALITY_RARE:   (160, 120,   0),
    QUALITY_UNIQUE: (180,  60,   0),
}
Q_LABEL = {
    QUALITY_NORMAL: "",
    QUALITY_MAGIC:  "Magic ",
    QUALITY_RARE:   "Rare ",
    QUALITY_UNIQUE: "",          # unique items use their proper name directly
}

# ── Equipment slots ───────────────────────────────────────────────────────────

SLOT_WEAPON = "weapon"
SLOT_SHIELD = "shield"
SLOT_HELM   = "helm"
SLOT_CHEST  = "chest"
SLOT_GLOVES = "gloves"
SLOT_BOOTS  = "boots"
SLOT_BELT   = "belt"
SLOT_RING   = "ring"
SLOT_AMULET = "amulet"

SLOT_ORDER  = [SLOT_WEAPON, SLOT_SHIELD, SLOT_HELM, SLOT_CHEST,
               SLOT_GLOVES, SLOT_BOOTS,  SLOT_BELT, SLOT_RING,
               "ring2",     SLOT_AMULET]
SLOT_LABELS = {
    SLOT_WEAPON: "WEAPON",  SLOT_SHIELD: "SHIELD",
    SLOT_HELM:   "HELM",    SLOT_CHEST:  "CHEST",
    SLOT_GLOVES: "GLOVES",  SLOT_BOOTS:  "BOOTS",
    SLOT_BELT:   "BELT",    SLOT_RING:   "RING 1",
    "ring2":     "RING 2",  SLOT_AMULET: "AMULET",
}

# Which slots care about the primary stat (atk or def)
_WEAPON_SLOTS = {SLOT_WEAPON}
_ARMOR_SLOTS  = {SLOT_SHIELD, SLOT_HELM, SLOT_CHEST,
                 SLOT_GLOVES, SLOT_BOOTS, SLOT_BELT}

# ── Modifier types ────────────────────────────────────────────────────────────

MOD_ATK        = "atk"
MOD_ATK_PCT    = "atk_pct"     # % of base attack
MOD_DEF        = "def"
MOD_MAX_HP     = "max_hp"
MOD_HP_REGEN   = "hp_regen"    # HP / sec
MOD_LIFE_STEAL = "life_steal"  # % of damage dealt converted to HP
MOD_CRIT       = "crit"        # % crit chance (×2 damage)
MOD_THORNS     = "thorns"      # flat damage returned to attacker
MOD_SPEED      = "speed"       # % movement speed bonus
MOD_GOLD_FIND  = "gold_find"   # % extra gold from drops
MOD_MAX_MANA   = "max_mana"
MOD_ATK_SPD    = "atk_spd"     # % reduction in attack cooldown


class Modifier:
    """Single stat modifier on an equipment item."""

    _FMT = {
        MOD_ATK:        lambda v: f"+{int(v)} to Attack",
        MOD_ATK_PCT:    lambda v: f"+{int(v)}% Enhanced Damage",
        MOD_DEF:        lambda v: f"+{int(v)} to Defense",
        MOD_MAX_HP:     lambda v: f"+{int(v)} to Life",
        MOD_HP_REGEN:   lambda v: f"+{v:.1f} Life Regen / sec",
        MOD_LIFE_STEAL: lambda v: f"{int(v)}% Life Stolen per Hit",
        MOD_CRIT:       lambda v: f"+{int(v)}% Critical Strike",
        MOD_THORNS:     lambda v: f"Attacker Takes {int(v)} Damage",
        MOD_SPEED:      lambda v: f"+{int(v)}% Faster Run/Walk",
        MOD_GOLD_FIND:  lambda v: f"+{int(v)}% Better Chance of Gold",
        MOD_MAX_MANA:   lambda v: f"+{int(v)} to Mana",
        MOD_ATK_SPD:    lambda v: f"+{int(v)}% Increased Attack Speed",
    }

    def __init__(self, kind: str, value: float):
        self.kind  = kind
        self.value = value

    def describe(self) -> str:
        fmt = self._FMT.get(self.kind)
        return fmt(self.value) if fmt else f"+{self.value} {self.kind}"


# ── Affix pools ───────────────────────────────────────────────────────────────
# (name, mod_kind, min_val, max_val, min_item_level)

_PREFIXES: list[tuple] = [
    # ilvl 1
    ("Sturdy",         MOD_DEF,         2,   5,  1),
    ("Strong",         MOD_ATK,         2,   5,  1),
    ("Healthy",        MOD_MAX_HP,     10,  20,  1),
    ("Sharp",          MOD_ATK,         3,   7,  1),
    ("Light",          MOD_SPEED,       5,  10,  1),
    # ilvl 2
    ("Savage",         MOD_ATK,         7,  14,  2),
    ("Heavy",          MOD_DEF,         6,  11,  2),
    ("Stalwart",       MOD_MAX_HP,     20,  40,  2),
    ("Vampiric",       MOD_LIFE_STEAL,  2,   5,  2),
    ("Swift",          MOD_SPEED,      10,  18,  2),
    ("Enhanced",       MOD_ATK_PCT,    10,  20,  2),
    ("Rugged",         MOD_DEF,         8,  14,  2),
    # ilvl 3
    ("Brutal",         MOD_ATK,        14,  22,  3),
    ("Fortified",      MOD_DEF,        11,  18,  3),
    ("Vital",          MOD_MAX_HP,     40,  70,  3),
    ("Draining",       MOD_LIFE_STEAL,  5,  10,  3),
    ("Fleeting",       MOD_SPEED,      18,  25,  3),
    ("Deadly",         MOD_ATK_PCT,    20,  35,  3),
    ("Glinting",       MOD_CRIT,        3,   7,  3),
    ("Regenerating",   MOD_HP_REGEN,  0.5, 1.5,  3),
    # ilvl 4
    ("Cruel",          MOD_ATK,        22,  35,  4),
    ("Impenetrable",   MOD_DEF,        18,  28,  4),
    ("Massive",        MOD_MAX_HP,     70, 100,  4),
    ("Sanguine",       MOD_LIFE_STEAL,  8,  15,  4),
    ("Ferocious",      MOD_ATK_PCT,    35,  55,  4),
    ("Razorsharp",     MOD_CRIT,        7,  14,  4),
    ("Mending",        MOD_HP_REGEN,  1.5, 3.0,  4),
    ("Thorned",        MOD_THORNS,     10,  20,  4),
    # ilvl 5
    ("Godly",          MOD_ATK,        35,  55,  5),
    ("Indestructible", MOD_DEF,        28,  45,  5),
    ("Mammoth",        MOD_MAX_HP,    100, 150,  5),
    ("Merciless",      MOD_ATK_PCT,    55,  80,  5),
    ("Ruinous",        MOD_THORNS,     20,  35,  5),
]

_SUFFIXES: list[tuple] = [
    # ilvl 1
    ("of Power",       MOD_ATK,         2,   5,  1),
    ("of Defense",     MOD_DEF,         2,   4,  1),
    ("of Health",      MOD_MAX_HP,     10,  20,  1),
    ("of the Nimble",  MOD_SPEED,       5,   8,  1),
    ("of Mana",        MOD_MAX_MANA,    5,  15,  1),
    # ilvl 2
    ("of Slaying",     MOD_ATK,         5,  12,  2),
    ("of Warding",     MOD_DEF,         4,   9,  2),
    ("of Vitality",    MOD_MAX_HP,     20,  40,  2),
    ("of Speed",       MOD_SPEED,       8,  15,  2),
    ("of Wealth",      MOD_GOLD_FIND,  20,  40,  2),
    ("of the Fox",     MOD_LIFE_STEAL,  2,   5,  2),
    # ilvl 3
    ("of Destruction", MOD_ATK,        12,  20,  3),
    ("of the Sentinel",MOD_DEF,         9,  15,  3),
    ("of the Colossus",MOD_MAX_HP,     40,  70,  3),
    ("of Alacrity",    MOD_ATK_SPD,    10,  20,  3),
    ("of the Magpie",  MOD_GOLD_FIND,  40,  70,  3),
    ("of Leeching",    MOD_LIFE_STEAL,  5,  10,  3),
    ("of Fortune",     MOD_CRIT,        3,   7,  3),
    ("of Remedy",      MOD_HP_REGEN,  0.5, 1.5,  3),
    # ilvl 4
    ("of Carnage",     MOD_ATK,        20,  33,  4),
    ("of the Titan",   MOD_DEF,        15,  25,  4),
    ("of Giants",      MOD_MAX_HP,     70, 100,  4),
    ("of Precision",   MOD_ATK_SPD,    20,  35,  4),
    ("of Greed",       MOD_GOLD_FIND,  70, 110,  4),
    ("of Vampirism",   MOD_LIFE_STEAL,  8,  15,  4),
    ("of Doom",        MOD_CRIT,        7,  14,  4),
    ("of Thorns",      MOD_THORNS,      8,  18,  4),
    # ilvl 5
    ("of Inferno",     MOD_ATK,        33,  50,  5),
    ("of Mastery",     MOD_ATK_PCT,    20,  40,  5),
    ("of Obliteration",MOD_CRIT,       14,  22,  5),
]

# ── Rare name generator ───────────────────────────────────────────────────────

_RARE_FIRST  = ["Blood", "Storm", "Shadow", "Iron", "Doom", "Death", "Void",
                "Grim",  "Dark",  "War",    "Bone", "Night","Soul",  "Chaos",
                "Vile",  "Wrath", "Steel",  "Dusk", "Fury", "Dread"]
_RARE_SECOND = ["Bane",  "Edge",  "Crest",  "Wail", "Brand","Gore",  "Fang",
                "Toll",  "Grasp", "Tread",  "Coil", "Hide", "Mark",  "Grip",
                "Shank", "Loop",  "Clutch", "Collar","Knot","Claw"]

# ── Base item types ───────────────────────────────────────────────────────────
# (slot, primary_stat_min, primary_stat_max, level_tier)

_BASES: dict[str, tuple] = {
    # Weapons — primary = ATK
    "Dagger":          (SLOT_WEAPON,  1,  3, 1),
    "Short Sword":     (SLOT_WEAPON,  3,  6, 1),
    "Broad Sword":     (SLOT_WEAPON,  6, 10, 2),
    "Battle Axe":      (SLOT_WEAPON, 10, 16, 3),
    "War Hammer":      (SLOT_WEAPON, 15, 22, 4),
    "Great Sword":     (SLOT_WEAPON, 20, 30, 5),
    # Shields — primary = DEF
    "Buckler":         (SLOT_SHIELD,  1,  2, 1),
    "Kite Shield":     (SLOT_SHIELD,  3,  5, 3),
    "Tower Shield":    (SLOT_SHIELD,  6, 10, 5),
    # Helms
    "Cap":             (SLOT_HELM,    1,  2, 1),
    "Helm":            (SLOT_HELM,    3,  5, 3),
    "Great Helm":      (SLOT_HELM,    6, 10, 5),
    # Chest
    "Leather Armor":   (SLOT_CHEST,   2,  4, 1),
    "Ring Mail":       (SLOT_CHEST,   5,  8, 3),
    "Plate Armor":     (SLOT_CHEST,   9, 14, 5),
    # Gloves
    "Leather Gloves":  (SLOT_GLOVES,  1,  2, 1),
    "Chain Gloves":    (SLOT_GLOVES,  2,  4, 3),
    "Gauntlets":       (SLOT_GLOVES,  4,  7, 5),
    # Boots
    "Leather Boots":   (SLOT_BOOTS,   1,  2, 1),
    "Chain Boots":     (SLOT_BOOTS,   2,  4, 3),
    "Greaves":         (SLOT_BOOTS,   4,  7, 5),
    # Belt
    "Sash":            (SLOT_BELT,    0,  1, 1),
    "Belt":            (SLOT_BELT,    1,  3, 3),
    "War Belt":        (SLOT_BELT,    3,  5, 5),
    # Jewellery — no primary stat
    "Ring":            (SLOT_RING,    0,  0, 1),
    "Amulet":          (SLOT_AMULET,  0,  0, 1),
}

# Weapon/armour type available at each level (pick from this list)
_LEVEL_WEAPONS = {1: ["Dagger", "Short Sword"],
                  2: ["Short Sword", "Broad Sword"],
                  3: ["Broad Sword", "Battle Axe"],
                  4: ["Battle Axe", "War Hammer"],
                  5: ["War Hammer", "Great Sword"]}

_LEVEL_ARMOR: dict[str, dict[int, str]] = {
    SLOT_SHIELD: {1: "Buckler",        2: "Buckler",        3: "Kite Shield",
                  4: "Kite Shield",    5: "Tower Shield"},
    SLOT_HELM:   {1: "Cap",            2: "Cap",            3: "Helm",
                  4: "Helm",           5: "Great Helm"},
    SLOT_CHEST:  {1: "Leather Armor",  2: "Leather Armor",  3: "Ring Mail",
                  4: "Ring Mail",      5: "Plate Armor"},
    SLOT_GLOVES: {1: "Leather Gloves", 2: "Leather Gloves", 3: "Chain Gloves",
                  4: "Chain Gloves",   5: "Gauntlets"},
    SLOT_BOOTS:  {1: "Leather Boots",  2: "Leather Boots",  3: "Chain Boots",
                  4: "Chain Boots",    5: "Greaves"},
    SLOT_BELT:   {1: "Sash",           2: "Sash",           3: "Belt",
                  4: "Belt",           5: "War Belt"},
}

# ── Unique item database ──────────────────────────────────────────────────────

_UNIQUES: list[dict] = [
    # ── Weapons ──────────────────────────────────────────────────────────────
    {"slot": SLOT_WEAPON, "base": "Dagger",      "min_lvl": 1,
     "name": "Shadowfang",
     "mods": [(MOD_ATK, 8), (MOD_CRIT, 15), (MOD_LIFE_STEAL, 6), (MOD_SPEED, 10)],
     "flavor": "Swift as shadow, sharp as regret."},

    {"slot": SLOT_WEAPON, "base": "Short Sword", "min_lvl": 2,
     "name": "Cruel Edge",
     "mods": [(MOD_ATK, 15), (MOD_ATK_PCT, 25), (MOD_LIFE_STEAL, 8)],
     "flavor": "Pain is its purpose."},

    {"slot": SLOT_WEAPON, "base": "Broad Sword", "min_lvl": 3,
     "name": "Windforce",
     "mods": [(MOD_ATK_PCT, 40), (MOD_ATK_SPD, 30), (MOD_CRIT, 10), (MOD_SPEED, 15)],
     "flavor": "Strikes like a gale, vanishes like smoke."},

    {"slot": SLOT_WEAPON, "base": "Battle Axe",  "min_lvl": 4,
     "name": "The Reaper's Toll",
     "mods": [(MOD_ATK, 30), (MOD_ATK_PCT, 20), (MOD_LIFE_STEAL, 12)],
     "flavor": "Every swing is a payment due."},

    {"slot": SLOT_WEAPON, "base": "War Hammer",  "min_lvl": 4,
     "name": "Earth Shaker",
     "mods": [(MOD_ATK, 45), (MOD_THORNS, 20), (MOD_MAX_HP, 50)],
     "flavor": "The ground trembles at its passing."},

    {"slot": SLOT_WEAPON, "base": "Great Sword",  "min_lvl": 5,
     "name": "Doom Bringer",
     "mods": [(MOD_ATK, 60), (MOD_ATK_PCT, 50), (MOD_CRIT, 20)],
     "flavor": "Its edge separates the living from the dead."},

    # ── Shields ───────────────────────────────────────────────────────────────
    {"slot": SLOT_SHIELD, "base": "Buckler",     "min_lvl": 1,
     "name": "Stormshield",
     "mods": [(MOD_DEF, 15), (MOD_THORNS, 12), (MOD_MAX_HP, 30)],
     "flavor": "The storm cannot reach you here."},

    {"slot": SLOT_SHIELD, "base": "Tower Shield", "min_lvl": 4,
     "name": "Ironwall",
     "mods": [(MOD_DEF, 30), (MOD_THORNS, 25), (MOD_HP_REGEN, 2.0)],
     "flavor": "Nothing gets through."},

    # ── Helms ─────────────────────────────────────────────────────────────────
    {"slot": SLOT_HELM, "base": "Cap",            "min_lvl": 1,
     "name": "Dark Shako",
     "mods": [(MOD_MAX_HP, 60), (MOD_MAX_MANA, 30), (MOD_GOLD_FIND, 50)],
     "flavor": "Seek riches in the dark."},

    {"slot": SLOT_HELM, "base": "Great Helm",     "min_lvl": 4,
     "name": "Veil of Steel",
     "mods": [(MOD_DEF, 20), (MOD_MAX_HP, 80), (MOD_HP_REGEN, 1.5)],
     "flavor": "Iron resolve, iron will."},

    # ── Chest ─────────────────────────────────────────────────────────────────
    {"slot": SLOT_CHEST, "base": "Leather Armor", "min_lvl": 1,
     "name": "Twitchthroe",
     "mods": [(MOD_DEF, 8), (MOD_ATK_SPD, 20), (MOD_CRIT, 8)],
     "flavor": "Speed is its own armor."},

    {"slot": SLOT_CHEST, "base": "Ring Mail",     "min_lvl": 3,
     "name": "Skin of the Vipermagi",
     "mods": [(MOD_DEF, 15), (MOD_ATK_SPD, 30), (MOD_THORNS, 15)],
     "flavor": "The serpent's gift of venom and speed."},

    {"slot": SLOT_CHEST, "base": "Plate Armor",   "min_lvl": 5,
     "name": "Arkaine's Valor",
     "mods": [(MOD_DEF, 35), (MOD_MAX_HP, 100), (MOD_HP_REGEN, 3.0)],
     "flavor": "Forged in courage, worn with pride."},

    # ── Gloves ────────────────────────────────────────────────────────────────
    {"slot": SLOT_GLOVES, "base": "Leather Gloves","min_lvl": 1,
     "name": "Bloodfist",
     "mods": [(MOD_MAX_HP, 40), (MOD_ATK_SPD, 20), (MOD_LIFE_STEAL, 4)],
     "flavor": "The fist that bleeds your enemies."},

    {"slot": SLOT_GLOVES, "base": "Gauntlets",    "min_lvl": 4,
     "name": "Laying of Hands",
     "mods": [(MOD_DEF, 12), (MOD_LIFE_STEAL, 10), (MOD_ATK, 15)],
     "flavor": "Holy fury in an iron fist."},

    # ── Boots ─────────────────────────────────────────────────────────────────
    {"slot": SLOT_BOOTS, "base": "Leather Boots", "min_lvl": 1,
     "name": "Goblin Toe",
     "mods": [(MOD_CRIT, 12), (MOD_SPEED, 8)],
     "flavor": "Aim for the throat, kick with the toe."},

    {"slot": SLOT_BOOTS, "base": "Greaves",       "min_lvl": 4,
     "name": "War Traveler",
     "mods": [(MOD_SPEED, 25), (MOD_MAX_HP, 50), (MOD_GOLD_FIND, 80)],
     "flavor": "Miles of dungeons, pockets full of gold."},

    # ── Belt ──────────────────────────────────────────────────────────────────
    {"slot": SLOT_BELT, "base": "Sash",           "min_lvl": 1,
     "name": "Goldwrap",
     "mods": [(MOD_GOLD_FIND, 100), (MOD_MAX_HP, 20), (MOD_ATK_SPD, 10)],
     "flavor": "Greed is its own reward."},

    {"slot": SLOT_BELT, "base": "War Belt",       "min_lvl": 4,
     "name": "Verdungo's Coil",
     "mods": [(MOD_MAX_HP, 120), (MOD_HP_REGEN, 2.5), (MOD_DEF, 10)],
     "flavor": "Coiled iron, coiled strength."},

    # ── Rings ─────────────────────────────────────────────────────────────────
    {"slot": SLOT_RING, "base": "Ring",            "min_lvl": 1,
     "name": "Stone of Jordan",
     "mods": [(MOD_MAX_MANA, 50), (MOD_MAX_HP, 20), (MOD_ATK, 5)],
     "flavor": "The legends say it fell from the sky."},

    {"slot": SLOT_RING, "base": "Ring",            "min_lvl": 3,
     "name": "Nagelring",
     "mods": [(MOD_GOLD_FIND, 120), (MOD_ATK, 8), (MOD_CRIT, 5)],
     "flavor": "The ring that remembers all treasures."},

    {"slot": SLOT_RING, "base": "Ring",            "min_lvl": 4,
     "name": "Raven Frost",
     "mods": [(MOD_ATK, 15), (MOD_CRIT, 12), (MOD_DEF, 8)],
     "flavor": "Cold as the grave."},

    # ── Amulets ───────────────────────────────────────────────────────────────
    {"slot": SLOT_AMULET, "base": "Amulet",        "min_lvl": 1,
     "name": "Atma's Scarab",
     "mods": [(MOD_THORNS, 15), (MOD_GOLD_FIND, 60), (MOD_ATK, 10)],
     "flavor": "The scarab carries the weight of curses."},

    {"slot": SLOT_AMULET, "base": "Amulet",        "min_lvl": 4,
     "name": "Mara's Kaleidoscope",
     "mods": [(MOD_ATK, 15), (MOD_DEF, 15), (MOD_MAX_HP, 50), (MOD_LIFE_STEAL, 8)],
     "flavor": "The shifting colors of power."},

    {"slot": SLOT_AMULET, "base": "Amulet",        "min_lvl": 5,
     "name": "The Eye of Etlich",
     "mods": [(MOD_LIFE_STEAL, 12), (MOD_MAX_HP, 40), (MOD_CRIT, 10), (MOD_SPEED, 12)],
     "flavor": "Sees all, grants all."},
]


# ── World item base class ─────────────────────────────────────────────────────

class Item:
    """Base class: something lying on the dungeon floor."""

    def __init__(self, tx: int, ty: int):
        self.x   = float(tx * TILE_SIZE + TILE_SIZE // 2)
        self.y   = float(ty * TILE_SIZE + TILE_SIZE // 2)
        self.size      = ITEM_SIZE
        self.collected = False
        self.bob_timer = random.uniform(0, math.pi * 2)
        self.rect      = pygame.Rect(0, 0, self.size, self.size)
        self.rect.center = (int(self.x), int(self.y))

    def _reposition(self, px: float, py: float):
        self.x, self.y = px, py
        self.rect.center = (int(px), int(py))

    def update(self, dt: float):
        self.bob_timer += dt * 2.5

    def collect(self, player):
        self.collected = True

    def draw(self, surface: pygame.Surface, camera):
        bob_y    = math.sin(self.bob_timer) * 2
        draw_rect = camera.apply(self.rect).move(0, int(bob_y))
        play_h   = SCREEN_HEIGHT - HUD_HEIGHT
        if not (-20 < draw_rect.x < SCREEN_WIDTH + 20 and
                -20 < draw_rect.y < play_h + 20):
            return
        self._draw_shape(surface, draw_rect)

    def _draw_shape(self, surface: pygame.Surface, rect: pygame.Rect):
        pygame.draw.rect(surface, WHITE, rect)


# ── Consumables ───────────────────────────────────────────────────────────────

class GoldPile(Item):
    """Diamond-shaped coin, colour by value."""

    def __init__(self, tx: int, ty: int, amount: int = 0):
        super().__init__(tx, ty)
        self.amount = amount if amount else random.randint(5, 25)
        self.size   = ITEM_SIZE - 2

    def collect(self, player):
        player.gold += self.amount
        self.collected = True

    def _draw_shape(self, surface: pygame.Surface, rect: pygame.Rect):
        cx, cy = rect.centerx, rect.centery
        if self.amount >= 25:
            col, hi = (204, 0, 0),    (252,  80,  80)
        elif self.amount >= 10:
            col, hi = (0,   60, 216), (80,  140, 252)
        else:
            col, hi = (0,  168,   0), (0,   252,   0)
        h   = rect.height // 2 + 1
        pts = [(cx, cy - h), (cx + h - 2, cy), (cx, cy + h), (cx - h + 2, cy)]
        pygame.draw.polygon(surface, (0, 0, 0), pts)
        inner = [(cx, cy - h + 2), (cx + h - 4, cy),
                 (cx, cy + h - 2), (cx - h + 4, cy)]
        pygame.draw.polygon(surface, col, inner)
        pygame.draw.line(surface, hi, (cx - 1, cy - h + 2), (cx - h + 5, cy - 1))
        if int(self.bob_timer * 2) % 4 == 0:
            surface.set_at((cx + 2, cy - h + 4), (252, 252, 252))


class HealthPotion(Item):
    """Red potion bottle."""

    def __init__(self, tx: int, ty: int, heal: int = 0):
        super().__init__(tx, ty)
        self.heal_amount = heal if heal else random.randint(20, 40)

    def collect(self, player):
        player.add_item(self)
        self.collected = True

    def _draw_shape(self, surface: pygame.Surface, rect: pygame.Rect):
        cx, cy = rect.centerx, rect.centery
        _RED   = (204,   0,   0)
        _HI    = (252,  80,  80)
        _CORK  = (160, 100,  28)
        body   = pygame.Rect(cx - 5, cy - 2, 10, 10)
        pygame.draw.rect(surface, (0, 0, 0), body.inflate(2, 2))
        pygame.draw.rect(surface, _RED,  body)
        pygame.draw.rect(surface, _HI,   (body.left + 1, body.top + 1, 3, body.height - 2))
        pygame.draw.rect(surface, (0, 0, 0), (cx - 2, cy - 7, 4, 6))
        pygame.draw.rect(surface, _RED,  (cx - 1, cy - 6, 2, 4))
        pygame.draw.rect(surface, (0, 0, 0), (cx - 3, cy - 9, 6, 3))
        pygame.draw.rect(surface, _CORK, (cx - 2, cy - 8, 4, 2))
        bub_y = body.top + 2 + int(self.bob_timer * 4) % max(1, body.height - 4)
        if body.top + 1 < bub_y < body.bottom - 2:
            surface.set_at((cx + 2, bub_y), _HI)


# ── Equipment item ────────────────────────────────────────────────────────────

class EquipItem(Item):
    """Droppable equipment item with quality + affix modifiers."""

    def __init__(self, tx: int, ty: int, base_name: str,
                 quality: int, mods: list[Modifier],
                 unique_name: str = "", flavor: str = ""):
        super().__init__(tx, ty)
        slot_data     = _BASES[base_name]
        self.slot     = slot_data[0]
        self.base_stat_range = (slot_data[1], slot_data[2])
        self.base_stat = random.randint(slot_data[1], slot_data[2]) if slot_data[2] > 0 else 0

        self.base_name   = base_name
        self.quality     = quality
        self.mods: list[Modifier] = mods
        self.unique_name = unique_name
        self.flavor      = flavor

        # Rare items get a procedural two-part name
        if quality == QUALITY_RARE and not unique_name:
            self.rare_name = (random.choice(_RARE_FIRST) + " " +
                              random.choice(_RARE_SECOND))
        else:
            self.rare_name = ""

    # ── Display helpers ───────────────────────────────────────────────────────

    @property
    def display_name(self) -> str:
        if self.unique_name:
            return self.unique_name
        if self.rare_name:
            return self.rare_name
        # Magic: assemble prefix + base_name + suffix
        prefix = next((m.name for m in self.mods if getattr(m, "is_prefix", False)), "")
        suffix = next((m.name for m in self.mods if getattr(m, "is_suffix", False)), "")
        if prefix or suffix:
            parts = [p for p in [prefix, self.base_name, suffix] if p]
            return " ".join(parts)
        return self.base_name

    @property
    def quality_color(self) -> tuple:
        return Q_COLOR[self.quality]

    def get_mod_total(self, kind: str) -> float:
        return sum(m.value for m in self.mods if m.kind == kind)

    @property
    def primary_stat(self) -> int:
        """ATK for weapons, DEF for armor (base value, not including affixes)."""
        return self.base_stat

    def stat_lines(self) -> list[tuple[str, tuple]]:
        """Return list of (description_text, color) lines for tooltip."""
        lines: list[tuple[str, tuple]] = []
        # Primary stat
        if self.slot in _WEAPON_SLOTS and self.base_stat:
            lines.append((f"{self.base_stat} Attack", (188, 188, 188)))
        elif self.slot in _ARMOR_SLOTS and self.base_stat:
            lines.append((f"{self.base_stat} Defense", (188, 188, 188)))
        # Affix modifiers
        for m in self.mods:
            lines.append((m.describe(), (100, 220, 100)))
        # Flavor text
        if self.flavor:
            lines.append((f"\"{self.flavor}\"", (140, 120, 80)))
        return lines

    # ── Inventory interaction ─────────────────────────────────────────────────

    def collect(self, player):
        player.add_item(self)
        self.collected = True

    # ── Ground drawing ────────────────────────────────────────────────────────

    def _draw_shape(self, surface: pygame.Surface, rect: pygame.Rect):
        cx, cy = rect.centerx, rect.centery
        col    = Q_COLOR[self.quality]
        glow   = Q_GLOW[self.quality]

        # Quality-based glow halo for non-normal items
        if self.quality > QUALITY_NORMAL:
            pulse = 0.6 + 0.4 * abs(math.sin(self.bob_timer * 1.8))
            gr    = rect.width + 8
            gs    = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)

            if self.quality == QUALITY_UNIQUE:
                # Animated shimmer: gold → orange → gold colour cycle
                t     = self.bob_timer * 0.9
                sr    = int(215 + 40 * math.sin(t))
                sg    = int(140 + 55 * math.sin(t + 1.2))
                sb    = int(20  + 20 * abs(math.sin(t + 0.6)))
                glow  = (min(255, sr), min(255, sg), min(255, sb))
                alpha = int(110 * pulse)
                # Second outer ring for extra punch
                gr2   = gr + 8
                gs2   = pygame.Surface((gr2 * 2, gr2 * 2), pygame.SRCALPHA)
                pygame.draw.circle(gs2, (*glow, int(40 * pulse)), (gr2, gr2), gr2)
                surface.blit(gs2, (cx - gr2, cy - gr2))
            else:
                alpha = int(50 * pulse)

            pygame.draw.circle(gs, (*glow, alpha), (gr, gr), gr)
            surface.blit(gs, (cx - gr, cy - gr))

        # Draw icon based on slot type
        if self.slot == SLOT_WEAPON:
            self._draw_weapon_icon(surface, rect, col)
        elif self.slot in (SLOT_SHIELD, SLOT_HELM, SLOT_CHEST,
                           SLOT_GLOVES, SLOT_BOOTS, SLOT_BELT):
            self._draw_armor_icon(surface, rect, col)
        else:
            # Ring / Amulet: small diamond
            pygame.draw.polygon(surface, (0, 0, 0),
                                [(cx, cy - 6), (cx + 5, cy), (cx, cy + 6), (cx - 5, cy)])
            pygame.draw.polygon(surface, col,
                                [(cx, cy - 5), (cx + 4, cy), (cx, cy + 5), (cx - 4, cy)])
            surface.set_at((cx - 1, cy - 2), (252, 252, 252))

        # Quality tier border ring
        if self.quality == QUALITY_MAGIC:
            pygame.draw.rect(surface, col, rect, 1)
        elif self.quality == QUALITY_RARE:
            pygame.draw.rect(surface, col, rect.inflate(2, 2), 1)
        elif self.quality == QUALITY_UNIQUE:
            pygame.draw.rect(surface, col, rect.inflate(2, 2), 2)

    def _draw_weapon_icon(self, surface, rect, col):
        hi  = tuple(min(255, c + 50) for c in col)
        cx, cy = rect.centerx, rect.centery
        pygame.draw.line(surface, (0, 0, 0), (rect.left + 1, rect.top + 1), (cx + 2, cy + 2), 4)
        pygame.draw.line(surface, col,       (rect.left + 1, rect.top + 1), (cx + 2, cy + 2), 3)
        pygame.draw.line(surface, hi,        (rect.left + 2, rect.top + 2), (cx,     cy),     1)
        pygame.draw.line(surface, (176, 140, 36),
                         (cx - 5, cy + 4), (cx + 5, cy - 3), 2)
        pygame.draw.line(surface, (176, 140, 36), (cx + 3, cy + 2),
                         (rect.right - 3, rect.bottom - 3), 3)
        pygame.draw.rect(surface, (176, 140, 36),
                         (rect.right - 5, rect.bottom - 5, 4, 4))

    def _draw_armor_icon(self, surface, rect, col):
        cx   = rect.centerx
        dark = tuple(max(0, c - 60) for c in col)
        hi   = tuple(min(255, c + 60) for c in col)
        pts_out = [(rect.left + 1,  rect.top + 1),
                   (rect.right - 1, rect.top + 1),
                   (rect.right - 1, rect.centery + 2),
                   (cx,             rect.bottom - 1),
                   (rect.left + 1,  rect.centery + 2)]
        pts_in  = [(rect.left + 3,  rect.top + 3),
                   (rect.right - 3, rect.top + 3),
                   (rect.right - 3, rect.centery + 1),
                   (cx,             rect.bottom - 3),
                   (rect.left + 3,  rect.centery + 1)]
        pygame.draw.polygon(surface, (0, 0, 0), pts_out)
        pygame.draw.polygon(surface, dark, pts_out)
        pygame.draw.polygon(surface, col,  pts_in)
        pygame.draw.line(surface, hi, (cx, rect.top + 4),  (cx, rect.centery))
        pygame.draw.line(surface, hi, (cx - 4, rect.top + 7), (cx + 4, rect.top + 7))
        pygame.draw.line(surface, hi, pts_out[0], pts_out[4])


# ── Item generation ───────────────────────────────────────────────────────────

def _pick_affixes(quality: int, ilvl: int) -> list[Modifier]:
    """Roll random affixes for the given quality tier and item level."""
    eligible_pre = [p for p in _PREFIXES if p[4] <= ilvl]
    eligible_suf = [s for s in _SUFFIXES if s[4] <= ilvl]

    mods: list[Modifier] = []

    if quality == QUALITY_MAGIC:
        # 1 prefix and/or 1 suffix (at least one guaranteed, no shared mod_kind)
        roll = random.random()
        picks: list[tuple[str, tuple]] = []
        if roll < 0.4 and eligible_pre:
            picks.append(('pre', random.choice(eligible_pre)))
        elif roll < 0.7 and eligible_suf:
            picks.append(('suf', random.choice(eligible_suf)))
        else:
            if eligible_pre:
                picks.append(('pre', random.choice(eligible_pre)))
            if eligible_suf and random.random() < 0.6:
                # Ensure suffix doesn't duplicate the prefix's mod_kind
                used_kind = picks[0][1][1] if picks else None
                suf_pool  = [s for s in eligible_suf if s[1] != used_kind]
                if suf_pool:
                    picks.append(('suf', random.choice(suf_pool)))
        if not picks and eligible_pre:
            picks.append(('pre', random.choice(eligible_pre)))
        for role, p in picks:
            m = Modifier(p[1], round(random.uniform(p[2], p[3]), 1))
            m.name       = p[0]                      # type: ignore[attr-defined]
            m.is_prefix  = (role == 'pre')            # type: ignore[attr-defined]
            m.is_suffix  = (role == 'suf')            # type: ignore[attr-defined]
            mods.append(m)

    elif quality == QUALITY_RARE:
        # 2-3 prefixes + 2-3 suffixes; no duplicate mod kinds across either pool
        used_pre  = set()   # affix names already taken from prefix pool
        used_suf  = set()   # affix names already taken from suffix pool
        used_kinds = set()  # mod_kind values used across both pools (no same stat twice)
        for _ in range(random.randint(2, 3)):
            remaining = [p for p in eligible_pre
                         if p[0] not in used_pre and p[1] not in used_kinds]
            if not remaining:
                break
            p = random.choice(remaining)
            used_pre.add(p[0])
            used_kinds.add(p[1])
            m = Modifier(p[1], round(random.uniform(p[2], p[3]), 1))
            m.is_prefix = True   # type: ignore[attr-defined]
            m.is_suffix = False  # type: ignore[attr-defined]
            m.name      = p[0]   # type: ignore[attr-defined]
            mods.append(m)
        for _ in range(random.randint(2, 3)):
            remaining = [s for s in eligible_suf
                         if s[0] not in used_suf and s[1] not in used_kinds]
            if not remaining:
                break
            s = random.choice(remaining)
            used_suf.add(s[0])
            used_kinds.add(s[1])
            m = Modifier(s[1], round(random.uniform(s[2], s[3]), 1))
            m.is_prefix = False  # type: ignore[attr-defined]
            m.is_suffix = True   # type: ignore[attr-defined]
            m.name      = s[0]   # type: ignore[attr-defined]
            mods.append(m)

    return mods


def _pick_quality(ilvl: int, quality_bonus: int = 0) -> int:
    """Roll item quality based on dungeon level + optional bonus."""
    # Quality thresholds (cumulative %): [normal, magic, rare, unique]
    tables = {
        1: (70, 25,  4,  1),
        2: (55, 30, 12,  3),
        3: (40, 35, 18,  7),
        4: (25, 35, 28, 12),
        5: (15, 30, 35, 20),
    }
    norm, mag, rare, uniq = tables.get(ilvl, (40, 35, 18, 7))
    # quality_bonus shifts mass from normal → up
    bonus = min(quality_bonus, 40)
    norm  = max(5, norm - bonus)
    mag  += bonus // 2
    rare += bonus // 3
    uniq += bonus // 6

    r = random.randint(1, 100)
    if r <= uniq:
        return QUALITY_UNIQUE
    if r <= uniq + rare:
        return QUALITY_RARE
    if r <= uniq + rare + mag:
        return QUALITY_MAGIC
    return QUALITY_NORMAL


def random_equip(tx: int, ty: int, ilvl: int,
                 quality: int | None = None,
                 slot: str | None = None) -> EquipItem:
    """Generate a random equipment item for the given dungeon level."""
    ilvl = max(1, min(5, ilvl))

    if quality is None:
        quality = _pick_quality(ilvl)

    # Try to spawn a unique
    if quality == QUALITY_UNIQUE:
        eligible = [u for u in _UNIQUES
                    if u["min_lvl"] <= ilvl and
                    (slot is None or u["slot"] == slot)]
        if eligible:
            u    = random.choice(eligible)
            mods = [Modifier(kind, val) for kind, val in u["mods"]]
            return EquipItem(tx, ty, u["base"], QUALITY_UNIQUE, mods,
                             unique_name=u["name"], flavor=u["flavor"])
        # Fall back to rare if no eligible uniques
        quality = QUALITY_RARE

    # Choose slot
    if slot is None:
        slot = random.choice([SLOT_WEAPON, SLOT_WEAPON,   # weapons more common
                              SLOT_SHIELD, SLOT_HELM, SLOT_CHEST,
                              SLOT_GLOVES, SLOT_BOOTS, SLOT_BELT,
                              SLOT_RING,   SLOT_AMULET])

    # Choose base type
    if slot == SLOT_WEAPON:
        base = random.choice(_LEVEL_WEAPONS.get(ilvl, ["Short Sword"]))
    elif slot in _LEVEL_ARMOR:
        base = _LEVEL_ARMOR[slot].get(ilvl, list(_LEVEL_ARMOR[slot].values())[0])
    elif slot == SLOT_RING:
        base = "Ring"
    else:
        base = "Amulet"

    mods = _pick_affixes(quality, ilvl)
    return EquipItem(tx, ty, base, quality, mods)


class TreasureChest:
    """A one-time loot chest placed in a room. Opens when the player touches it."""

    SIZE = 22

    def __init__(self, tx: int, ty: int):
        self.x   = float(tx * TILE_SIZE + TILE_SIZE // 2)
        self.y   = float(ty * TILE_SIZE + TILE_SIZE // 2)
        self.rect = pygame.Rect(0, 0, self.SIZE, self.SIZE)
        self.rect.centerx = round(self.x)
        self.rect.centery = round(self.y)
        self.opened      = False
        self._anim_timer = 0.0   # lid-open animation

    def update(self, dt: float):
        if self._anim_timer > 0:
            self._anim_timer = max(0.0, self._anim_timer - dt)

    def open(self, player, item_list: list, level: int):
        """Spawn 2-3 items + a gold pile into item_list."""
        if self.opened:
            return
        self.opened      = True
        self._anim_timer = 0.55
        scatter = [(-16, -16), (16, -16), (0, -22), (-20, 0), (20, 0)]
        random.shuffle(scatter)
        n_items = random.randint(2, 3)
        for ox, oy in scatter[:n_items]:
            itm = random_equip(0, 0, level, quality=_pick_quality(level, quality_bonus=25))
            itm._reposition(self.x + ox, self.y + oy)
            item_list.append(itm)
        gold = GoldPile(0, 0, random.randint(20, 50) * level)
        gold._reposition(self.x, self.y + 10)
        item_list.append(gold)

    def draw(self, surface: pygame.Surface, camera):
        from src.utils.camera import Camera
        ox = int(self.x - camera.x)
        oy = int(self.y - camera.y)

        if self.opened:
            # Draw an open chest (lid tilted back)
            _WOOD  = (120,  70,  20)
            _WOOD_D= ( 70,  38,   8)
            _GOLD  = (220, 175,  40)
            _BLACK = (  0,   0,   0)
            hw = self.SIZE // 2
            # Base
            pygame.draw.rect(surface, _BLACK, (ox - hw - 1, oy - 2, self.SIZE + 2, 12))
            pygame.draw.rect(surface, _WOOD_D,(ox - hw,     oy - 1, self.SIZE,     11))
            pygame.draw.line(surface, _GOLD,  (ox - hw, oy - 1), (ox + hw - 1, oy - 1))
            # Open lid (rotated back)
            lid_pts = [
                (ox - hw, oy - 2),
                (ox + hw, oy - 2),
                (ox + hw - 2, oy - 11),
                (ox - hw + 2, oy - 11),
            ]
            pygame.draw.polygon(surface, _WOOD,  lid_pts)
            pygame.draw.polygon(surface, _BLACK, lid_pts, 1)
            return

        # Closed chest
        _WOOD  = (140,  80,  22)
        _WOOD_D= ( 80,  42,   8)
        _GOLD  = (220, 175,  40)
        _BLACK = (  0,   0,   0)
        hw  = self.SIZE // 2
        hh  = self.SIZE // 2

        # Shadow
        sh = pygame.Surface((self.SIZE + 4, 4), pygame.SRCALPHA)
        sh.fill((0, 0, 0, 50))
        surface.blit(sh, (ox - hw - 2, oy + hh - 1))

        # Body
        pygame.draw.rect(surface, _BLACK, (ox - hw - 1, oy - hh + 3, self.SIZE + 2, hh + 1))
        pygame.draw.rect(surface, _WOOD_D,(ox - hw,     oy - hh + 4, self.SIZE,     hh - 1))
        # Lid
        pygame.draw.rect(surface, _BLACK, (ox - hw - 1, oy - hh - 2, self.SIZE + 2, hh - 2))
        pygame.draw.rect(surface, _WOOD,  (ox - hw,     oy - hh - 1, self.SIZE,     hh - 3))
        # Gold latch
        pygame.draw.rect(surface, _GOLD,  (ox - 3, oy - 5, 6, 5))
        pygame.draw.rect(surface, _BLACK, (ox - 3, oy - 5, 6, 5), 1)
        # Planks
        for bx in (ox - hw + 4, ox - hw + 10, ox - hw + 16):
            pygame.draw.line(surface, _WOOD_D, (bx, oy - hh + 4),
                             (bx, oy + hh - 3), 1)
        # Gold trim top-edge
        pygame.draw.line(surface, _GOLD, (ox - hw, oy - hh - 1),
                         (ox + hw - 1, oy - hh - 1))
        pygame.draw.line(surface, _GOLD, (ox - hw, oy - 5),
                         (ox + hw - 1, oy - 5))
        # Glow hint
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003)) * 0.5 + 0.5
        gw = int(14 * pulse)
        if gw > 1:
            gsurf = pygame.Surface((gw * 2, gw * 2), pygame.SRCALPHA)
            pygame.draw.circle(gsurf, (220, 175, 40, 60), (gw, gw), gw)
            surface.blit(gsurf, (ox - gw, oy - gw))


def random_item(tx: int, ty: int, level: int = 1,
                quality_bonus: int = 0) -> Item:
    """
    Factory — returns one of: GoldPile, HealthPotion, or EquipItem.
    quality_bonus nudges item quality upward (higher for tougher enemies).
    """
    roll = random.random()
    if roll < 0.28:
        return GoldPile(tx, ty)
    if roll < 0.46:
        return HealthPotion(tx, ty)
    quality = _pick_quality(level, quality_bonus)
    return random_equip(tx, ty, level, quality)
