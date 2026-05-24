"""
Skill tree system — three branches (Combat / Magic / Rogue).
Each skill has up to 5 levels; spending a point requires the prerequisite
skill to be unlocked first.  Skill points are awarded once per character level.
"""
from __future__ import annotations

from dataclasses import dataclass

# ── Skill IDs ────────────────────────────────────────────────────────────────

# Combat
SK_POWER_STRIKE    = "power_strike"     # +8% melee dmg / level
SK_TOUGHNESS       = "toughness"        # +6% max HP / level
SK_BATTLE_CRY      = "battle_cry"       # B: +25% dmg 5 s (active, costs mana)
SK_WHIRLWIND       = "whirlwind"        # SHIFT+SPC: hits all nearby (active)

# Magic
SK_FIREBALL_MASTERY= "fireball_mastery" # +15% fireball dmg, −2 mana / level
SK_ARCANE_MIND     = "arcane_mind"      # +10% max mana / level
SK_ICE_NOVA        = "ice_nova"         # unlocks Ice Nova (X)
SK_CHAIN_LIGHTNING = "chain_lightning"  # unlocks Chain Lightning (R)

# Rogue
SK_CRIT_MASTERY    = "crit_mastery"     # +5% crit chance / level
SK_EVASION         = "evasion"          # +4% dodge chance / level
SK_POISON_BLADE    = "poison_blade"     # melee hits apply Poison (3 levels)
SK_SHADOW_STEP     = "shadow_step"      # unlocks Blink (V), −5 mana / level


@dataclass
class SkillDef:
    id:        str
    name:      str
    desc:      str
    max_level: int
    tree:      str              # "combat" | "magic" | "rogue"
    requires:  str | None = None


_ALL_DEFS: list[SkillDef] = [
    # ── Combat ───────────────────────────────────────────────────────────────
    SkillDef(SK_POWER_STRIKE,    "Power Strike",
             "+8% melee damage per level",             5, "combat"),
    SkillDef(SK_TOUGHNESS,       "Toughness",
             "+6% max HP per level",                   5, "combat"),
    SkillDef(SK_BATTLE_CRY,      "Battle Cry",
             "B — +25% dmg for 5 s (20 mana)",        5, "combat",
             requires=SK_POWER_STRIKE),
    SkillDef(SK_WHIRLWIND,       "Whirlwind",
             "SHIFT+SPC — hits all nearby (25 mana)",  5, "combat",
             requires=SK_TOUGHNESS),

    # ── Magic ─────────────────────────────────────────────────────────────────
    SkillDef(SK_FIREBALL_MASTERY, "Fireball Mastery",
             "+15% fireball dmg, -2 mana per level",  5, "magic"),
    SkillDef(SK_ARCANE_MIND,      "Arcane Mind",
             "+10% max mana per level",               5, "magic"),
    SkillDef(SK_ICE_NOVA,         "Ice Nova",
             "Unlocks Ice Nova spell (X)",            1, "magic",
             requires=SK_ARCANE_MIND),
    SkillDef(SK_CHAIN_LIGHTNING,  "Chain Lightning",
             "Unlocks Chain Lightning (R)",           1, "magic",
             requires=SK_FIREBALL_MASTERY),

    # ── Rogue ─────────────────────────────────────────────────────────────────
    SkillDef(SK_CRIT_MASTERY,  "Critical Mastery",
             "+5% crit chance per level",             5, "rogue"),
    SkillDef(SK_EVASION,       "Evasion",
             "+4% dodge chance per level",            5, "rogue"),
    SkillDef(SK_POISON_BLADE,  "Poison Blade",
             "Melee hits apply Poison (25/50/75%)",   3, "rogue",
             requires=SK_CRIT_MASTERY),
    SkillDef(SK_SHADOW_STEP,   "Shadow Step",
             "Unlocks Blink (V), -5 mana/level",      3, "rogue",
             requires=SK_EVASION),
]

_BY_ID: dict[str, SkillDef] = {s.id: s for s in _ALL_DEFS}


class SkillTree:
    def __init__(self):
        self.levels:        dict[str, int] = {s.id: 0 for s in _ALL_DEFS}
        self.skill_points:  int = 0

    # ── Queries ───────────────────────────────────────────────────────────────

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
        if self.levels[sid] >= d.max_level:
            return False
        if d.requires and not self.is_unlocked(d.requires):
            return False
        return True

    def spend(self, sid: str) -> bool:
        if not self.can_spend(sid):
            return False
        self.levels[sid] += 1
        self.skill_points -= 1
        return True

    # ── Bonus getters (consumed by player properties & game logic) ─────────────

    def melee_damage_bonus(self) -> float:
        """Fractional bonus to melee damage output (additive mult)."""
        return self.levels.get(SK_POWER_STRIKE, 0) * 0.08

    def max_hp_bonus(self) -> float:
        return self.levels.get(SK_TOUGHNESS, 0) * 0.06

    def max_mana_bonus(self) -> float:
        return self.levels.get(SK_ARCANE_MIND, 0) * 0.10

    def crit_bonus(self) -> float:
        """Extra crit chance in percent."""
        return self.levels.get(SK_CRIT_MASTERY, 0) * 5.0

    def dodge_chance(self) -> float:
        """Dodge chance in percent (0–100)."""
        return self.levels.get(SK_EVASION, 0) * 4.0

    def fireball_damage_mult(self) -> float:
        return 1.0 + self.levels.get(SK_FIREBALL_MASTERY, 0) * 0.15

    def fireball_mana_discount(self) -> int:
        return self.levels.get(SK_FIREBALL_MASTERY, 0) * 2

    def has_ice_nova(self) -> bool:
        return self.is_unlocked(SK_ICE_NOVA)

    def has_chain_lightning(self) -> bool:
        return self.is_unlocked(SK_CHAIN_LIGHTNING)

    def has_blink(self) -> bool:
        return self.is_unlocked(SK_SHADOW_STEP)

    def blink_mana_discount(self) -> int:
        return self.levels.get(SK_SHADOW_STEP, 0) * 5

    def poison_blade_chance(self) -> float:
        """Probability (0–1) that a melee hit applies Poison."""
        return self.levels.get(SK_POISON_BLADE, 0) * 0.25

    def battle_cry_bonus(self) -> float:
        """Fractional extra damage during Battle Cry (scales with skill level)."""
        lvl = self.levels.get(SK_BATTLE_CRY, 0)
        return 0.25 + lvl * 0.05   # 0.30 → 0.55

    def has_whirlwind(self) -> bool:
        return self.is_unlocked(SK_WHIRLWIND)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {"levels": dict(self.levels), "points": self.skill_points}

    @classmethod
    def from_dict(cls, data: dict) -> "SkillTree":
        st = cls()
        st.levels.update({k: v for k, v in data.get("levels", {}).items()
                          if k in st.levels})
        st.skill_points = data.get("points", 0)
        return st

    # ── Tree iteration (used by UI) ────────────────────────────────────────────

    @staticmethod
    def all_defs() -> list[SkillDef]:
        return _ALL_DEFS

    @staticmethod
    def tree_defs(tree: str) -> list[SkillDef]:
        return [s for s in _ALL_DEFS if s.tree == tree]
