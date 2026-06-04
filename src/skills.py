"""
Skill tree — three branches (Combat / Magic / Rogue), each with 8 skills
spread across 4 tiers.  One skill point is awarded per character level.

Layout per tree
───────────────
  Tier 1 (roots, 2 nodes):  always available
  Tier 2 (3 nodes):  each requires one Tier-1 skill
  Tier 3 (2 nodes):  each requires one Tier-2 skill
  Tier 4 (1 capstone): requires one Tier-3 skill
"""
from __future__ import annotations
from dataclasses import dataclass

# ── Skill IDs ──────────────────────────────────────────────────────────────────

# Combat – Tier 1
SK_POWER_STRIKE    = "power_strike"
SK_TOUGHNESS       = "toughness"
# Combat – Tier 2
SK_BATTLE_CRY      = "battle_cry"
SK_IRON_FIST       = "iron_fist"
SK_WHIRLWIND       = "whirlwind"
# Combat – Tier 3
SK_WAR_SHOUT       = "war_shout"
SK_SHIELD_MASTERY  = "shield_mastery"
# Combat – Tier 4
SK_COLOSSUS        = "colossus"

# Magic – Tier 1
SK_ARCANE_MIND      = "arcane_mind"
SK_FIREBALL_MASTERY = "fireball_mastery"
# Magic – Tier 2
SK_ICE_NOVA         = "ice_nova"
SK_MANA_SHIELD      = "mana_shield"
SK_CHAIN_LIGHTNING  = "chain_lightning"
# Magic – Tier 3
SK_ARCANE_SURGE     = "arcane_surge"
SK_ELEMENTAL_FURY   = "elemental_fury"
# Magic – Tier 4
SK_ARCANE_ASCENSION = "arcane_ascension"

# Rogue – Tier 1
SK_CRIT_MASTERY    = "crit_mastery"
SK_EVASION         = "evasion"
# Rogue – Tier 2
SK_POISON_BLADE    = "poison_blade"
SK_SHADOW_STEP     = "shadow_step"
SK_KNIFE_FAN       = "knife_fan"
# Rogue – Tier 3
SK_ASSASSINATION   = "assassination"
SK_SHADOW_ARTS     = "shadow_arts"
# Rogue – Tier 4
SK_DEATH_MARK      = "death_mark"


@dataclass
class SkillDef:
    id:        str
    name:      str
    desc:      str
    max_level: int
    tree:      str          # "combat" | "magic" | "rogue"
    tier:      int          # 1–4
    requires:  str | None = None


_ALL_DEFS: list[SkillDef] = [
    # ── Combat ───────────────────────────────────────────────────────────────
    SkillDef(SK_POWER_STRIKE,   "Power Strike",
             "+8% melee damage per level",              5, "combat", 1),
    SkillDef(SK_TOUGHNESS,      "Toughness",
             "+6% max HP per level",                    5, "combat", 1),

    SkillDef(SK_BATTLE_CRY,     "Battle Cry",
             "B — deal 25–50% bonus dmg for 5 s",       5, "combat", 2,
             requires=SK_POWER_STRIKE),
    SkillDef(SK_IRON_FIST,      "Iron Fist",
             "10/20/30% chance to stun on melee hit",   3, "combat", 2,
             requires=SK_POWER_STRIKE),
    SkillDef(SK_WHIRLWIND,      "Whirlwind",
             "SHIFT+SPC — hit all nearby (25 mana)",    3, "combat", 2,
             requires=SK_TOUGHNESS),

    SkillDef(SK_WAR_SHOUT,      "War Shout",
             "Battle Cry: +3 s duration, +5% dmg/lv",  3, "combat", 3,
             requires=SK_BATTLE_CRY),
    SkillDef(SK_SHIELD_MASTERY, "Shield Mastery",
             "+2 DEF per level; at max: -10% dmg taken",5, "combat", 3,
             requires=SK_WHIRLWIND),

    SkillDef(SK_COLOSSUS,       "Colossus",
             "+50 HP, +10 DEF, immune to slow/freeze",  1, "combat", 4,
             requires=SK_WAR_SHOUT),

    # ── Magic ─────────────────────────────────────────────────────────────────
    SkillDef(SK_ARCANE_MIND,      "Arcane Mind",
             "+10% max mana per level",                 5, "magic", 1),
    SkillDef(SK_FIREBALL_MASTERY, "Fireball Mastery",
             "+15% fireball dmg, -2 mana per level",    5, "magic", 1),

    SkillDef(SK_ICE_NOVA,        "Ice Nova",
             "Unlocks Ice Nova (X)",                    1, "magic", 2,
             requires=SK_ARCANE_MIND),
    SkillDef(SK_MANA_SHIELD,     "Mana Shield",
             "15/30/45% of dmg absorbed by mana",       3, "magic", 2,
             requires=SK_ARCANE_MIND),
    SkillDef(SK_CHAIN_LIGHTNING, "Chain Lightning",
             "Unlocks Chain Lightning (R)",             1, "magic", 2,
             requires=SK_FIREBALL_MASTERY),

    SkillDef(SK_ARCANE_SURGE,    "Arcane Surge",
             "10/20/30% chance spells trigger echo",    3, "magic", 3,
             requires=SK_ICE_NOVA),
    SkillDef(SK_ELEMENTAL_FURY,  "Elemental Fury",
             "+12/24/36% damage for ALL spells",        3, "magic", 3,
             requires=SK_CHAIN_LIGHTNING),

    SkillDef(SK_ARCANE_ASCENSION,"Arcane Ascension",
             "At full mana: spells +50% dmg, -50% cost",1, "magic", 4,
             requires=SK_ARCANE_SURGE),

    # ── Rogue ─────────────────────────────────────────────────────────────────
    SkillDef(SK_CRIT_MASTERY,  "Critical Mastery",
             "+5% crit chance per level",               5, "rogue", 1),
    SkillDef(SK_EVASION,       "Evasion",
             "+4% dodge chance per level",              5, "rogue", 1),

    SkillDef(SK_POISON_BLADE,  "Poison Blade",
             "Melee hits apply Poison (25/50/75%)",     3, "rogue", 2,
             requires=SK_CRIT_MASTERY),
    SkillDef(SK_SHADOW_STEP,   "Shadow Step",
             "Unlocks Blink (V), -5 mana per level",    3, "rogue", 2,
             requires=SK_EVASION),
    SkillDef(SK_KNIFE_FAN,     "Knife Fan",
             "Arrows pierce +1/2/3 extra enemies",      3, "rogue", 2,
             requires=SK_EVASION),

    SkillDef(SK_ASSASSINATION, "Assassination",
             "Crits deal +25/50/75% extra damage",      3, "rogue", 3,
             requires=SK_POISON_BLADE),
    SkillDef(SK_SHADOW_ARTS,   "Shadow Arts",
             "+5% speed, +1% dodge, +10% blink/level",  5, "rogue", 3,
             requires=SK_SHADOW_STEP),

    SkillDef(SK_DEATH_MARK,    "Death Mark",
             "Enemies explode on kill: 20% HP AoE",     1, "rogue", 4,
             requires=SK_ASSASSINATION),
]

_BY_ID: dict[str, SkillDef] = {s.id: s for s in _ALL_DEFS}


# ── SkillTree ──────────────────────────────────────────────────────────────────

class SkillTree:
    def __init__(self):
        self.levels:       dict[str, int] = {s.id: 0 for s in _ALL_DEFS}
        self.skill_points: int = 0

    # ── Queries ────────────────────────────────────────────────────────────────

    def level(self, sid: str) -> int:
        return self.levels.get(sid, 0)

    def is_unlocked(self, sid: str) -> bool:
        return self.levels.get(sid, 0) > 0

    def can_spend(self, sid: str) -> bool:
        if self.skill_points <= 0:
            return False
        d = _BY_ID.get(sid)
        if not d:
            return False
        if self.levels.get(sid, 0) >= d.max_level:
            return False
        if d.requires and not self.is_unlocked(d.requires):
            return False
        return True

    def spend(self, sid: str) -> bool:
        if not self.can_spend(sid):
            return False
        self.levels[sid] = self.levels.get(sid, 0) + 1
        self.skill_points -= 1
        return True

    # ── Combat bonuses ─────────────────────────────────────────────────────────

    def melee_damage_bonus(self) -> float:
        return self.levels.get(SK_POWER_STRIKE, 0) * 0.08

    def max_hp_bonus(self) -> float:
        return self.levels.get(SK_TOUGHNESS, 0) * 0.06

    def battle_cry_bonus(self) -> float:
        lvl = self.levels.get(SK_BATTLE_CRY, 0)
        ext = self.levels.get(SK_WAR_SHOUT,  0) * 0.05
        return 0.25 + lvl * 0.05 + ext

    def battle_cry_duration(self) -> float:
        """Total active duration in seconds."""
        from src.settings import BATTLE_CRY_DURATION
        return BATTLE_CRY_DURATION + self.levels.get(SK_WAR_SHOUT, 0) * 3.0

    def has_whirlwind(self) -> bool:
        return self.is_unlocked(SK_WHIRLWIND)

    def whirlwind_damage_bonus(self) -> float:
        """Extra multiplier for whirlwind damage."""
        return 1.0 + self.levels.get(SK_WHIRLWIND, 0) * 0.25

    def iron_fist_stun_chance(self) -> float:
        """Probability (0–1) to stun an enemy on melee hit."""
        return self.levels.get(SK_IRON_FIST, 0) * 0.10

    def shield_mastery_def(self) -> int:
        return self.levels.get(SK_SHIELD_MASTERY, 0) * 2

    def shield_mastery_resist(self) -> float:
        """Damage reduction fraction (0–0.10) at max level."""
        return 0.10 if self.levels.get(SK_SHIELD_MASTERY, 0) >= 5 else 0.0

    def has_colossus(self) -> bool:
        return self.is_unlocked(SK_COLOSSUS)

    # ── Magic bonuses ──────────────────────────────────────────────────────────

    def max_mana_bonus(self) -> float:
        return self.levels.get(SK_ARCANE_MIND, 0) * 0.10

    def fireball_damage_mult(self) -> float:
        return 1.0 + self.levels.get(SK_FIREBALL_MASTERY, 0) * 0.15

    def fireball_mana_discount(self) -> int:
        return self.levels.get(SK_FIREBALL_MASTERY, 0) * 2

    def has_ice_nova(self) -> bool:
        return self.is_unlocked(SK_ICE_NOVA)

    def has_chain_lightning(self) -> bool:
        return self.is_unlocked(SK_CHAIN_LIGHTNING)

    def mana_shield_fraction(self) -> float:
        """Fraction of incoming damage absorbed by mana (0–0.45)."""
        return self.levels.get(SK_MANA_SHIELD, 0) * 0.15

    def arcane_surge_chance(self) -> float:
        """Probability spell triggers a secondary echo blast."""
        return self.levels.get(SK_ARCANE_SURGE, 0) * 0.10

    def elemental_fury_mult(self) -> float:
        """Additive spell damage bonus from Elemental Fury."""
        return self.levels.get(SK_ELEMENTAL_FURY, 0) * 0.12

    def has_arcane_ascension(self) -> bool:
        return self.is_unlocked(SK_ARCANE_ASCENSION)

    # ── Rogue bonuses ──────────────────────────────────────────────────────────

    def crit_bonus(self) -> float:
        base = self.levels.get(SK_CRIT_MASTERY, 0) * 5.0
        base += self.levels.get(SK_SHADOW_ARTS, 0) * 1.0
        return base

    def dodge_chance(self) -> float:
        base = self.levels.get(SK_EVASION, 0) * 4.0
        base += self.levels.get(SK_SHADOW_ARTS, 0) * 1.0
        return base

    def poison_blade_chance(self) -> float:
        return self.levels.get(SK_POISON_BLADE, 0) * 0.25

    def has_blink(self) -> bool:
        return self.is_unlocked(SK_SHADOW_STEP)

    def blink_mana_discount(self) -> int:
        return self.levels.get(SK_SHADOW_STEP, 0) * 5

    def blink_range_bonus(self) -> float:
        """Extra fraction of blink range from Shadow Arts."""
        return self.levels.get(SK_SHADOW_ARTS, 0) * 0.10

    def knife_fan_count(self) -> int:
        """Number of extra targets pierced by arrows."""
        return self.levels.get(SK_KNIFE_FAN, 0)

    def assassination_crit_bonus(self) -> float:
        """Extra damage fraction on critical hits."""
        return self.levels.get(SK_ASSASSINATION, 0) * 0.25

    def shadow_arts_speed_bonus(self) -> float:
        return self.levels.get(SK_SHADOW_ARTS, 0) * 0.05

    def has_death_mark(self) -> bool:
        return self.is_unlocked(SK_DEATH_MARK)

    # ── Serialisation ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {"levels": dict(self.levels), "points": self.skill_points}

    @classmethod
    def from_dict(cls, data: dict) -> "SkillTree":
        st = cls()
        for k, v in data.get("levels", {}).items():
            if k in st.levels:
                st.levels[k] = v
        st.skill_points = data.get("points", 0)
        return st
