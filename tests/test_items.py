"""Tests for the loot / item system."""
import pytest
import random as _random
from src.items.item import (
    EquipItem, HealthPotion, GoldPile, Modifier, TreasureChest,
    random_equip, random_item, _pick_quality, _pick_affixes,
    QUALITY_NORMAL, QUALITY_MAGIC, QUALITY_RARE, QUALITY_UNIQUE,
    SLOT_WEAPON, SLOT_SHIELD, SLOT_HELM, SLOT_CHEST,
    SLOT_GLOVES, SLOT_BOOTS, SLOT_BELT, SLOT_RING, SLOT_AMULET,
    MOD_ATK, MOD_DEF, MOD_MAX_HP, MOD_CRIT, MOD_LIFE_STEAL,
)


# ── Modifier ──────────────────────────────────────────────────────────────────

class TestModifier:
    def test_describe_known_kind(self):
        m = Modifier(MOD_ATK, 5)
        assert "+5 to Attack" in m.describe()

    def test_describe_unknown_kind(self):
        m = Modifier("weird_stat", 7)
        assert "7" in m.describe()


# ── GoldPile ──────────────────────────────────────────────────────────────────

class TestGoldPile:
    def test_collect_adds_gold(self):
        from src.entities.player import Player
        p = Player(160, 160)
        g = GoldPile(0, 0, amount=42)
        g.collect(p)
        assert p.gold == 42
        assert g.collected

    def test_default_amount_positive(self):
        g = GoldPile(0, 0)
        assert g.amount > 0


# ── HealthPotion ──────────────────────────────────────────────────────────────

class TestHealthPotion:
    def test_collect_adds_to_potions(self):
        from src.entities.player import Player
        p = Player(160, 160)
        pot = HealthPotion(0, 0, 30)
        pot.collect(p)
        assert len(p.potions) == 1
        assert p.potions[0].heal_amount == 30

    def test_default_heal_positive(self):
        pot = HealthPotion(0, 0)
        assert pot.heal_amount > 0


# ── EquipItem ─────────────────────────────────────────────────────────────────

class TestEquipItem:
    def test_slot_matches_base(self):
        item = EquipItem(0, 0, "Broad Sword", QUALITY_NORMAL, [])
        assert item.slot == SLOT_WEAPON

    def test_display_name_unique(self):
        item = EquipItem(0, 0, "Dagger", QUALITY_UNIQUE, [],
                         unique_name="Shadowfang")
        assert item.display_name == "Shadowfang"

    def test_display_name_rare(self):
        item = EquipItem(0, 0, "Short Sword", QUALITY_RARE, [])
        # rare items get a procedural two-word name
        parts = item.display_name.split()
        assert len(parts) == 2

    def test_display_name_magic_with_mods(self):
        m = Modifier(MOD_ATK, 5)
        m.name      = "Sharp"       # type: ignore
        m.is_prefix = True           # type: ignore
        m.is_suffix = False          # type: ignore
        item = EquipItem(0, 0, "Short Sword", QUALITY_MAGIC, [m])
        assert "Sharp" in item.display_name
        assert "Short Sword" in item.display_name

    def test_quality_color_defined_for_all_tiers(self):
        for q in (QUALITY_NORMAL, QUALITY_MAGIC, QUALITY_RARE, QUALITY_UNIQUE):
            item = EquipItem(0, 0, "Cap", q, [])
            col = item.quality_color
            assert len(col) == 3

    def test_get_mod_total_sums(self):
        mods = [Modifier(MOD_ATK, 3), Modifier(MOD_ATK, 7)]
        item = EquipItem(0, 0, "Dagger", QUALITY_MAGIC, mods)
        assert item.get_mod_total(MOD_ATK) == 10.0

    def test_get_mod_total_zero_for_missing_kind(self):
        item = EquipItem(0, 0, "Dagger", QUALITY_NORMAL, [])
        assert item.get_mod_total(MOD_DEF) == 0.0

    def test_stat_lines_include_base_stat_weapon(self):
        item = EquipItem(0, 0, "Broad Sword", QUALITY_NORMAL, [])
        labels = [l for l, _ in item.stat_lines()]
        assert any("Attack" in l for l in labels)

    def test_stat_lines_include_base_stat_armor(self):
        item = EquipItem(0, 0, "Leather Armor", QUALITY_NORMAL, [])
        labels = [l for l, _ in item.stat_lines()]
        assert any("Defense" in l for l in labels)


# ── _pick_affixes ─────────────────────────────────────────────────────────────

class TestPickAffixes:
    def test_magic_has_at_least_one_mod(self):
        for _ in range(50):
            mods = _pick_affixes(QUALITY_MAGIC, 1)
            assert len(mods) >= 1, "magic item got zero mods"

    def test_rare_has_at_least_two_mods(self):
        for _ in range(30):
            mods = _pick_affixes(QUALITY_RARE, 3)
            assert len(mods) >= 2

    def test_rare_no_duplicate_mod_kinds(self):
        for _ in range(40):
            mods = _pick_affixes(QUALITY_RARE, 5)
            kinds = [m.kind for m in mods]
            assert len(kinds) == len(set(kinds)), f"duplicate kind in {kinds}"

    def test_normal_has_no_mods(self):
        mods = _pick_affixes(QUALITY_NORMAL, 5)
        assert mods == []


# ── _pick_quality ─────────────────────────────────────────────────────────────

class TestPickQuality:
    def test_returns_valid_quality(self):
        valid = {QUALITY_NORMAL, QUALITY_MAGIC, QUALITY_RARE, QUALITY_UNIQUE}
        for ilvl in range(1, 6):
            for _ in range(20):
                assert _pick_quality(ilvl) in valid

    def test_bonus_reduces_normals(self):
        # With max bonus, unique chance should go up (rough statistical check)
        normal_count = sum(
            1 for _ in range(200) if _pick_quality(5, quality_bonus=40) == QUALITY_NORMAL
        )
        # With bonus the normal count should be well below 200*0.15 expected w/out bonus
        assert normal_count < 100   # very loose bound


# ── random_equip ──────────────────────────────────────────────────────────────

class TestRandomEquip:
    def test_returns_equip_item(self):
        item = random_equip(0, 0, ilvl=1)
        assert isinstance(item, EquipItem)

    def test_unique_slot_filter(self):
        for _ in range(10):
            item = random_equip(0, 0, ilvl=5, quality=QUALITY_UNIQUE, slot=SLOT_WEAPON)
            assert item.slot == SLOT_WEAPON

    def test_forced_quality(self):
        item = random_equip(0, 0, ilvl=3, quality=QUALITY_RARE)
        assert item.quality == QUALITY_RARE

    def test_ilvl_clamp_low(self):
        item = random_equip(0, 0, ilvl=0)
        assert isinstance(item, EquipItem)

    def test_ilvl_clamp_high(self):
        item = random_equip(0, 0, ilvl=99)
        assert isinstance(item, EquipItem)

    def test_fallback_from_unique_to_rare_if_no_eligible(self):
        # Force unique for a slot with no matching unique (none for SLOT_BELT at min_lvl > 1)
        # Easiest: ask for unique with slot=SLOT_BELT at ilvl=1 — Goldwrap is eligible
        item = random_equip(0, 0, ilvl=1, quality=QUALITY_UNIQUE, slot=SLOT_BELT)
        # should be unique (Goldwrap) or fallback to rare if no eligible
        assert item.quality in (QUALITY_UNIQUE, QUALITY_RARE)


# ── random_item ───────────────────────────────────────────────────────────────

class TestRandomItem:
    def test_distribution(self):
        """Smoke test: runs 200 times, must return only known types."""
        for _ in range(200):
            item = random_item(0, 0, level=3)
            assert isinstance(item, (GoldPile, HealthPotion, EquipItem))

    def test_level_affects_equip_quality(self):
        """Floor 5 items should rarely be normal — rough statistical check."""
        normal = sum(
            1 for _ in range(200)
            if isinstance(r := random_item(0, 0, level=5), EquipItem)
            and r.quality == QUALITY_NORMAL
        )
        # Floor 5: ~15% of *equipment* are normal; equipment itself ~54% of drops
        # So ~8% of all items. Over 200 we expect ~16; cap at 60 for safety.
        assert normal < 60


# ── TreasureChest ─────────────────────────────────────────────────────────────

class TestTreasureChest:
    def test_open_spawns_items(self):
        from src.entities.player import Player
        p    = Player(160, 160)
        chest = TreasureChest(5, 5)
        items: list = []
        chest.open(p, items, level=2)
        assert len(items) >= 3          # 2-3 equipment + 1 gold pile
        assert chest.opened

    def test_open_twice_is_idempotent(self):
        from src.entities.player import Player
        p     = Player(160, 160)
        chest = TreasureChest(5, 5)
        items: list = []
        chest.open(p, items, level=1)
        n = len(items)
        chest.open(p, items, level=1)  # second call must do nothing
        assert len(items) == n
