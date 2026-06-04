"""
Perk system — milestone passive abilities chosen every PERK_INTERVAL levels.

Each perk is a permanent passive effect.  Effects are applied via:
  - player.py stat properties  (flat stat bonuses)
  - combat.py / spells.py      (hooks for conditional effects)
  - player.take_damage()        (damage-reduction perks)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

PERK_INTERVAL = 5   # offer a perk pick every N levels

# ── Perk definition ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Perk:
    id:       str
    name:     str
    tier:     int          # 1–4; matches the milestone range
    category: str          # 'combat' | 'defense' | 'magic' | 'utility'
    desc:     str          # one-line tooltip shown on the pick screen

# ── Category colours (used in the UI) ────────────────────────────────────────
CATEGORY_COLORS = {
    "combat":  (220,  80,  60),
    "defense": ( 60, 140, 220),
    "magic":   (160,  80, 240),
    "utility": ( 60, 200, 100),
}

# ── All perks ─────────────────────────────────────────────────────────────────
# 5 perks per tier × 4 tiers = 20 total.  Each milestone draws 3 from the
# correct tier (excluding any already owned).

ALL_PERKS: list[Perk] = [
    # ── Tier 1  (levels 5, 10) ────────────────────────────────────────────────
    Perk("bloodlust",      "Bloodlust",        1, "combat",
         "Killing an enemy restores 8 HP."),
    Perk("iron_skin",      "Iron Skin",        1, "defense",
         "Reduce all incoming damage by 2."),
    Perk("battle_focus",   "Battle Focus",     1, "combat",
         "+10% critical hit chance."),
    Perk("fortitude",      "Fortitude",        1, "defense",
         "Gain +40 permanent max HP."),
    Perk("spell_surge",    "Spell Surge",      1, "magic",
         "All spell mana costs reduced by 20%."),

    # ── Tier 2  (levels 15, 20) ───────────────────────────────────────────────
    Perk("execute",        "Execute",          2, "combat",
         "Deal +60% damage to enemies below 25% HP."),
    Perk("vampiric",       "Vampiric",         2, "combat",
         "Gain +4% life steal on all hits."),
    Perk("arcane_reserve", "Arcane Reserve",   2, "magic",
         "+50 max mana.  Spells cost an extra 10% less mana."),
    Perk("thorned",        "Thorned",          2, "defense",
         "Reflect 12 damage to every attacker."),
    Perk("precision",      "Precision",        2, "combat",
         "Critical hits deal 3× damage instead of 2×."),

    # ── Tier 3  (levels 25, 30) ───────────────────────────────────────────────
    Perk("berserker",      "Berserker",        3, "combat",
         "+1 ATK for every 5 HP currently missing."),
    Perk("second_wind",    "Second Wind",      3, "defense",
         "Once per floor, survive a killing blow at 1 HP."),
    Perk("arcane_mastery", "Arcane Mastery",   3, "magic",
         "All spells deal +30% damage."),
    Perk("fortified",      "Fortified",        3, "defense",
         "+60 max HP.  Take 10% less damage from all sources."),
    Perk("gold_rush",      "Gold Rush",        3, "utility",
         "+30% gold find.  Enemies drop loot 15% more often."),

    # ── Tier 4  (levels 35, 40) ───────────────────────────────────────────────
    Perk("warlord",        "Warlord",          4, "combat",
         "+12 ATK, +8% crit chance."),
    Perk("undying",        "Undying",          4, "defense",
         "+80 max HP.  Regenerate +2 HP per second."),
    Perk("avatar_of_war",  "Avatar of War",    4, "combat",
         "Deal +25% damage.  Also take 10% more damage."),
    Perk("arcane_overflow","Arcane Overflow",  4, "magic",
         "When at full mana, spells deal +50% damage."),
    Perk("eternal_warrior","Eternal Warrior",  4, "utility",
         "+3 ATK and +3 DEF for every level above 30."),
]

_BY_ID: dict[str, Perk] = {p.id: p for p in ALL_PERKS}


def get_perk(perk_id: str) -> Perk | None:
    return _BY_ID.get(perk_id)


def perk_tier_for_level(level: int) -> int:
    """Return which tier of perks to draw from for this milestone level."""
    if level <= 10:  return 1
    if level <= 20:  return 2
    if level <= 30:  return 3
    return 4


def roll_perk_choices(level: int, owned: list[str],
                       rng: random.Random | None = None) -> list[Perk]:
    """
    Return 3 perk choices for the given milestone level, excluding already
    owned perks.  Falls back to lower-tier perks if the correct tier is
    exhausted.
    """
    if rng is None:
        rng = random.Random()
    tier     = perk_tier_for_level(level)
    pool     = [p for p in ALL_PERKS if p.tier == tier and p.id not in owned]
    if len(pool) < 3:
        # Top up from adjacent tiers
        extra = [p for p in ALL_PERKS if p.tier != tier and p.id not in owned]
        pool  = pool + extra
    rng.shuffle(pool)
    return pool[:3]
