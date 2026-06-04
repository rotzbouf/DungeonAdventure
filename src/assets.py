"""
Asset loader — serves pre-generated PNG sprites/textures from assets/.
Falls back silently to None when assets are absent so the procedural
pygame.draw code continues to work unchanged.

Usage:
    from src.assets import assets
    spr = assets.player("south")         # pygame.Surface or None
    spr = assets.enemy("goblin")         # pygame.Surface or None
    tex = assets.tile("floor", "dungeon", variant=0)
    fac = assets.town_facade("weapons")  # pygame.Surface or None
"""
from __future__ import annotations
import sys
from pathlib import Path
import pygame

# When running as a PyInstaller bundle sys.frozen is True and all bundled
# data files live under sys._MEIPASS.  In normal development the assets/
# folder sits two levels above this file.
if getattr(sys, "frozen", False):
    _ASSETS = Path(sys._MEIPASS) / "assets"   # type: ignore[attr-defined]
else:
    _ASSETS = Path(__file__).parent.parent / "assets"


class AssetManager:
    def __init__(self):
        self._cache: dict[str, pygame.Surface | None] = {}
        self._ready = False   # pygame must be init before loading

    def _load(self, path: Path, size: tuple | None = None) -> pygame.Surface | None:
        key = str(path) + str(size)
        if key in self._cache:
            return self._cache[key]
        if not path.exists():
            self._cache[key] = None
            return None
        try:
            surf = pygame.image.load(str(path)).convert_alpha()
            if size:
                surf = pygame.transform.smoothscale(surf, size)
            self._cache[key] = surf
            return surf
        except Exception:
            self._cache[key] = None
            return None

    # ── Player sprites ────────────────────────────────────────────────────────

    def player(self, direction: str = "south",
               size: tuple | None = None) -> pygame.Surface | None:
        """direction: 'south' | 'north' | 'east' | 'west'"""
        path = _ASSETS / "sprites" / f"player_{direction}.png"
        return self._load(path, size)

    # ── Enemy sprites ─────────────────────────────────────────────────────────

    def enemy(self, kind: str, size: tuple | None = None) -> pygame.Surface | None:
        """kind: 'goblin' | 'skeleton' | 'orc' | 'demon' (etc.)"""
        path = _ASSETS / "sprites" / "enemies" / f"{kind.lower()}.png"
        return self._load(path, size)

    # ── Tile textures ─────────────────────────────────────────────────────────

    def tile(self, tile_type: str, theme: str,
             variant: int = 0) -> pygame.Surface | None:
        """tile_type: 'floor' | 'wall'.  theme: 'dungeon' | 'crypt' etc."""
        path = _ASSETS / "tiles" / f"{tile_type}_{theme}_{variant % 4}.png"
        return self._load(path, (40, 40))

    # ── Town facades ──────────────────────────────────────────────────────────

    def town_facade(self, specialty: str,
                    size: tuple | None = None) -> pygame.Surface | None:
        """specialty: 'weapons' | 'armor' | 'jewelry' | 'potions' | 'enchant' | 'craft' | 'house'"""
        path = _ASSETS / "town" / f"facade_{specialty}.png"
        return self._load(path, size)

    # ── Item sprites ──────────────────────────────────────────────────────────

    def item(self, kind: str,
             size: tuple | None = None) -> pygame.Surface | None:
        """kind: 'gold_pile' | 'health_potion' | 'weapon_sword' | 'ring' etc."""
        path = _ASSETS / "items" / f"{kind}.png"
        return self._load(path, size)

    def clear_cache(self):
        self._cache.clear()

    @property
    def available(self) -> bool:
        return (_ASSETS / "sprites" / "player_south.png").exists()


# Module-level singleton
assets = AssetManager()
