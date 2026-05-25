"""Tests for the skill tree."""
import pytest
from src.skills import (SkillTree, SK_POWER_STRIKE, SK_TOUGHNESS,
                        SK_BATTLE_CRY, SK_WHIRLWIND, SK_ARCANE_MIND,
                        SK_FIREBALL_MASTERY, SK_ICE_NOVA, SK_CHAIN_LIGHTNING,
                        SK_CRIT_MASTERY, SK_EVASION, SK_POISON_BLADE,
                        SK_SHADOW_STEP)


# ── Helpers ───────────────────────────────────────────────────────────────────

def tree_with(skill_id: str, levels: int = 1) -> SkillTree:
    st = SkillTree()
    st.skill_points = levels
    for _ in range(levels):
        assert st.spend(skill_id), f"spend({skill_id}) failed"
    return st


# ── Basic spend / level ───────────────────────────────────────────────────────

class TestSpend:
    def test_spend_without_points_returns_false(self):
        st = SkillTree()
        assert not st.spend(SK_POWER_STRIKE)

    def test_spend_grants_level(self):
        st = SkillTree()
        st.skill_points = 1
        assert st.spend(SK_POWER_STRIKE)
        assert st.level(SK_POWER_STRIKE) == 1

    def test_spend_consumes_point(self):
        st = SkillTree()
        st.skill_points = 1
        st.spend(SK_POWER_STRIKE)
        assert st.skill_points == 0

    def test_cannot_exceed_max_level(self):
        st = SkillTree()
        st.skill_points = 10
        for _ in range(10):
            st.spend(SK_POWER_STRIKE)           # max_level = 5
        assert st.level(SK_POWER_STRIKE) == 5

    def test_prerequisite_blocks_spend(self):
        st = SkillTree()
        st.skill_points = 5
        # battle_cry requires power_strike
        assert not st.spend(SK_BATTLE_CRY)

    def test_prerequisite_satisfied(self):
        st = SkillTree()
        st.skill_points = 2
        st.spend(SK_POWER_STRIKE)
        assert st.spend(SK_BATTLE_CRY)

    def test_unknown_skill_returns_false(self):
        st = SkillTree()
        st.skill_points = 1
        assert not st.spend("nonexistent_skill")


# ── Bonus getters ─────────────────────────────────────────────────────────────

class TestBonuses:
    def test_melee_damage_bonus_scales(self):
        st = SkillTree()
        st.skill_points = 3
        for _ in range(3):
            st.spend(SK_POWER_STRIKE)
        assert abs(st.melee_damage_bonus() - 0.24) < 1e-9

    def test_max_hp_bonus(self):
        st = tree_with(SK_TOUGHNESS, 2)
        assert abs(st.max_hp_bonus() - 0.12) < 1e-9

    def test_crit_bonus(self):
        st = tree_with(SK_CRIT_MASTERY, 3)
        assert st.crit_bonus() == 15.0

    def test_dodge_chance(self):
        st = tree_with(SK_EVASION, 5)
        assert st.dodge_chance() == 20.0

    def test_fireball_mult(self):
        st = tree_with(SK_FIREBALL_MASTERY, 2)
        assert abs(st.fireball_damage_mult() - 1.30) < 1e-9

    def test_fireball_discount(self):
        st = tree_with(SK_FIREBALL_MASTERY, 3)
        assert st.fireball_mana_discount() == 6

    def test_has_ice_nova_false_without_prereq(self):
        st = SkillTree()
        assert not st.has_ice_nova()

    def test_has_ice_nova_with_unlock(self):
        st = SkillTree()
        st.skill_points = 2
        st.spend(SK_ARCANE_MIND)
        st.spend(SK_ICE_NOVA)
        assert st.has_ice_nova()

    def test_has_chain_lightning_with_unlock(self):
        st = SkillTree()
        st.skill_points = 2
        st.spend(SK_FIREBALL_MASTERY)
        st.spend(SK_CHAIN_LIGHTNING)
        assert st.has_chain_lightning()

    def test_blink_requires_shadow_step(self):
        st = SkillTree()
        assert not st.has_blink()
        st.skill_points = 2
        st.spend(SK_EVASION)
        st.spend(SK_SHADOW_STEP)
        assert st.has_blink()

    def test_poison_blade_chance_scales(self):
        st = SkillTree()
        st.skill_points = 4
        st.spend(SK_CRIT_MASTERY)
        for _ in range(3):
            st.spend(SK_POISON_BLADE)
        assert st.poison_blade_chance() == 0.75

    def test_battle_cry_bonus_base(self):
        st = SkillTree()
        st.skill_points = 2
        st.spend(SK_POWER_STRIKE)
        st.spend(SK_BATTLE_CRY)
        # level 1 → 0.25 + 1*0.05 = 0.30
        assert abs(st.battle_cry_bonus() - 0.30) < 1e-9


# ── Serialisation ─────────────────────────────────────────────────────────────

class TestSerialisation:
    def test_round_trip(self):
        st = SkillTree()
        st.skill_points = 3
        st.spend(SK_POWER_STRIKE)
        st.spend(SK_TOUGHNESS)
        st.skill_points = 5
        d  = st.to_dict()
        st2 = SkillTree.from_dict(d)
        assert st2.level(SK_POWER_STRIKE) == 1
        assert st2.level(SK_TOUGHNESS)    == 1
        assert st2.skill_points           == 5

    def test_from_dict_ignores_unknown_keys(self):
        st = SkillTree.from_dict({"levels": {"bogus_skill": 9}, "points": 0})
        assert st.level("bogus_skill") == 0

    def test_from_empty_dict(self):
        st = SkillTree.from_dict({})
        assert st.skill_points == 0
        assert all(v == 0 for v in st.levels.values())
