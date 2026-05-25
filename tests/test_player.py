"""Tests for the Player entity."""
import pytest
from src.entities.player import Player
from src.skills import SkillTree, SK_TOUGHNESS, SK_ARCANE_MIND
from src.settings import (PLAYER_MAX_HP, PLAYER_MAX_MANA, BASE_STR,
                           BASE_DEX, BASE_VIT, BASE_ENE, XP_BASE, MAX_PLAYER_LEVEL)
from src.items.item import (EquipItem, HealthPotion, GoldPile, Modifier,
                             QUALITY_NORMAL, QUALITY_MAGIC, QUALITY_UNIQUE,
                             SLOT_WEAPON, SLOT_CHEST, SLOT_RING,
                             MOD_ATK, MOD_DEF, MOD_MAX_HP, MOD_MAX_MANA)


# ── Derived stats ─────────────────────────────────────────────────────────────

class TestDerivedStats:
    def test_attack_increases_with_str(self):
        p = Player(0, 0)
        base = p.attack
        p.str_pts += 2
        assert p.attack == base + 4     # +2 attack per STR above floor

    def test_defense_increases_with_dex(self):
        p = Player(0, 0)
        base = p.defense
        p.dex_pts += 3
        assert p.defense == base + 3    # +1 DEF per DEX above floor

    def test_max_hp_total_increases_with_vit(self):
        p = Player(0, 0)
        base = p.max_hp_total
        p.vit_pts += 2
        assert p.max_hp_total == base + 20  # +10 HP per VIT above floor

    def test_max_mana_total_increases_with_ene(self):
        p = Player(0, 0)
        base = p.max_mana_total
        p.ene_pts += 3
        assert p.max_mana_total == base + 15  # +5 mana per ENE above floor

    def test_crit_chance_increases_with_dex(self):
        p = Player(0, 0)
        base = p.crit_chance
        p.dex_pts += 4
        assert abs(p.crit_chance - (base + 2.0)) < 1e-9   # +0.5% per DEX

    def test_toughness_skill_scales_max_hp(self):
        p = Player(0, 0)
        base = p.max_hp_total
        p.skill_tree = SkillTree()
        p.skill_tree.skill_points = 2
        p.skill_tree.spend(SK_TOUGHNESS)
        p.skill_tree.spend(SK_TOUGHNESS)
        # 2 levels × 6% = 12% bonus
        expected = int(base * 1.12)
        assert p.max_hp_total == expected

    def test_arcane_mind_scales_max_mana(self):
        p = Player(0, 0)
        base = p.max_mana_total
        p.skill_tree = SkillTree()
        p.skill_tree.skill_points = 1
        p.skill_tree.spend(SK_ARCANE_MIND)
        expected = int(base * 1.10)
        assert p.max_mana_total == expected

    def test_equip_bonus_adds_to_attack(self):
        p    = Player(0, 0)
        base = p.attack
        mod  = Modifier(MOD_ATK, 10)
        item = EquipItem(0, 0, "Broad Sword", QUALITY_NORMAL, [mod])
        p.equipment[SLOT_WEAPON] = item
        assert p.attack == base + 10


# ── Inventory ─────────────────────────────────────────────────────────────────

class TestInventory:
    def test_equip_item_goes_to_slot_if_empty(self):
        p    = Player(0, 0)
        item = EquipItem(0, 0, "Cap", QUALITY_NORMAL, [])
        p.add_item(item)
        assert p.equipment["helm"] is item

    def test_equip_item_goes_to_backpack_if_slot_full(self):
        p     = Player(0, 0)
        item1 = EquipItem(0, 0, "Cap", QUALITY_NORMAL, [])
        item2 = EquipItem(0, 0, "Cap", QUALITY_NORMAL, [])
        p.add_item(item1)
        p.add_item(item2)
        assert p.equipment["helm"] is item1
        assert item2 in p.backpack

    def test_ring_fills_both_ring_slots(self):
        p    = Player(0, 0)
        r1   = EquipItem(0, 0, "Ring", QUALITY_NORMAL, [])
        r2   = EquipItem(0, 0, "Ring", QUALITY_NORMAL, [])
        p.add_item(r1)
        p.add_item(r2)
        assert p.equipment["ring"]  is r1
        assert p.equipment["ring2"] is r2

    def test_third_ring_goes_to_backpack(self):
        p  = Player(0, 0)
        for _ in range(3):
            p.add_item(EquipItem(0, 0, "Ring", QUALITY_NORMAL, []))
        assert len(p.backpack) == 1

    def test_potion_added_to_potions_list(self):
        p   = Player(0, 0)
        pot = HealthPotion(0, 0, 30)
        p.add_item(pot)
        assert pot in p.potions

    def test_equip_swap_returns_old_item(self):
        p    = Player(0, 0)
        old  = EquipItem(0, 0, "Cap", QUALITY_NORMAL, [])
        new  = EquipItem(0, 0, "Helm", QUALITY_MAGIC, [])
        p.equipment["helm"] = old
        prev = p.equip(new, "helm")
        assert prev is old
        assert p.equipment["helm"] is new

    def test_unequip_moves_to_backpack(self):
        p    = Player(0, 0)
        item = EquipItem(0, 0, "Cap", QUALITY_NORMAL, [])
        p.equipment["helm"] = item
        p.unequip("helm")
        assert p.equipment["helm"] is None
        assert item in p.backpack


# ── use_potion ────────────────────────────────────────────────────────────────

class TestUsePotion:
    def test_use_potion_restores_hp(self):
        p     = Player(0, 0)
        p.hp  = 50.0
        p.add_item(HealthPotion(0, 0, 30))
        used  = p.use_potion()
        assert used
        assert p.hp == 80.0

    def test_use_potion_fails_at_full_hp(self):
        p = Player(0, 0)
        p.hp = p.max_hp_total
        p.add_item(HealthPotion(0, 0, 30))
        used = p.use_potion()
        assert not used
        assert len(p.potions) == 1   # potion was NOT consumed

    def test_use_potion_fails_without_potions(self):
        p    = Player(0, 0)
        p.hp = 10.0
        assert not p.use_potion()

    def test_hp_capped_at_max(self):
        p    = Player(0, 0)
        p.hp = p.max_hp_total - 5
        p.add_item(HealthPotion(0, 0, 100))
        p.use_potion()
        assert p.hp == p.max_hp_total


# ── Combat ────────────────────────────────────────────────────────────────────

class TestCombat:
    def test_take_damage_reduces_hp(self):
        p   = Player(0, 0)
        p._invincible_timer = 0.0
        pre = p.hp
        p.take_damage(20)
        assert p.hp < pre

    def test_defense_reduces_incoming_damage(self):
        p   = Player(0, 0)
        p._invincible_timer = 0.0
        actual = p.take_damage(p.defense + 5)
        assert actual == 5    # 5 after defense

    def test_minimum_1_damage(self):
        p = Player(0, 0)
        p._invincible_timer = 0.0
        # Give massive defense
        p.equipment[SLOT_CHEST] = EquipItem(
            0, 0, "Plate Armor", QUALITY_NORMAL,
            [Modifier(MOD_DEF, 999)])
        actual = p.take_damage(1)
        assert actual == 1   # floor at 1

    def test_invincible_timer_blocks_damage(self):
        p = Player(0, 0)
        p._invincible_timer = 1.0
        assert p.take_damage(50) == 0
        assert p.hp == float(PLAYER_MAX_HP)

    def test_heal_capped_at_max(self):
        p = Player(0, 0)
        p.hp = 10.0
        p.heal(9999)
        assert p.hp == p.max_hp_total

    def test_is_alive_false_below_zero(self):
        p    = Player(0, 0)
        p.hp = 0.0
        assert not p.is_alive()

    def test_is_alive_true_above_zero(self):
        p = Player(0, 0)
        assert p.is_alive()


# ── gain_xp / levelling ───────────────────────────────────────────────────────

class TestGainXP:
    def test_gain_xp_increases_xp(self):
        p = Player(0, 0)
        p.gain_xp(10)
        assert p.xp == 10

    def test_level_up_on_threshold(self):
        p   = Player(0, 0)
        leveled = p.gain_xp(p.xp_to_next)
        assert leveled
        assert p.level == 2

    def test_level_up_grants_stat_points(self):
        p   = Player(0, 0)
        pre = p.stat_points
        p.gain_xp(p.xp_to_next)
        from src.settings import STAT_POINTS_PER_LEVEL
        assert p.stat_points == pre + STAT_POINTS_PER_LEVEL

    def test_level_up_grants_skill_point(self):
        p   = Player(0, 0)
        pre = p.skill_tree.skill_points
        p.gain_xp(p.xp_to_next)
        assert p.skill_tree.skill_points == pre + 1

    def test_no_xp_gain_at_max_level(self):
        p       = Player(0, 0)
        p.level = MAX_PLAYER_LEVEL
        leveled = p.gain_xp(99999)
        assert not leveled
        assert p.level == MAX_PLAYER_LEVEL

    def test_multi_level_up_in_one_call(self):
        p = Player(0, 0)
        p.gain_xp(p.xp_to_next * 10)
        assert p.level > 2

    def test_xp_carries_over_across_levels(self):
        p      = Player(0, 0)
        thresh = p.xp_to_next
        p.gain_xp(thresh + 5)
        assert p.level == 2
        assert p.xp == 5


# ── spend_stat ────────────────────────────────────────────────────────────────

class TestSpendStat:
    def test_spend_str(self):
        p = Player(0, 0)
        p.stat_points = 1
        ok = p.spend_stat("str")
        assert ok
        assert p.str_pts == BASE_STR + 1
        assert p.stat_points == 0

    def test_spend_vit_increases_max_hp_and_heals(self):
        p         = Player(0, 0)
        p.stat_points = 1
        p.hp      = p.max_hp_total
        old_max   = p.max_hp_total
        p.spend_stat("vit")
        assert p.max_hp_total > old_max
        assert p.hp == p.max_hp_total   # auto-healed by the vit delta

    def test_spend_stat_fails_without_points(self):
        p = Player(0, 0)
        assert not p.spend_stat("str")

    def test_spend_unknown_stat(self):
        p = Player(0, 0)
        p.stat_points = 1
        assert not p.spend_stat("lck")
        assert p.stat_points == 1   # not consumed
