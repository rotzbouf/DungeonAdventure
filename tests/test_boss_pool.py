"""Tests for the power-gated boss pool."""
import random
import pytest

from src.boss_pool import BOSS_SCHEDULE, compute_cr, pick_boss, BossSpec
from src.entities.player import Player
from src.items.item import QUALITY_NORMAL, QUALITY_MAGIC, QUALITY_RARE, QUALITY_UNIQUE


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _player(level: int = 1) -> Player:
    p = Player(0, 0)
    p.level = level
    return p


def _equip_all(player: Player, quality: int):
    """Fill every equipment slot with a valid item of the given quality."""
    from src.items.item import EquipItem, SLOT_WEAPON
    _SLOT_BASES = {
        "weapon": "Dagger",        "shield": "Buckler",
        "helm":   "Cap",           "chest":  "Leather Armor",
        "gloves": "Leather Gloves","boots":  "Leather Boots",
        "belt":   "Sash",          "ring":   "Ring",
        "ring2":  "Ring",          "amulet": "Amulet",
    }
    for slot in player.equipment:
        base = _SLOT_BASES.get(slot, "Short Sword")
        item = EquipItem(0, 0, base_name=base, quality=quality, mods=[])
        player.equipment[slot] = item


# ── compute_cr ────────────────────────────────────────────────────────────────

class TestComputeCR:
    def test_bare_level1_floor1(self):
        p = _player(1)
        cr = compute_cr(p, 1)
        assert cr == 1 * 12 + 1 * 3 + 0   # 15

    def test_gear_adds_score(self):
        p = _player(5)
        _equip_all(p, QUALITY_MAGIC)
        cr_gear  = compute_cr(p, 1)
        cr_bare  = compute_cr(_player(5), 1)
        assert cr_gear > cr_bare

    def test_unique_gear_scores_highest(self):
        p_magic  = _player(10); _equip_all(p_magic,  QUALITY_MAGIC)
        p_unique = _player(10); _equip_all(p_unique, QUALITY_UNIQUE)
        assert compute_cr(p_unique, 5) > compute_cr(p_magic, 5)

    def test_floor_contributes(self):
        p = _player(10)
        assert compute_cr(p, 20) > compute_cr(p, 5)


# ── pick_boss ─────────────────────────────────────────────────────────────────

class TestPickBoss:
    def _rng_always_true(self):
        """RNG that always returns 0 (triggers every chance check)."""
        class _R:
            def random(self): return 0.0
        return _R()

    def test_no_boss_on_floor1_underpowered(self):
        p = _player(1)
        defeated: set = set()
        rng = self._rng_always_true()
        # Floor 1 is below every boss's floor_min
        result = pick_boss(p, 1, defeated, rng)
        assert result is None

    def test_lich_spawns_when_eligible(self):
        from src.entities.enemy import Lich
        # Lich: cr_min=45, cr_max=140, floor_min=3
        # Level 3 bare = 3*12 + 3*3 = 36+9=45 — exactly at min
        p = _player(3)
        defeated: set = set()
        result = pick_boss(p, 3, defeated, self._rng_always_true())
        assert result is Lich

    def test_defeated_boss_not_respawned(self):
        from src.entities.enemy import Lich
        p = _player(3)
        defeated = {"Lich"}
        result = pick_boss(p, 3, defeated, self._rng_always_true())
        assert result is not Lich

    def test_overleveled_skips_boss(self):
        # Lich cr_max=140; a very high-CR player should skip Lich
        from src.entities.enemy import Lich
        p = _player(15); _equip_all(p, QUALITY_UNIQUE)
        cr = compute_cr(p, 5)
        # Ensure CR is well above 140
        if cr <= 140:
            pytest.skip("Player not overleveled enough for this test")
        defeated: set = set()
        # Force floor far past Lich window
        result = pick_boss(p, 5, {"DemonLord","StoneGolem","VampireLord",
                                   "ElderDragon","IronColossus"}, self._rng_always_true())
        # Lich should be skipped (overleveled); only Lich remains un-defeated but past window
        assert result is not Lich

    def test_force_spawn_after_too_many_floors(self):
        from src.entities.enemy import Lich
        # Lich: floor_min=3, force_after=9 → forces at floor 12+
        p = _player(3)   # CR just barely in Lich window
        defeated: set = set()
        # Use an RNG that always returns 1.0 (never triggers random spawn)
        class _NeverRNG:
            def random(self): return 1.0
        result = pick_boss(p, 3 + 9, defeated, _NeverRNG())  # floor 12
        assert result is Lich

    def test_pool_resets_when_all_defeated(self):
        from src.entities.enemy import Lich
        all_names = {s.name for s in BOSS_SCHEDULE}
        defeated = set(all_names)  # all beaten
        p = _player(3)
        # After reset, Lich should be eligible again
        result = pick_boss(p, 3, defeated, self._rng_always_true())
        assert result is Lich
        # And the defeated set was cleared
        assert len(defeated) == 0

    def test_schedule_is_ordered_by_cr(self):
        crs = [s.cr_min for s in BOSS_SCHEDULE]
        assert crs == sorted(crs), "Boss schedule must be in ascending CR order"

    def test_iron_colossus_has_no_upper_cap(self):
        spec = next(s for s in BOSS_SCHEDULE if s.name == "IronColossus")
        assert spec.cr_max >= 9000, "IronColossus should have no upper CR cap"
