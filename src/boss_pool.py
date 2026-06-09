"""
Power-gated boss pool.

Each boss has a Combat Rating (CR) window.  When the player's CR falls inside
that window there is a per-floor spawn chance.  Once a boss is defeated it is
removed from the pool for the rest of the run.

A safety valve forces a boss to appear after it has been eligible for
FORCE_AFTER_FLOORS floors without spawning, so players can never permanently
avoid a boss by luck alone.

If every boss is defeated the pool resets so the cycle continues on deeper
floors (bosses scale via scale_to_level, so second-cycle encounters are harder).
"""
from __future__ import annotations

import random
from dataclasses import dataclass


# ── Boss specifications ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class BossSpec:
    name:         str    # matches Enemy subclass __name__
    cr_min:       int    # minimum player CR to be eligible
    cr_max:       int    # CR above which the window closes (use 9999 for no cap)
    floor_min:    int    # dungeon floor must be at least this
    chance:       float  # probability of spawning per floor when eligible (0–1)
    force_after:  int    # floors past floor_min before a forced spawn


BOSS_SCHEDULE: list[BossSpec] = [
    BossSpec("TrollKing",     cr_min= 15, cr_max= 100, floor_min= 3, chance=0.32, force_after=9),
    BossSpec("Lich",          cr_min= 60, cr_max= 160, floor_min= 7, chance=0.30, force_after=9),
    BossSpec("DemonLord",     cr_min=110, cr_max= 250, floor_min=12, chance=0.28, force_after=9),
    BossSpec("StoneGolem",    cr_min=180, cr_max= 360, floor_min=17, chance=0.25, force_after=9),
    BossSpec("ChaosWitch",    cr_min=240, cr_max= 440, floor_min=22, chance=0.25, force_after=9),
    BossSpec("VampireLord",   cr_min=320, cr_max= 520, floor_min=28, chance=0.22, force_after=9),
    BossSpec("FrostGiant",    cr_min=420, cr_max= 640, floor_min=34, chance=0.22, force_after=9),
    BossSpec("ElderDragon",   cr_min=530, cr_max= 780, floor_min=40, chance=0.20, force_after=9),
    BossSpec("IronColossus",  cr_min=660, cr_max= 950, floor_min=48, chance=0.18, force_after=9),
    BossSpec("VoidReaper",    cr_min=800, cr_max=9999, floor_min=57, chance=0.16, force_after=9),
]


# ── Combat Rating ─────────────────────────────────────────────────────────────

# Gold value per equipped-item quality tier for gear scoring
_GEAR_SCORE = {0: 0, 1: 3, 2: 8, 3: 20}   # Normal / Magic / Rare / Unique


def compute_cr(player, floor: int) -> int:
    """
    Player Combat Rating — used to gate boss eligibility.

        CR = level × 12  +  floor × 3  +  gear_score
        gear_score = Σ _GEAR_SCORE[quality] for each equipped item
    """
    gear = sum(
        _GEAR_SCORE.get(getattr(item, "quality", 0), 0)
        for item in player.equipment.values()
        if item is not None
    )
    return player.level * 12 + floor * 3 + gear


# ── Boss selection ────────────────────────────────────────────────────────────

def pick_boss(player, floor: int,
              defeated: set[str],
              rng: random.Random) -> type | None:
    """
    Return a boss class to spawn this floor, or None.

    Parameters
    ----------
    player   : Player instance (needs .level, .equipment)
    floor    : current dungeon floor number
    defeated : set of boss class-name strings already beaten this run
    rng      : per-dungeon RNG for reproducibility

    The pool auto-resets when all six bosses have been defeated, so the
    cycle continues indefinitely on deeper floors.
    """
    from src.entities.enemy import (TrollKing, Lich, DemonLord, StoneGolem,
                                     ChaosWitch, VampireLord, FrostGiant,
                                     ElderDragon, IronColossus, VoidReaper)
    _CLASS = {
        "TrollKing":    TrollKing,
        "Lich":         Lich,
        "DemonLord":    DemonLord,
        "StoneGolem":   StoneGolem,
        "ChaosWitch":   ChaosWitch,
        "VampireLord":  VampireLord,
        "FrostGiant":   FrostGiant,
        "ElderDragon":  ElderDragon,
        "IronColossus": IronColossus,
        "VoidReaper":   VoidReaper,
    }

    # If every boss defeated → full reset so cycle continues
    all_names = {s.name for s in BOSS_SCHEDULE}
    active_defeated = defeated & all_names
    if active_defeated >= all_names:
        defeated.clear()

    cr = compute_cr(player, floor)

    forced:   list[BossSpec] = []
    eligible: list[BossSpec] = []

    for spec in BOSS_SCHEDULE:
        if spec.name in defeated:
            continue
        if floor < spec.floor_min:
            continue

        in_window  = spec.cr_min <= cr <= spec.cr_max
        past_window = cr > spec.cr_max and spec.cr_max < 9000

        # Force-spawn: eligible floor range exceeded AND player is at least
        # at the minimum CR (prevents forcing on truly under-geared players)
        is_forced = (floor >= spec.floor_min + spec.force_after
                     and not past_window
                     and cr >= spec.cr_min)

        if past_window:
            continue   # player outgrew this boss — skip permanently

        if is_forced:
            forced.append(spec)
        elif in_window:
            eligible.append(spec)

    # Forced bosses take priority (pick the earliest one by schedule order)
    if forced:
        return _CLASS[forced[0].name]

    # Probabilistic spawn from eligible pool — first success wins
    for spec in eligible:
        if rng.random() < spec.chance:
            return _CLASS[spec.name]

    return None


# ── Helper: HUD description ───────────────────────────────────────────────────

def boss_cr_hint(player, floor: int) -> str | None:
    """
    Return a short hint string if a boss is approaching the player's CR, or
    None.  Used to show 'A great evil stirs…' before the boss floor arrives.
    """
    cr   = compute_cr(player, floor)
    for spec in BOSS_SCHEDULE:
        if spec.floor_min <= floor and spec.cr_min <= cr + 20 <= spec.cr_max:
            return spec.name
    return None
