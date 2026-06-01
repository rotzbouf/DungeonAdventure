"""
Enchantment system.

Items may have 0-3 enchantment slots (very rare).
Each slot can hold one named enchantment from the registry.
Cross-item synergies activate when two enchantments share a tag pair
across all currently equipped items.
"""
from __future__ import annotations
import random

from src.items.item import (
    MOD_ATK, MOD_ATK_PCT, MOD_DEF, MOD_MAX_HP, MOD_HP_REGEN,
    MOD_LIFE_STEAL, MOD_CRIT, MOD_THORNS, MOD_SPEED,
    MOD_GOLD_FIND, MOD_MAX_MANA, MOD_ATK_SPD,
    QUALITY_NORMAL, QUALITY_MAGIC, QUALITY_RARE, QUALITY_UNIQUE,
)


# ── Enchantment class ─────────────────────────────────────────────────────────

class Enchantment:
    def __init__(self, eid: str, name: str, color: tuple,
                 mods: list[tuple[str, float]], tags: list[str],
                 cost: int, rarity: str):
        self.id     = eid
        self.name   = name
        self.color  = color   # display colour
        self.mods   = mods    # [(mod_kind, value), ...]
        self.tags   = tags    # synergy group tags
        self.cost   = cost    # gold cost at the Enchanter
        self.rarity = rarity  # common / uncommon / rare / veryrare / legendary

    def get_mod(self, kind: str) -> float:
        return sum(v for k, v in self.mods if k == kind)

    def describe_lines(self) -> list[str]:
        from src.items.item import Modifier
        return [Modifier(k, v).describe() for k, v in self.mods]


# ── Registry ──────────────────────────────────────────────────────────────────

ENCHANTMENTS: dict[str, Enchantment] = {}


def _reg(eid, name, color, mods, tags, cost, rarity):
    ENCHANTMENTS[eid] = Enchantment(eid, name, color, mods, tags, cost, rarity)


_RED    = (220,  60,  60)
_BLUE   = ( 80, 160, 240)
_PURPLE = (200, 100, 255)
_GREEN  = ( 60, 200, 100)
_GOLD   = (220, 175,   0)
_ORANGE = (255, 140,   0)
_CRIMSON= (180,  30,  30)

# ── Common (40 %) ─────────────────────────────────────────────────────────────
_reg("E_BLOODRAGE",    "Bloodrage",      _RED,     [(MOD_LIFE_STEAL, 6)],                         ["assault", "blood"],    80, "common")
_reg("E_RENDING",      "Rending",        _RED,     [(MOD_ATK_PCT, 20)],                           ["assault", "power"],    80, "common")
_reg("E_BULWARK",      "Bulwark",        _BLUE,    [(MOD_DEF, 20)],                               ["ward",    "iron"],     80, "common")
_reg("E_VITALITY",     "Vitality",       _BLUE,    [(MOD_MAX_HP, 40)],                            ["ward",    "life"],     80, "common")
_reg("E_SWIFTNESS",    "Swiftness",      _GREEN,   [(MOD_SPEED, 18)],                             ["shadow",  "speed"],    80, "common")
_reg("E_STRIKING",     "Striking",       _RED,     [(MOD_ATK, 15)],                               ["assault", "power"],    80, "common")

# ── Uncommon (30 %) ───────────────────────────────────────────────────────────
_reg("E_SHATTER",      "Shatter",        _RED,     [(MOD_CRIT, 10)],                              ["assault", "precise"], 150, "uncommon")
_reg("E_FRENZY",       "Frenzy",         _RED,     [(MOD_ATK_SPD, 15)],                           ["assault", "speed"],   150, "uncommon")
_reg("E_MENDING",      "Mending",        _BLUE,    [(MOD_HP_REGEN, 3.0)],                         ["ward",    "life"],    150, "uncommon")
_reg("E_RETRIBUTION",  "Retribution",    _BLUE,    [(MOD_THORNS, 25)],                            ["ward",    "iron"],    150, "uncommon")
_reg("E_GILDED",       "Gilded",         _GOLD,    [(MOD_GOLD_FIND, 40)],                         ["fortune", "gold"],    150, "uncommon")
_reg("E_IRONWILL",     "Iron Will",      _BLUE,    [(MOD_DEF, 12), (MOD_MAX_HP, 20)],             ["ward",    "iron"],    180, "uncommon")

# ── Rare (20 %) ───────────────────────────────────────────────────────────────
_reg("E_ARCANE_SURGE", "Arcane Surge",   _PURPLE,  [(MOD_MAX_MANA, 25)],                          ["arcane",  "mana"],    300, "rare")
_reg("E_OVERCHARGE",   "Overcharge",     _PURPLE,  [(MOD_ATK, 22)],                               ["arcane",  "power"],   300, "rare")
_reg("E_CHANNELING",   "Channeling",     _PURPLE,  [(MOD_ATK_SPD, 12)],                           ["arcane",  "speed"],   300, "rare")
_reg("E_VENOMOUS",     "Venomous",       _GREEN,   [(MOD_LIFE_STEAL, 8), (MOD_ATK, 12)],          ["shadow",  "blood"],   350, "rare")
_reg("E_LUCKY",        "Lucky",          _GOLD,    [(MOD_CRIT, 8), (MOD_ATK_PCT, 15)],            ["fortune", "precise"], 350, "rare")
_reg("E_FLEETFOOT",    "Fleetfoot",      _GREEN,   [(MOD_ATK_SPD, 12), (MOD_SPEED, 12)],          ["shadow",  "speed"],   350, "rare")
_reg("E_SIPHON",       "Siphon",         _GREEN,   [(MOD_LIFE_STEAL, 10), (MOD_HP_REGEN, 1.5)],   ["shadow",  "blood"],   380, "rare")

# ── Very Rare (8 %) ───────────────────────────────────────────────────────────
_reg("E_ANCIENT_PWR",  "Ancient Power",  _ORANGE,  [(MOD_ATK, 30), (MOD_DEF, 30)],                ["ancient", "power"],   800, "veryrare")
_reg("E_ANCIENT_MGT",  "Ancient Might",  _ORANGE,  [(MOD_MAX_HP, 80), (MOD_MAX_MANA, 20)],         ["ancient", "life"],    800, "veryrare")
_reg("E_ETHEREAL",     "Ethereal",       _PURPLE,  [(MOD_ATK_PCT, 25), (MOD_SPEED, 15), (MOD_CRIT, 5)], ["arcane", "speed"], 900, "veryrare")

# ── Legendary (2 %) ───────────────────────────────────────────────────────────
_reg("E_CURSED",       "Cursed",         _CRIMSON, [(MOD_ATK_PCT, 45), (MOD_MAX_HP, -20)],        ["cursed",  "power"],  1500, "legendary")
_reg("E_DEMONIC",      "Demonic",        _CRIMSON, [(MOD_ATK, 28), (MOD_LIFE_STEAL, 14)],         ["cursed",  "blood"],  1500, "legendary")
_reg("E_WORLDBREAKER", "Worldbreaker",   _CRIMSON, [(MOD_ATK, 50), (MOD_ATK_PCT, 30), (MOD_MAX_HP, -40)], ["cursed", "power"], 2000, "legendary")


# ── Synergy table ─────────────────────────────────────────────────────────────
# (tag_pair, display_name, bonus_mods)
# Activates when any two equipped items share both tags across their enchantments.

SYNERGIES: list[tuple[frozenset, str, list[tuple[str, float]]]] = [
    (frozenset({"assault", "blood"}),    "Blood Frenzy",    [(MOD_ATK_PCT, 15), (MOD_LIFE_STEAL, 3)]),
    (frozenset({"ward",    "iron"}),     "Iron Fortress",   [(MOD_DEF, 15),     (MOD_THORNS, 15)]),
    (frozenset({"ward",    "life"}),     "Undying",         [(MOD_MAX_HP, 40),  (MOD_HP_REGEN, 1.5)]),
    (frozenset({"assault", "precise"}),  "Killing Blow",    [(MOD_CRIT, 8),     (MOD_ATK_PCT, 10)]),
    (frozenset({"shadow",  "speed"}),    "Phantom",         [(MOD_SPEED, 10),   (MOD_ATK_SPD, 10)]),
    (frozenset({"ancient", "cursed"}),   "Abyssal",         [(MOD_ATK, 40),     (MOD_ATK_PCT, 25), (MOD_MAX_HP, -30)]),
    (frozenset({"arcane",  "power"}),    "Spellblade",      [(MOD_ATK, 20),     (MOD_MAX_MANA, 15)]),
    (frozenset({"fortune", "gold"}),     "Treasure Hunter", [(MOD_GOLD_FIND, 30),(MOD_CRIT, 5)]),
    (frozenset({"assault", "speed"}),    "Berserker",       [(MOD_ATK_SPD, 12), (MOD_ATK_PCT, 12)]),
    (frozenset({"shadow",  "blood"}),    "Predator",        [(MOD_LIFE_STEAL, 5),(MOD_ATK, 18)]),
]

RARITY_COLORS = {
    "common":    (188, 188, 188),
    "uncommon":  ( 80, 160, 255),
    "rare":      (220, 175,   0),
    "veryrare":  (200,  80, 255),
    "legendary": (255, 100,  20),
}

RARITY_LABELS = {
    "common":   "Common",
    "uncommon": "Uncommon",
    "rare":     "Rare",
    "veryrare": "Very Rare",
    "legendary":"Legendary",
}


# ── Slot probability tables by item quality ───────────────────────────────────
# Format: [(slot_count, cumulative_weight), ...]  — very rare overall

_SLOT_TABLES = {
    QUALITY_NORMAL: [(0, 98), (1,  2)],
    QUALITY_MAGIC:  [(0, 92), (1,  7), (2,  1)],
    QUALITY_RARE:   [(0, 82), (1, 14), (2,  3), (3, 1)],
    QUALITY_UNIQUE: [(1, 40), (2, 45), (3, 15)],
}


def roll_enchant_slots(quality: int) -> int:
    table = _SLOT_TABLES.get(quality, [(0, 100)])
    r = random.randint(1, 100)
    cumul = 0
    for slots, weight in table:
        cumul += weight
        if r <= cumul:
            return slots
    return 0


# ── Weighted selection ────────────────────────────────────────────────────────

_RARITY_WEIGHTS = {
    "common": 40, "uncommon": 30, "rare": 20, "veryrare": 8, "legendary": 2,
}


def random_enchantment() -> Enchantment:
    pool    = list(ENCHANTMENTS.values())
    weights = [_RARITY_WEIGHTS[e.rarity] for e in pool]
    return random.choices(pool, weights=weights, k=1)[0]


# ── Synergy computation ───────────────────────────────────────────────────────

def active_synergies(all_tags: set[str]) -> list[tuple[str, list[tuple[str, float]]]]:
    """Return (name, bonus_mods) for every synergy whose tags are all present."""
    return [
        (syn_name, bonus_mods)
        for tag_pair, syn_name, bonus_mods in SYNERGIES
        if tag_pair.issubset(all_tags)
    ]
