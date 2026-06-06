"""WandererNPC — a lost adventurer or survivor found randomly in the dungeon.

Spawns 0-1 per floor (from floor 3+).  Player presses F to interact;
a quest-giver screen opens offering one quest.
"""
from __future__ import annotations

import math
import random
import pygame
from src.settings import TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT
from src.entities.merchant import _load_npc_sprite, _draw_npc_glow

_NAMES = [
    "Survivor", "Wanderer", "Lost Scout", "Drifter",
    "Stray Guard", "Deserter", "Delver",
]

_INTERACT_R = TILE_SIZE * 2.5
_SPR_SIZE   = 42


class WandererNPC:
    def __init__(self, tx: int, ty: int, floor: int):
        self.x       = float(tx * TILE_SIZE + TILE_SIZE // 2)
        self.y       = float(ty * TILE_SIZE + TILE_SIZE // 2)
        self.floor   = floor
        self.title   = random.choice(_NAMES)
        self._bob_t  = random.uniform(0, math.pi * 2)
        self._sprite = _load_npc_sprite("wanderer", _SPR_SIZE)
        self._gem    = (
            random.randint(80, 200),
            random.randint(80, 200),
            random.randint(80, 200),
        )

    def near_player(self, player) -> bool:
        return math.hypot(self.x - player.x, self.y - player.y) < _INTERACT_R

    def update(self, dt: float) -> None:
        self._bob_t += dt

    def draw(self, surface: pygame.Surface, camera) -> None:
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        sx = int(self.x - camera.x)
        sy = int(self.y - camera.y)
        if not (-60 < sx < SCREEN_WIDTH + 60 and -60 < sy < play_h + 60):
            return
        bob = math.sin(self._bob_t * 1.4) * 3
        cy = sy + int(bob)
        _draw_npc_glow(surface, sx, cy, self._bob_t, self._gem)
        if self._sprite:
            r = self._sprite.get_rect(centerx=sx, bottom=cy + _SPR_SIZE // 2 + 4)
            surface.blit(self._sprite, r)
        else:
            pygame.draw.circle(surface, self._gem, (sx, cy), 12)
            pygame.draw.circle(surface, (0, 0, 0), (sx, cy), 12, 1)
        # Name tag
        try:
            font = pygame.font.SysFont("monospace", 14, bold=True)
            tag  = font.render(self.title, True, (220, 220, 160))
            surface.blit(tag, (sx - tag.get_width() // 2, cy - _SPR_SIZE // 2 - 14))
        except Exception:
            pass
