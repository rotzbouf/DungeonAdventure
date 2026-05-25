"""Tests for dungeon generation."""
from src.world.dungeon import Dungeon
from src.settings import TILE_SIZE, FLOORS_PER_NG


# ── Generation sanity ─────────────────────────────────────────────────────────

class TestGeneration:
    def test_rooms_generated(self):
        d = Dungeon(level=1, seed=42)
        assert len(d.rooms) >= 2      # need at least start + stairs room

    def test_player_start_is_walkable(self):
        d  = Dungeon(level=1, seed=42)
        px, py = d.player_start
        tx, ty = int(px // TILE_SIZE), int(py // TILE_SIZE)
        assert d.is_walkable(tx, ty)

    def test_stairs_pos_is_walkable(self):
        d  = Dungeon(level=1, seed=42)
        sx, sy = d.stairs_pos
        tx, ty = int(sx // TILE_SIZE), int(sy // TILE_SIZE)
        assert d.is_walkable(tx, ty)

    def test_enemy_spawns_are_walkable(self):
        d = Dungeon(level=2, seed=99)
        for tx, ty in d.enemy_spawns:
            assert d.is_walkable(tx, ty), f"enemy spawn ({tx},{ty}) not walkable"

    def test_item_spawns_are_walkable(self):
        d = Dungeon(level=1, seed=7)
        for tx, ty in d.item_spawns:
            assert d.is_walkable(tx, ty)

    def test_merchant_spawns_are_walkable(self):
        d = Dungeon(level=1, seed=1)
        for tx, ty in d.merchant_spawns:
            assert d.is_walkable(tx, ty)

    def test_chest_positions_are_walkable(self):
        d = Dungeon(level=1, seed=3)
        for tx, ty in d.chest_positions:
            assert d.is_walkable(tx, ty)

    def test_trap_positions_on_corridor_tiles(self):
        """Traps must be on floor tiles."""
        from src.world.tile import WALKABLE
        d = Dungeon(level=3, seed=55)
        for tx, ty in d.trap_positions:
            assert d.grid[ty][tx] in WALKABLE


# ── Merchant rarity (the new spawn logic) ────────────────────────────────────

class TestMerchantRarity:
    def test_not_always_present(self):
        """Over 30 seeds on floor 1, at least a few floors must have no merchant."""
        floors_without_merchant = sum(
            1 for seed in range(30)
            if not Dungeon(level=1, seed=seed).merchant_spawns
        )
        assert floors_without_merchant >= 1, \
            "Merchants appear on every floor 1 — they should be rare"

    def test_at_most_two_merchants(self):
        """Never more than 2 merchants on any floor."""
        for seed in range(50):
            for level in range(1, FLOORS_PER_NG + 1):
                d = Dungeon(level=level, seed=seed)
                assert len(d.merchant_spawns) <= 2, \
                    f"floor {level} seed {seed}: {len(d.merchant_spawns)} merchants"

    def test_single_merchant_most_common(self):
        """When a merchant is present it's usually just one."""
        counts = [len(Dungeon(level=3, seed=s).merchant_spawns)
                  for s in range(100)]
        single = counts.count(1)
        double = counts.count(2)
        total  = single + double
        if total > 0:   # might be zero if all floors had no merchant
            assert single >= double, \
                f"Two-merchant floors ({double}) outnumber single-merchant floors ({single})"

    def test_deeper_floors_have_higher_spawn_rate(self):
        """Floor 5 should produce more merchants than floor 1 over many seeds."""
        def spawn_count(level):
            return sum(1 for s in range(200) if Dungeon(level=level, seed=s).merchant_spawns)
        floor1_count = spawn_count(1)
        floor5_count = spawn_count(5)
        assert floor5_count > floor1_count, \
            f"Floor 5 ({floor5_count}) no more merchants than floor 1 ({floor1_count})"


# ── Determinism ───────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_seed_same_layout(self):
        d1 = Dungeon(level=2, seed=1234)
        d2 = Dungeon(level=2, seed=1234)
        assert d1.player_start == d2.player_start
        assert d1.stairs_pos   == d2.stairs_pos
        assert len(d1.rooms)   == len(d2.rooms)

    def test_different_seeds_differ(self):
        d1 = Dungeon(level=1, seed=1)
        d2 = Dungeon(level=1, seed=9999)
        # Player starts will almost certainly differ
        assert d1.player_start != d2.player_start


# ── is_walkable boundary ──────────────────────────────────────────────────────

class TestIsWalkable:
    def test_out_of_bounds_not_walkable(self):
        d = Dungeon(level=1, seed=0)
        assert not d.is_walkable(-1, 0)
        assert not d.is_walkable(0, -1)
        assert not d.is_walkable(d.width, 0)
        assert not d.is_walkable(0, d.height)

    def test_void_tile_not_walkable(self):
        from src.world.tile import TILE_VOID
        d = Dungeon(level=1, seed=0)
        # Top-left corner is always VOID
        assert d.grid[0][0] == TILE_VOID
        assert not d.is_walkable(0, 0)
