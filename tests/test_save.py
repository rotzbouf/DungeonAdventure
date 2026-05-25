"""Tests for the save / load system."""
import pytest

import src.save as savesys
from src.entities.player import Player
from src.quests import QuestLog
from src.skills import SkillTree, SK_POWER_STRIKE, SK_TOUGHNESS
from src.items.item import (EquipItem, HealthPotion, Modifier,
                             QUALITY_MAGIC, SLOT_WEAPON, MOD_ATK, MOD_DEF)


@pytest.fixture(autouse=True)
def tmp_save(tmp_path, monkeypatch):
    """Redirect save path to a temp directory so tests never touch ~/.dungeonadventure."""
    save_file = tmp_path / "save.json"
    monkeypatch.setattr(savesys, "SAVE_PATH", save_file)
    yield save_file


# ── has_save / delete_save ────────────────────────────────────────────────────

def test_no_save_initially(tmp_save):
    assert not savesys.has_save()


def test_save_creates_file(tmp_save):
    p = Player(0, 0)
    savesys.save_game(p, dungeon_level=1, ng_plus=0)
    assert savesys.has_save()


def test_delete_removes_file(tmp_save):
    p = Player(0, 0)
    savesys.save_game(p, dungeon_level=1, ng_plus=0)
    savesys.delete_save()
    assert not savesys.has_save()


def test_delete_missing_save_is_ok(tmp_save):
    savesys.delete_save()   # should not raise


# ── save_game / load_game round-trip ─────────────────────────────────────────

def test_load_returns_none_when_no_save(tmp_save):
    assert savesys.load_game() is None


def test_load_returns_dict(tmp_save):
    p = Player(0, 0)
    savesys.save_game(p, dungeon_level=2, ng_plus=1)
    data = savesys.load_game()
    assert isinstance(data, dict)


def test_save_persists_dungeon_level(tmp_save):
    p = Player(0, 0)
    savesys.save_game(p, dungeon_level=3, ng_plus=0)
    assert savesys.load_game()["dungeon_level"] == 3


def test_save_persists_ng_plus(tmp_save):
    p = Player(0, 0)
    savesys.save_game(p, dungeon_level=1, ng_plus=2)
    assert savesys.load_game()["ng_plus"] == 2


def test_save_persists_gold(tmp_save):
    p      = Player(0, 0)
    p.gold = 250
    savesys.save_game(p, dungeon_level=1, ng_plus=0)
    assert savesys.load_game()["gold"] == 250


def test_save_persists_stats(tmp_save):
    p         = Player(0, 0)
    p.str_pts = 15
    p.dex_pts = 8
    savesys.save_game(p, dungeon_level=1, ng_plus=0)
    data = savesys.load_game()
    assert data["str_pts"] == 15
    assert data["dex_pts"] == 8


def test_save_persists_skill_levels(tmp_save):
    p = Player(0, 0)
    p.skill_tree.skill_points = 2
    p.skill_tree.spend(SK_POWER_STRIKE)
    p.skill_tree.spend(SK_TOUGHNESS)
    ql = QuestLog()
    savesys.save_game(p, 1, 0, quest_log=ql, skill_tree=p.skill_tree)
    data = savesys.load_game()
    st2  = SkillTree.from_dict(data["skills"])
    assert st2.level(SK_POWER_STRIKE) == 1
    assert st2.level(SK_TOUGHNESS)    == 1


def test_save_persists_potions(tmp_save):
    p = Player(0, 0)
    from src.items.item import HealthPotion
    p.potions = [HealthPotion(0, 0, 35), HealthPotion(0, 0, 20)]
    savesys.save_game(p, 1, 0)
    data = savesys.load_game()
    assert len(data["potions"]) == 2
    assert data["potions"][0]["heal"] == 35


def test_save_persists_equipment(tmp_save):
    p    = Player(0, 0)
    mod  = Modifier(MOD_ATK, 8)
    item = EquipItem(0, 0, "Broad Sword", QUALITY_MAGIC, [mod])
    p.equipment[SLOT_WEAPON] = item
    savesys.save_game(p, 1, 0)
    data = savesys.load_game()
    assert data["equipment"]["weapon"] is not None
    assert data["equipment"]["weapon"]["base_name"] == "Broad Sword"


# ── BUG: max_hp and max_mana must be saved and restored ──────────────────────
# A levelled-up player's HP pool is larger than the default 100.
# After loading, the pool must match what it was at save time.

def test_save_and_restore_preserves_max_hp(tmp_save):
    """
    REGRESSION: Player.max_hp grows +5 per level-up.
    If max_hp is not serialised, a loaded level-10 save will
    silently truncate the player's max HP pool to the default 100.
    """
    p = Player(0, 0)
    # Simulate 9 level-ups worth of max_hp growth
    for _ in range(9):
        p.max_hp += 5
    p.max_mana += 3 * 9
    expected_max_hp   = p.max_hp
    expected_max_mana = p.max_mana

    savesys.save_game(p, dungeon_level=2, ng_plus=0)
    data = savesys.load_game()

    p2 = Player(0, 0)
    savesys.restore_player(p2, data)

    assert p2.max_hp   == expected_max_hp,   (
        f"max_hp not restored: got {p2.max_hp}, expected {expected_max_hp}")
    assert p2.max_mana == expected_max_mana, (
        f"max_mana not restored: got {p2.max_mana}, expected {expected_max_mana}")


# ── restore_player ────────────────────────────────────────────────────────────

def test_restore_player_sets_level(tmp_save):
    p       = Player(0, 0)
    p.level = 7
    p.xp    = 42
    savesys.save_game(p, 1, 0)
    p2 = Player(0, 0)
    savesys.restore_player(p2, savesys.load_game())
    assert p2.level == 7
    assert p2.xp    == 42


def test_restore_player_restores_backpack(tmp_save):
    p    = Player(0, 0)
    item = EquipItem(0, 0, "Cap", QUALITY_MAGIC,
                     [Modifier(MOD_DEF, 3)])
    p.backpack.append(item)
    savesys.save_game(p, 1, 0)
    p2 = Player(0, 0)
    savesys.restore_player(p2, savesys.load_game())
    assert len(p2.backpack) == 1
    assert p2.backpack[0].base_name == "Cap"


def test_restore_player_handles_none_equipment_slots(tmp_save):
    p = Player(0, 0)
    savesys.save_game(p, 1, 0)   # all slots are None
    p2 = Player(0, 0)
    savesys.restore_player(p2, savesys.load_game())
    assert p2.equipment["weapon"] is None


# ── Resilience ────────────────────────────────────────────────────────────────

def test_load_game_returns_none_on_corrupt_file(tmp_save):
    tmp_save.write_text("not valid json {{{{")
    assert savesys.load_game() is None


def test_restore_player_survives_missing_optional_keys(tmp_save):
    """
    Minimal save dict — only required keys present.
    restore_player must not crash even when optional fields are absent.
    """
    p = Player(0, 0)
    minimal = {
        "level":       1,
        "xp":          0,
        "xp_to_next":  80,
        "hp":          100.0,
        "mana":        50.0,
        "gold":        0,
        "str_pts":     10,
        "dex_pts":     5,
        "vit_pts":     10,
        "ene_pts":     5,
        "stat_points": 0,
    }
    savesys.restore_player(p, minimal)   # must not raise


# ── item_to_dict / item_from_dict ─────────────────────────────────────────────

def test_equip_item_round_trip():
    mod  = Modifier(MOD_ATK, 12)
    mod.name      = "Brutal"        # type: ignore
    mod.is_prefix = True            # type: ignore
    mod.is_suffix = False           # type: ignore
    item = EquipItem(0, 0, "Battle Axe", QUALITY_MAGIC, [mod],
                     unique_name="", flavor="")
    d    = savesys.item_to_dict(item)
    item2 = savesys.item_from_dict(d)
    assert item2.base_name == "Battle Axe"
    assert item2.quality   == QUALITY_MAGIC
    assert len(item2.mods) == 1
    assert item2.mods[0].kind  == MOD_ATK
    assert item2.mods[0].value == 12


def test_potion_round_trip():
    pot  = HealthPotion(0, 0, 40)
    d    = savesys.item_to_dict(pot)
    pot2 = savesys.item_from_dict(d)
    assert isinstance(pot2, HealthPotion)
    assert pot2.heal_amount == 40


def test_item_to_dict_none_returns_none():
    assert savesys.item_to_dict(None) is None


def test_item_from_dict_none_returns_none():
    assert savesys.item_from_dict(None) is None


def test_item_from_dict_empty_returns_none():
    assert savesys.item_from_dict({}) is None
